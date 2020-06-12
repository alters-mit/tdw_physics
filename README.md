# tdw_physics

These classes create a generic structure for generating physics datasets using TDW. They aim to:

1. Simplify the process of writing many similar controllers.
2. Ensure uniform output data organization across similar controllers.

## Installation

1. Clone the TDWBase repo and download the latest build.
2. Clone this repo.
3. `cd path/to/tdw_physics`
4. `pip3 install -e .` (This installs the `tdw_physics` module).

## Controllers

See the `controllers/` directory for controllers that use `tdw_physics` as well as [documentation](controllers/README.md). See below for the output .hdf5 file structure.

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

**`Controller.add_object()` and `Conroller.get_add_object()` will throw an exception.** You must instead use `RigidbodiesDataset.add_physics_object()` or `RigidbodiesDataset.add_physics_object_default()`. This will automatically cache the object ID, allowing the object to be destroyed at the end of the trial.

Objects should only be added in `get_trial_initialization_commands()` or (more rarely) `get_per_frame_commands()`.

#### `def add_physics_object()`

Get commands to add an object and assign physics properties. Write the object's static info to the .hdf5 file.

_Return:_ A list of commands: `[add_object, set_mass, set_physic_material]`

```python
from tdw.librarian import ModelLibrarian
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset

class MyDataset(RigidbodiesDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Your code here.
        lib = ModelLibrarian("models_full.json")
        record = lib.get_record("iron_box")
        commands.extend(self.add_physics_objec(record=record, 
                                               position={"x": 0, "y": 0, "z": 0},
                                               rotation={"x": 0, "y": 0, "z": 0},
                                               o_id=0,
                                               mass=1.5,
                                               dynamic_friction=0.1,
                                               static_friction=0.2,
                                               bounciness=0.5))
```

| Parameter          | Type               | Default | Description                                                  |
| ------------------ | ------------------ | ------- | ------------------------------------------------------------ |
| `record`           | `ModelRecord`      |         | The model record.                                            |
| `position`         | `Dict[str, float]` |         | The initial position of the object.                          |
| `rotation`         | `Dict[str, float]` |         | The initial rotation of the object, in Euler angles.         |
| `o_id`             | `Optional[int]`    | `None`  | The unique ID of the object. If None, a random ID is generated. |
| `mass`             | `float`            |         | The mass of the object.                                      |
| `dynamic_friction` | `float`            |         | The dynamic friction of the object's physic material.        |
| `static_friction`  | `float`            |         | The static friction of the object's physic material.         |
| `bounciness`       | `float`            |         | The bounciness of the object's physic material.              |

#### `def add_physics_object_default()`

Get commands to add an object and assign physics values based on _default physics values_. These values are loaded automatically and located in: `tdw_physics/data/physics_info.json` Note that _only a small percentage of TDW objects have physics info._ More will be added over time.

_Return:_ A list of commands: `[add_object, set_mass, set_physic_material]`

```python
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset

class MyDataset(RigidbodiesDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Your code here.
        commands.extend(self.add_physics_object_default(name="iron_box", 
                                                        position={"x": 0, "y": 0, "z": 0},
                                                        rotation={"x": 0, "y": 0, "z": 0},
                                                        o_id=0))
```

| Parameter  | Type               | Default | Description                                                  |
| ---------- | ------------------ | ------- | ------------------------------------------------------------ |
| `name`     | `str`              |         | The name of the model.                                       |
| `position` | `Dict[str, float]` |         | The initial position of the object.                          |
| `rotation` | `Dict[str, float]` |         | The initial rotation of the object, in Euler angles.         |
| `o_id`     | `Optional[int]`    | `None`  | The unique ID of the object. If None, a random ID is generated. |

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
from tdw_physics.RigidbodiesDataset import PHYSICS_INFO

info = PHYSICS_INFO["chair_billiani_doll"]

print(info.record.name) # chair_billiani_doll
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

