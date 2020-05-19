# tdw_physics

These classes create a generic structure for generating physics datasets using TDW. They aim to:

1. Simplify the process of writing many similar controllers.
2. Ensure uniform output data organization across similar controllers.

## Installation

1. Clone the TDWBase repo and download the latest build.
2. Clone this repo.
3. `cd path/to/tdw_physics`
4. `pip3 install -e .` (This installs the `tdw_physics` module).

## Usage

tdw_physics provides abstract Controller classes. To write your own physics dataset controller, you should create a superclass of the appropriate controller.

| Abstract Controller  | Output Data                                                  |
| -------------------- | ------------------------------------------------------------ |
| `RigidbodiesDataset` | `Tranforms`, `Images`, `CameraMatrices`, `Rigidbodies`, `Collision`, `EnvironmentCollision` |
| `TransformsDataset`  | `Transforms`, `Images`, `CameraMatrices`                     |

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

## How to Create a Dataset Controller

_Regardless_ of which abstract controller you use, you must override the following functions:

| Function                                     | Type         | Return                                                       |
| -------------------------------------------- | ------------ | ------------------------------------------------------------ |
| `get_scene_initialization_commands()`        | `List[dict]` | A list of commands to initialize the dataset's scene. These commands are sent only once in the entire dataset run (e.g. post-processing commands). |
| `get_trial_initialization_commands()`        | `List[dict]` | A list of commands to initialize a single trial. This should include all object setup, avatar position and camera rotation, etc. You do not need to include any cleanup commands such as `destroy_object`; that is handled automatically elsewhere. _NOTE:_ You must use alternate functions to add objects; see below. |
| `get_per_frame_commands(resp: List[bytes]):` | `List[dict]` | Commands to send per-frame, based on the response from the build. |
| `get_field_of_view()`                        | `float`      | The avatar's field of view value.                            |

***

## `RigidbodiesDataset`

```python
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset

class MyDataset(RigidbodiesDataset):
    def get_scene_initialization_commands(self) -> List[dict]:
        # Your code here.

    def get_trial_initialization_commands(self) -> List[dict]:
        # Your code here.

    def get_per_frame_commands(self, frame: int) -> List[dict]:
        # Your code here.

    def get_field_of_view(self, resp: List[bytes]) -> float:
        # Your code here.
```

A dataset creator that receives and writes per frame: `Tranforms`, `Images`, `CameraMatrices`, `Rigidbodies`, `Collision`, and `EnvironmentCollision`.

A `RigidbodiesDataset` trial ends when all objects are "sleeping" i.e. non-moving, or after 1000 frames. Objects that have fallen below the scene's floor (y < -1) are ignored.

### Adding objects

**`Controller.add_object()` and `Conroller.get_add_object()` will throw an exception.** You must instead use `RigidbodiesDataset.add_physics_object()` or `RigidbodiesDataset.add_physics_object_default()`. This will automatically cache the object ID, allowing the object to be destroyed at the end of the trial.

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

***

## `TransformsDataset`

```python
from tdw_physics.transforms_dataset import TransformsDataset

class MyDataset(TransformsDataset):
    def get_scene_initialization_commands(self) -> List[dict]:
        # Your code here.

    def get_trial_initialization_commands(self) -> List[dict]:
        # Your code here.

    def get_per_frame_commands(self, frame: int) -> List[dict]:
        # Your code here.

    def get_field_of_view(self, resp: List[bytes]) -> float:
        # Your code here.
```

A dataset creator that receives and writes per frame: `Transforms`, `Images`, `CameraMatrices`. 

A `TransformsDataset` trial has no "end" condition based on trial output data; you will need to define this yourself. Typically, though, you will want to use a physics-based abstract class such as `RigidbodiesDataset`.

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

