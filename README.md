# tdw_physics

These classes create a generic structure for generating physics datasets using TDW. They aim to:

1. Simplify the process of writing many similar controllers.
2. Ensure uniform output data organization across similar controllers.

## Requirements

- [TDW](https://github.com/threedworld-mit/tdw) (See requirements for graphics rendering)
- Some controllers in this repo have additional requirements. Read [this](controllers/README.md#Requirements) for a more detailed list.

## Installation

1. `cd path/to/tdw_physics`
2. `pip3 install -e .` (This installs the `tdw_physics` module).

## Controllers

See the `controllers/` directory for controllers that use `tdw_physics` as well as [documentation](controllers/README.md). See below for the output .hdf5 file structure.

## Changelog

See [changelog](changelog.md).

## Usage

tdw_physics provides abstract Controller classes. To write your own physics dataset controller, you should create a superclass of the appropriate controller.

| Abstract Controller  | Output Data                                                  |
| -------------------- | ------------------------------------------------------------ |
| `RigidbodiesDataset` | `Tranforms`, `Images`, `CameraMatrices`, `Rigidbodies`, `Collision`, `EnvironmentCollision` |
| `TransformsDataset`  | `Transforms`, `Images`, `CameraMatrices`                     |
| `FlexDataset`        | `Transforms`, `Images`, `CameraMatrics`, `FlexParticles`     |

**Every tdw_physics controller will do the following:**

1. When a dataset controller is initially launched, it will always sent [these commands](https://github.com/alters-mit/tdw_physics/blob/30314b753860f3fd92ddc72fdb182816856632d6/tdw_physics/dataset.py#L52-L76). 
2. Initialize a scene (these commands get sent only once in the entire dataset).
3. Run a series of trials:
   1. Initialize the trial.
   2. Create a new .hdf5 output file.
   3. Write _static data_ to the .hdf5 file. This data won't change between frames.
   4. Step through frames. Write _per-frame_ data to the .hdf5 file. Check if the trial is done.
   5. When the trial is done, destroy all objects and close the .hdf5 file.

Each trial outputs a separate .hdf5 file in the root output directory. The files are named sequentially, e.g.:

```
root/
....0000.hdf5
....0001.hdf1
```

- All images are 256x256
- The `_img` pass is a .jpg and all other passes are .png

## How to Create a Dataset Controller

_Regardless_ of which abstract controller you use, you must override the following functions:

| Function                                                 | Type         | Return                                                       |
| -------------------------------------------------------- | ------------ | ------------------------------------------------------------ |
| `get_scene_initialization_commands()`                    | `List[dict]` | A list of commands to initialize the dataset's scene. These commands are sent only once in the entire dataset run (e.g. post-processing commands). |
| `get_trial_initialization_commands()`                    | `List[dict]` | A list of commands to initialize a single trial. This should include all object setup, avatar position and camera rotation, etc. You do not need to include any cleanup commands such as `destroy_object`; that is handled automatically elsewhere. _NOTE:_ You must use alternate functions to add objects; see below. |
| `get_per_frame_commands(resp: List[bytes], frame: int):` | `List[dict]` | Commands to send per-frame, based on the response from the build. |
| `get_field_of_view()`                                    | `float`      | The avatar's field of view value.                            |

***

## `RigidbodiesDataset`

```python
from typing import List
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset

class MyDataset(RigidbodiesDataset):
    def get_scene_initialization_commands(self) -> List[dict]:
        # Your code here.

    def get_trial_initialization_commands(self) -> List[dict]:
        # Your code here.

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        # Your code here.

    def get_field_of_view(self) -> float:
        # Your code here.
```

A dataset creator that receives and writes per frame: `Tranforms`, `Images`, `CameraMatrices`, `Rigidbodies`, `Collision`, and `EnvironmentCollision`.

### Ending a trial

A `RigidbodiesDataset` trial ends when all objects are "sleeping" i.e. non-moving, or after 1000 frames. Objects that have fallen below the scene's floor (y < -1) are ignored.

You can override this by adding the function `def is_done()`:

```python
    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 1000 # End after 1000 frames even if objects are still moving.
```

### Adding objects

Objects should only be added in `get_trial_initialization_commands()` or (more rarely) `get_per_frame_commands()`.

#### `def get_add_physics_object()`

Get commands to add an object and assign physics properties. Write the object's static info to the .hdf5 file.

_Return:_ A list of commands to add an object and set its physics values.

```python
from typing import List
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset

class MyDataset(RigidbodiesDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Your code here.
        object_id = self.get_unique_id()
        commands.extend(self.get_add_physics_object(model_name="iron_box",
                                                    library="models_core.json",
                                                    object_id=object_id,
                                                    position={"x": 0, "y": 0, "z": 0},
                                                    rotation={"x": 0, "y": 0, "z": 0},
                                                    default_physics_values=False,
                                                    mass=1.5,
                                                    dynamic_friction=0.1,
                                                    static_friction=0.2,
                                                    bounciness=0.5))
        return commands
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| model_name |  str |  | The name of the model. |
| position |  Dict[str, float] | None | The position of the model. If None, defaults to `{"x": 0, "y": 0, "z": 0}`. |
| rotation |  Dict[str, float] | None | The starting rotation of the model, in Euler angles. If None, defaults to `{"x": 0, "y": 0, "z": 0}`. |
| library |  str  | "" | The path to the records file. If left empty, the default library will be selected. See `ModelLibrarian.get_library_filenames()` and `ModelLibrarian.get_default_library()`. |
| object_id |  int |  | The ID of the new object. |
| scale_factor |  Dict[str, float] | None | The [scale factor](../api/command_api.md#scale_object). |
| kinematic |  bool  | False | If True, the object will be [kinematic](../api/command_api.md#set_kinematic_state). |
| gravity |  bool  | True | If True, the object won't respond to [gravity](../api/command_api.md#set_kinematic_state). |
| default_physics_values |  bool  | True | If True, use default physics values. Not all objects have default physics values. To determine if object does: `has_default_physics_values = model_name in DEFAULT_OBJECT_AUDIO_STATIC_DATA`. |
| mass |  float  | 1 | The mass of the object. Ignored if `default_physics_values == True`. |
| dynamic_friction |  float  | 0.3 | The [dynamic friction](../api/command_api.md#set_physic_material) of the object. Ignored if `default_physics_values == True`. |
| static_friction |  float  | 0.3 | The [static friction](../api/command_api.md#set_physic_material) of the object. Ignored if `default_physics_values == True`. |
| bounciness |  float  | 0.7 | The [bounciness](../api/command_api.md#set_physic_material) of the object. Ignored if `default_physics_values == True`. |

#### `def get_objects_by_mass()`

_Return:_ IDs of objects with mass <= the mass threshold.

| Parameter | Type    | Default | Description         |
| --------- | ------- | ------- | ------------------- |
| `mass`    | `float` |         | The mass threshold. |

#### `def get_falling_commands()`

_Return:_ A list of lists; per-frame commands to make small objects fly up.

| Parameter | Type    | Default | Description                                      |
| --------- | ------- | ------- | ------------------------------------------------ |
| `mass`    | `float` | 3       | Objects with <= this mass might receive a force. |

#### `PHYSICS_INFO`

`RigidbodiesDataset` caches default physics info per object (see above) in a dictionary where the key is the model name and the values is a `PhysicsInfo` object:

```python
from tdw_physics.physics_info import PHYSICS_INFO

info = PHYSICS_INFO["chair_billiani_doll"]

print(info.model_name) # chair_billiani_doll
print(info.library)
print(info.mass)
print(info.dynamic_friction)
print(info.static_friction)
print(info.bounciness)
```

### .hdf5 file structure

```
static/    # Data that doesn't change per frame.
....object_ids
....mass
....static_friction
....dynamic_friction
....bounciness
frames/    # Per-frame data.
....0000/    # The frame number.
........images/    # Each image pass.
............_img
............_id
............_depth
............_normals
............_flow
........objects/    # Per-object data.
............positions
............forwards
............rotations
............velocities
............angular_velocities
........collisions/    # Collisions between two objects.
............object_ids
............relative_velocities
............contacts
........env_collisions/    # Collisions between one object and the environment.
............object_ids
............contacts
........camera_matrices/
............projection_matrix
............camera_matrix
....0001/
........ (etc.)
```

- All object data is ordered to match `object_ids`. For example:
  - `static/mass[0]` is the mass of `static/object_ids[0]`
  - `frames/0000/positions[0]` is the position of `static/object_ids[0]`
- The shape of each dataset in `objects` is determined by the number of coordinates. For example, `frames/objects/positions/` has shape `(num_objects, 3)`.
- The  shape of all datasets in `collisions/` and `env_collisions/`are defined by the number of collisions on that frame.
  -  `frames/collisions/relative_velocities` has the shape `(num_collisions, 3)`
  -  `frames/collisions/object_ids` has the shape `(num_collisions, 2)` (tuple of IDs).
  -  `frames/env_collisions/object_ids` has the shape `(num_collisions)` (only 1 ID per collision).
  -  `frames/collisions/contacts` and `frames/env_collision/contacts` are tuples of `(normal, point)`, i.e. the shape is `(num_collisions, 2, 3)`.

***

## `TransformsDataset`

```python
from typing import List
from tdw_physics.transforms_dataset import TransformsDataset

class MyDataset(TransformsDataset):
    def get_scene_initialization_commands(self) -> List[dict]:
        # Your code here.

    def get_trial_initialization_commands(self) -> List[dict]:
        # Your code here.

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        # Your code here.

    def get_field_of_view(self) -> float:
        # Your code here.
```

A dataset creator that receives and writes per frame: `Transforms`, `Images`, `CameraMatrices`. 

### Ending a trial

A `TransformsDataset` trial has no "end" condition based on trial output data; you will need to define this yourself by  adding the function `def is_done()`:

```python
    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 1000 # End after 1000 frames.
```

### Adding objects

#### `def get_add_object()`

_Return:_ An `add_object` command.

```python
from typing import List
from tdw_physics.transforms_dataset import TransformsDataset

class MyDataset(TransformsDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Your code here.
        commands.append(self.get_add_object(model_name="iron_box",
                                            library="models_core.json",
                                            object_id=self.get_unique_id(),
                                            position={"x": 0, "y": 0, "z": 0},
                                            rotation={"x": 0, "y": 0, "z": 0}))
        return commands
```

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| model_name |  str |  | The name of the model. |
| position |  Dict[str, float] | None | The position of the model. If None, defaults to `{"x": 0, "y": 0, "z": 0}`. |
| rotation |  Dict[str, float] | None | The starting rotation of the model, in Euler angles. If None, defaults to `{"x": 0, "y": 0, "z": 0}`. |
| library |  str  | "" | The path to the records file. If left empty, the default library will be selected. See `ModelLibrarian.get_library_filenames()` and `ModelLibrarian.get_default_library()`. |
| object_id |  int |  | The ID of the new object. |

### .hdf5 file structure

```
static/    # Data that doesn't change per frame.
....object_ids
frames/    # Per-frame data.
....0000/    # The frame number.
........images/    # Each image pass.
............_img
............_id
............_depth
............_normals
............_flow
........objects/    # Per-object data.
............positions
............forwards
............rotations
........camera_matrices/
............projection_matrix
............camera_matrix
....0001/
........ (etc.)
```

- All object data is ordered to match `object_ids`. For example:
  - `static/mass[0]` is the mass of `static/object_ids[0]`
  - `frames/0000/positions[0]` is the position of `static/object_ids[0]`
- The shape of each dataset in `objects` is determined by the number of coordinates. For example, `frames/objects/positions/` has shape `(num_objects, 3)`.

***

## `FlexDataset`

```python
from typing import List
from tdw_physics.flex_dataset import FlexDataset

class MyDataset(FlexDataset):
    def get_scene_initialization_commands(self) -> List[dict]:
        # Your code here.

    def get_trial_initialization_commands(self) -> List[dict]:
        # Your code here.

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        # Your code here.

    def get_field_of_view(self) -> float:
        # Your code here.
```

A dataset creator that receives and writes per frame: `Transforms`, `Images`, `CameraMatrices`, and `FlexParticles`. 

### Adding objects

**`Controller.add_object()` and `Conroller.get_add_object()` will throw an exception.** You must instead use wrapper functions to add Flex objects. They will automatically cache the object ID, allowing the object to be destroyed at the end of the trial.

#### `def add_solid_object()`

_Return:_ A list of commands to add a solid-body object.

```python
from typing import List
from tdw_physics.flex_dataset import FlexDataset

class MyDataset(FlexDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Your code here.
        commands.extend(self.add_solid_object(model_name="microwave",
                                              library="models_full.json", 
                                              object_id=self.get_unique_id(),                                      
                                              position={"x": 0, "y": 0, "z": 0},
                                              rotation={"x": 0, "y": 0, "z": 0},
                                              scale_factor={"x": 1, "y": 1, "z": 1},
                                              mesh_expansion=0,
                                              particle_spacing=0.125,
                                              mass_scale=1))
        return commands
```

| Parameter          | Type               | Default | Description                                               |
| ------------------ | ------------------ | ------- | --------------------------------------------------------- |
| `model_name`       | `str`              |         | The model name.                                           |
| `object_id`        | `int`              |         | The object ID.                                            |
| `library`          | `str`              |         | The model librarian.                                      |
| `position`         | `Dict[str, float`] |         | The initial position of the object.                       |
| `rotation`         | `Dict[str, float]` |         | The initial rotation of the object, in Euler angles.      |
| `scale_factor`     | `Dict[str, float]` | `None`  | The object scale factor. If None, the scale is (1, 1, 1). |
| `mesh_expansion`   | `float`            | 0       |                                                           |
| `particle_spacing` | `float`            | 0.125   |                                                           |
| `mass_scale`       | float              | 1       |                                                           |

#### `def add_soft_object()`

_Return:_ A list of commands to add a soft-body object.

```python
from typing import List
from tdw_physics.flex_dataset import FlexDataset

class MyDataset(FlexDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Your code here.
        commands.extend(self.add_soft_object(model_name="microwave",
                                             library="models_full.json",
                                             object_id=self.get_unique_id(),
                                             position={"x": 0, "y": 0, "z": 0},
                                             rotation={"x": 0, "y": 0, "z": 0},
                                             scale_factor={"x": 1, "y": 1, "z": 1},
                                             volume_sampling=2,
                                             surface_sampling=0,
                                             mass_scale=1,
                                             cluster_spacing=0.2,
                                             cluster_radius=0.2,
                                             cluster_stiffness=0.2,
                                             link_radius=0.1,
                                             link_stiffness=0.5,
                                             particle_spacing=0.02))
        return commands
```

| Parameter           | Type               | Default | Description                                                  |
| ------------------- | ------------------ | ------- | ------------------------------------------------------------ |
| `model_name`       | `str`              |         | The model name.                                           |
| `object_id`        | `int`              |         | The object ID.                                            |
| `library`          | `str`              |         | The model librarian.                                      |
| `position`          | `Dict[str, float`] |         | The initial position of the object.                          |
| `rotation`          | `Dict[str, float]` |         | The initial rotation of the object, in Euler angles.         |
| `scale_factor`             | `Dict[str, float]` | `None`  | The object scale factor. If None, the scale is (1, 1, 1).    |
| `volume_sampling`   | `float`            | 2       |                                                              |
| `surface_sampling`  | `float`            | 0       |                                                              |
| `mass_scale`        | `float`            | 1       |                                                              |
| `cluster_spacing`   | `float`            | 0.2     |                                                              |
| `cluster_radius`    | `float`            | 0.2     |                                                              |
| `cluster_stiffness` | `float`            | 0.2     |                                                              |
| `link_radius`       | `float`            | 0.1     |                                                              |
| `link_stiffness`    | `float`            | 0.5     |                                                              |
| `particle_spacing`  | `float`            | 0.02    |                                                              |

#### `def add_cloth_object()`

_Return:_ A list of commands to add a cloth object.

```python
from typing import List
from tdw_physics.flex_dataset import FlexDataset

class MyDataset(FlexDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Your code here.
        commands.extend(self.add_cloth_object(model_name="cloth_square",
                                              library="models_special.json",
                                              object_id=self.get_unique_id(),
                                              position={"x": 0, "y": 0, "z": 0},
                                              rotation={"x": 0, "y": 0, "z": 0},
                                              scale_factor={"x": 1, "y": 1, "z": 1},
                                              stretch_stiffness=0.1,
                                              bend_stiffness=0.1,
                                              tether_stiffness=0.1,
                                              tether_give=0,
                                              pressure=0,
                                              mass_scale=1))
        return commands
```

| Parameter           | Type               | Default | Description                                                  |
| ------------------- | ------------------ | ------- | ------------------------------------------------------------ |
| `model_name`       | `str`              |         | The model name.                                           |
| `object_id`        | `int`              |         | The object ID.                                            |
| `library`          | `str`              |         | The model librarian.                                      |
| `position`          | `Dict[str, float`] |         | The initial position of the object.                          |
| `rotation`          | `Dict[str, float]` |         | The initial rotation of the object, in Euler angles.         |
| `scale_factor`             | `Dict[str, float]` | `None`  | The object scale factor. If None, the scale is (1, 1, 1).    |
| `mesh_tesselation`  | `int`              | 1       |                                                              |
| `stretch_stiffness` | `int`              | 0.1     |                                                              |
| `bend_stiffness`    | `int`              | 0.1     |                                                              |
| `tether_stiffness`  | `float`            | 0       |                                                              |
| `tether_give`       | `float`            | 0       |                                                              |
| `pressure`          | `float`            | 0       |                                                              |
| `mass_scale`        | `float`            | 1       |                                                              |

#### `def add_fluid_object()`

_Return:_ A list of commands to add a fluid object.

```python
from typing import List
from tdw_physics.flex_dataset import FlexDataset


class MyDataset(FlexDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []

        # Your code here.

        # Cache the pool ID to destroy it correctly.
        pool_id = Controller.get_unique_id()
        self.non_flex_objects.append(pool_id)
        # Add the pool.
        commands.append(self.get_add_object(model_name="fluid_receptacle1x1",
                                            library="models_special.json",
                                            object_id=pool_id,
                                            position={"x": 0, "y": 0, "z": 0},
                                            rotation={"x": 0, "y": 0, "z": 0}))
        # Add a container here.

        # Add the fluid.
        commands.extend(self.add_fluid_object(position={"x": 0, "y": 1.0, "z": 0},
                                              rotation={"x": 0, "y": 0, "z": 0},
                                              object_id=Controller.get_unique_id(),
                                              fluid_type="water"))
        return commands
```

| Parameter          | Type               | Default | Description                                                  |
| ------------------ | ------------------ | ------- | ------------------------------------------------------------ |
| `object_id`        | `int`              |         | The object ID.                                            |
| `position`         | `Dict[str, float`] |         | The initial position of the object.                          |
| `rotation`         | `Dict[str, float]` |         | The initial rotation of the object, in Euler angles.         |
| `scale`            | `Dict[str, float]` | `None`  | The object scale factor. If None, the scale is (1, 1, 1).    |
| `particle_spacing` | `float`            | 0.05    |                                                              |
| `mass_scale`       | `float`            | 1       |                                                              |
| `fluid_type`       | `str`              |         | The name of the fluid type.                                  |

### .hdf5 file structure

```
static/    # Data that doesn't change per frame.
....object_ids
....container/ # Flex container parameters.
........radius
........solid_rest
........fluid_rest
........planes
........(etc.)
....solid_actors/ # Flex solid object parameters.
........object_id
........mass_scale
........(etc.)
....soft_actors/ # Flex soft object parameters.
........object_id
........mass_scale
........(etc.)
....cloth_actors/ # Flex cloth object parameters.
........object_id
........mass_scale
........(etc.)
....fluid_actors/ # Flex fluid object parameters.
........object_id
........mass_scale
........(etc.)
frames/    # Per-frame data.
....0000/    # The frame number.
........images/    # Each image pass.
............_img
............_id
............_depth
............_normals
............_flow
........objects/    # Per-object data.
............positions
............forwards
............rotations
........camera_matrices/
............projection_matrix
............camera_matrix
........particles/    # Per-object particles.
........velocities/    # Per-object velocities.
....0001/
........ (etc.)
```

- All object data is ordered to match `object_ids`. For example:
  - `static/mass[0]` is the mass of `static/object_ids[0]`
  - `frames/0000/positions[0]` is the position of `static/object_ids[0]`
- The shape of each dataset in `objects` is determined by the number of coordinates. For example, `frames/objects/positions/` has shape `(num_objects, 3)`.
- **Regarding Flex data**:
  - All static Flex data is serialized to match the `object_id` array. e.g. `static/solid_actors/mass_scale[0]` is the mass_scale of `static/solid_actors/object_id[0]`. This data *might not match the order* of `static/object_ids`.
  - Particles and velocities _do_ match `static/object_ids`. `frame/particles[0]` is the particles for `static/object_ids[0]`.
  - `frame/particles` and `frame/velocities` are arrays of arrays of particle data and have shape `(num_objects, len_particle_data)`.

## `utils.py`

Some helpful utility functions and variables.

#### `def get_move_along_direction()`

_Return:_ A position from pos by distance d along a directional vector defined by pos, target.

```python
from tdw_physics.util import get_move_along_direction

p_0 = {"x": 1, "y": 0, "z": -2}
p_1 = {"x": 5, "y": 0, "z": 3.4}
p_0 = get_move_along_direction(pos=p_0, target=p_1, d=0.7, noise=0.01)
```

| Parameter | Type               | Default | Description                         |
| --------- | ------------------ | ------- | ----------------------------------- |
| `pos`     | `Dict[str, float]` |         | The object's position.              |
| `target`  | `Dict[str, float]` |         | The target position.                |
| `d`       | `float`            |         | The distance to teleport.           |
| `noise`   | `float`            | 0       | Add a little noise to the teleport. |

#### `def get_object_look_at()`

_Return:_ A list of commands to rotate an object to look at the target position.

```python
from tdw_physics.util import get_object_look_at

o_id = 0 # Assume that the object has been already added to the scene.
p_1 = {"x": 5, "y": 0, "z": 3.4}
p_0 = get_object_look_at(o_id=o_id, pos=p_1, noise=5)
```

| Parameter | Type               | Default | Description                                                  |
| --------- | ------------------ | ------- | ------------------------------------------------------------ |
| `o_id`    | `int`              |         | The object's ID.                                             |
| `pos`     | `Dict[str, float]` |         | The position to look at.                                     |
| `noise`   | `float`            | 0       | Rotate the object randomly by this much after applying the look_at command. |

#### `def get_args()`

_Return:_ Command line arguments common to all controllers.

```python
from tdw_physics.util import get_args
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset

class MyDataset(RigidbodiesDataset):
    # Your code here.
    
if __name__ == "__main__":
    args = get_args("my_dataset")
    MyDataset().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
```

| Parameter     | Type  | Default | Description                                                  |
| ------------- | ----- | ------- | ------------------------------------------------------------ |
| `dataset_dir` | `str` |         | If you don't provide a `--dir` argument, the default output director is: `"D:/" + dataset_dir` |

## `extract_images.py`

```bash
python3 extract_images.py [ARGUMENTS]
```

Extract `_img` images from an .hdf5 file and save them to a destination directory.

| Argument | Type  | Default | Description                               |
| -------- | ----- | ------- | ----------------------------------------- |
| `--dest` | `str` |         | Root directory for the images.            |
| `--src`  | `str` |         | Root source directory of the .hdf5 files. |