#### `physics_info_calculator.py`

Use this controller to add more default `PhysicsInfo`. The controller will assign "best guess" values based on the object's material and size.

```bash
python3 physics_info_calculator.py [ARGUMENTS]
```

| Argument | Type  | Default            | Description                        |
| -------- | ----- | ------------------ | ---------------------------------- |
| `--name` | `str` |                    | The name of the model.             |
| `--lib`  | `str` | `models_full.json` | The model library.                 |
| `--mat`  | `str` |                    | The semantic material (see below). |

**Semantic Materials**

- ceramic
- concrete
- fabric
- glass
- leather
- metal
- plastic
- rubber
- stone
- wood
- paper
- organic

***

## `TransformsDataset`

```python
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

**`Controller.add_object()` and `Conroller.get_add_object()` will throw an exception.** You must instead use `TransformsDataset.add_transforms_object()`. This will automatically cache the object ID, allowing the object to be destroyed at the end of the trial.

#### `def add_transforms_object()`

_Return:_ An `add_object` command.

```python
from tdw.librarian import ModelLibrarian
from tdw_physics.transforms_dataset import TransformsDataset

class MyDataset(TransformsDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Your code here.
        lib = ModelLibrarian("models_full.json")
        record = lib.get_record("iron_box")
        commands.append(self.add_transforms_object(record=record, 
                                                   position={"x": 0, "y": 0, "z": 0},
                                                   rotation={"x": 0, "y": 0, "z": 0},
                                                   o_id=0))
```

| Parameter  | Type               | Default | Description                                                  |
| ---------- | ------------------ | ------- | ------------------------------------------------------------ |
| `record`   | `ModelRecord`      |         | The model record.                                            |
| `position` | `Dict[str, float]` |         | The initial position of the object.                          |
| `rotation` | `Dict[str, float]` |         | The initial rotation of the object, in Euler angles.         |
| `o_id`     | `Optional[int]`    | `None`  | The unique ID of the object. If None, a random ID is generated. |

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

_Return:_ A list of commands: `[add_object, scale_object, set_flex_solid_actor, assign_flex_container]`

```python
from tdw.librarian import ModelLibrarian
from tdw_physics.flex_dataset import FlexDataset

class MyDataset(FlexDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Your code here.
        lib = ModelLibrarian("models_full.json")
        record = lib.get_record("microwave")
        commands.append(self.add_solid_object(record=record, 
                                              position={"x": 0, "y": 0, "z": 0},
                                              rotation={"x": 0, "y": 0, "z": 0},
                                              scale={"x": 1, "y": 1, "z": 1},
                                              o_id=0,
                                              mesh_expansion=0,
                                              particle_spacing=0.125,
                                              mass_scale=1))
```

| Parameter          | Type               | Default | Description                                                  |
| ------------------ | ------------------ | ------- | ------------------------------------------------------------ |
| `record`           | `ModelRecord`      |         | The model record.                                            |
| `position`         | `Dict[str, float`] |         | The initial position of the object.                          |
| `rotation`         | `Dict[str, float]` |         | The initial rotation of the object, in Euler angles.         |
| `scale`            | `Dict[str, float]` | `None`  | The object scale factor. If None, the scale is (1, 1, 1).    |
| `o_id`             | `Optional[int]`    | `None`  | The unique ID of the object. If None, a random ID is generated. |
| `mesh_expansion`   | `float`            | 0       |                                                              |
| `particle_spacing` | `float`            | 0.125   |                                                              |
| `mass_scale`       | float              | 1       |                                                              |

#### `def get_soft_object()`

_Return:_ A list of commands: `[add_object, scale_object, set_flex_soft_actor, assign_flex_container]`

```python
from tdw.librarian import ModelLibrarian
from tdw_physics.flex_dataset import FlexDataset

class MyDataset(FlexDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Your code here.
        lib = ModelLibrarian("models_full.json")
        record = lib.get_record("microwave")
        commands.append(self.add_soft_object(record=record, 
                                             position={"x": 0, "y": 0, "z": 0},
                                             rotation={"x": 0, "y": 0, "z": 0},
                                             scale={"x": 1, "y": 1, "z": 1},
                                             o_id=0,
                                             volume_sampling=2,
                                             surface_sampling=0,
                                             mass_scale=1,
                                             cluster_spacing=0.2,
                                             cluster_radius=0.2,
                                             cluster_stiffness=0.2,
                                             link_radius=0.1,
                                             link_stiffness=0.5,
                                             particle_spacing=0.02))
```

| Parameter           | Type               | Default | Description                                                  |
| ------------------- | ------------------ | ------- | ------------------------------------------------------------ |
| `record`            | `ModelRecord`      |         | The model record.                                            |
| `position`          | `Dict[str, float`] |         | The initial position of the object.                          |
| `rotation`          | `Dict[str, float]` |         | The initial rotation of the object, in Euler angles.         |
| `scale`             | `Dict[str, float]` | `None`  | The object scale factor. If None, the scale is (1, 1, 1).    |
| `o_id`              | `Optional[int]`    | `None`  | The unique ID of the object. If None, a random ID is generated. |
| `volume_sampling`   | `float`            | 2       |                                                              |
| `surface_sampling`  | `float`            | 0       |                                                              |
| `mass_scale`        | `float`            | 1       |                                                              |
| `cluster_spacing`   | `float`            | 0.2     |                                                              |
| `cluster_radius`    | `float`            | 0.2     |                                                              |
| `cluster_stiffness` | `float`            | 0.2     |                                                              |
| `link_radius`       | `float`            | 0.1     |                                                              |
| `link_stiffness`    | `float`            | 0.5     |                                                              |
| `particle_spacing`  | `float`            | 0.02    |                                                              |

#### `def get_cloth_object()`

_Return:_ A list of commands: `[add_object, scale_object, set_flex_cloth_actor, assign_flex_container]`

```python
from tdw.librarian import ModelLibrarian
from tdw_physics.flex_dataset import FlexDataset

class MyDataset(FlexDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Your code here.
        lib = ModelLibrarian("models_special.json")
        record = lib.get_record("cloth_square")
        commands.append(self.add_cloth_object(record=record, 
                                              position={"x": 0, "y": 0, "z": 0},
                                              rotation={"x": 0, "y": 0, "z": 0},
                                              scale={"x": 1, "y": 1, "z": 1},
                                              o_id=0,
                                              mass_tesselation=1,
                                              stretch_stiffness=0.1
                                              bend_stiffness=0.1
                                              tether_stiffness=0.1,
                                              tether_give=0,
                                              pressure=0
                                              mass_scale=1))
```

| Parameter           | Type               | Default | Description                                                  |
| ------------------- | ------------------ | ------- | ------------------------------------------------------------ |
| `record`            | `ModelRecord`      |         | The model record.                                            |
| `position`          | `Dict[str, float`] |         | The initial position of the object.                          |
| `rotation`          | `Dict[str, float]` |         | The initial rotation of the object, in Euler angles.         |
| `scale`             | `Dict[str, float]` | `None`  | The object scale factor. If None, the scale is (1, 1, 1).    |
| `o_id`              | `Optional[int]`    | `None`  | The unique ID of the object. If None, a random ID is generated. |
| `mesh_tesselation`  | `int`              | 1       |                                                              |
| `stretch_stiffness` | `int`              | 0.1     |                                                              |
| `bend_stiffness`    | `int`              | 0.1     |                                                              |
| `tether_stiffness`  | `float`            | 0       |                                                              |
| `tether_give`       | `float`            | 0       |                                                              |
| `pressure`          | `float`            | 0       |                                                              |
| `mass_scale`        | `float`            | 1       |                                                              |

#### `def get_fluid_object()`

_Return:_ A list of commands: `[load_flex_fluid_from_resources, create_flex_fluid_object, assign_flex_container, step_physics]`

```python
from tdw.librarian import ModelLibrarian
from tdw_physics.flex_dataset import FlexDataset

class MyDataset(FlexDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        
        # Your code here.
        
        # Cache the pool ID to destroy it correctly.
        pool_id = Controller.get_unique_id()
        self.non_flex_objects.append(self.pool_id)
        
        # Add the pool.
        lib = ModelLibrarian("models_special.json")
        receptacle_record = lib.get_record("fluid_receptacle1x1")
        commands.append(self.add_transforms_object(record=self.receptacle_record,
                                                         position={"x": 0, "y": 0, "z": 0},
                                                         rotation={"x": 0, "y": 0, "z": 0},
                                                         o_id=self.pool_id))
        
        # Add a container here.
        
        # Add the fluid.
        fluid_id = Controller.get_unique_id()
        commands.extend(self.add_fluid_object(position={"x": 0, "y": 1.0, "z": 0},
                                              rotation={"x": 0, "y": 0, "z": 0},
                                              o_id=fluid_id,
                                              fluid_type="water"))
```

| Parameter          | Type               | Default | Description                                                  |
| ------------------ | ------------------ | ------- | ------------------------------------------------------------ |
| `record`           | `ModelRecord`      |         | The model record.                                            |
| `position`         | `Dict[str, float`] |         | The initial position of the object.                          |
| `rotation`         | `Dict[str, float]` |         | The initial rotation of the object, in Euler angles.         |
| `scale`            | `Dict[str, float]` | `None`  | The object scale factor. If None, the scale is (1, 1, 1).    |
| `o_id`             | `Optional[int]`    | `None`  | The unique ID of the object. If None, a random ID is generated. |
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

#### `MODEL_LIBRARIES`

Cache of all default model libraries, mapped to their names.

```python
from tdw_physics.utils import MODEL_LIBARIES

print(MODEL_LIBARIES["models_full.json"].get_record("iron_box").name) # iron_box
```

#### `def get_move_along_direction()`

_Return:_ A position from pos by distance d along a directional vector defined by pos, target.

```python
from tdw_physics.utils import get_move_along_direction

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
from tdw_physics.utils import get_object_look_at

o_id = 0 # Assume that the object has been already added to the scene.
p_1 = {"x": 5, "y": 0, "z": 3.4}
p_0 = get_move_along_direction(o_id=o_id, pos=p_1, noise=5)
```

| Parameter | Type               | Default | Description                                                  |
| --------- | ------------------ | ------- | ------------------------------------------------------------ |
| `o_id`    | `int`              |         | The object's ID.                                             |
| `pos`     | `Dict[str, float]` |         | The position to look at.                                     |
| `noise`   | `float`            | 0       | Rotate the object randomly by this much after applying the look_at command. |

#### `def get_args()`

_Return:_ Command line arguments common to all controllers.

```python
from tdw.physics_utils import get_args
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset

class MyDataset(RigidbodiesDataset):
    # Your code here.
    
if __name__ == "__main__":
    args = get_args("my_dataset")
    MyDataset().run(num=args.num, output_dir=args.dir, temp_path=args.temp)
```

| Parameter     | Type  | Default | Description                                                  |
| ------------- | ----- | ------- | ------------------------------------------------------------ |
| `dataset_dir` | `str` |         | If you don't provide a `--dir` argument, the default output director is: `"D:/" + dataset_dir` |

## `extract_images.py`

```python
python3 extract_images.py [ARGUMENTS]
```

Extract `_img` images from an .hdf5 file and save them to a destination directory.

| Argument | Type  | Default | Description                               |
| -------- | ----- | ------- | ----------------------------------------- |
| `--dest` | `str` |         | Root directory for the images.            |
| `--src`  | `str` |         | Root source directory of the .hdf5 files. |

