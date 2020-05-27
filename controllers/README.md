# tdw_physics controllers

## Arguments

These arguments are common for every controller.

| Argument | Type  | Default                                                      | Description                          |
| -------- | ----- | ------------------------------------------------------------ | ------------------------------------ |
| `--dir`  | `str` | `"D:/" + dataset_dir` <br>`dataset_dir` is defined by each controller. | Root output directory.               |
| `--num`  | `int` | 3000                                                         | The number of trials in the dataset. |
| `--temp` | `str` | D:/temp.hdf5                                                 | Temp path for incomplete files.      |

#### `table_scripted.py` and `table_proc_gen.py`

The "table controllers" have an additional argument:

| Argument     | Type  | Default | Choices      | Description                       |
| ------------ | ----- | ------- | ------------ | --------------------------------- |
| `--scenario` | `str` | tilt    | tilt<br>fall | The type of scenario (see below). |

## List of controllers

| Scenario        | Description                                                  | Script                                                       |
| --------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| Toy Collisions  | 2-3 "toy" objects spawn in a room. One object collides with another. | `toy_collisions.py`                                          |
| Occlusion       | Two objects and a moving camera. One object occludes the other. | `occlusion.py`                                               |
| Permanence      | An object moves behind an occluder, then reemerges on the other side. |                                                              |
| Shadows         | An object moves (e.g. rolls) into or out of a shadow or spotlight |                                                              |
| Falling         | A table and table settings (chairs, plates, etc.) are generated. In the scripted scene, the setup is mostly pre-assigned. In the proc-gen scene, the setup is procedural.<br/><br/>Launch small objects into the air and let them fall. | `table_scripted.py --scenario fall`<br/>*and*<br/>`table_proc_gen.py --scenario fall` |
| Sliding/Rolling | A table and table settings (chairs, plates, etc.) are generated. In the scripted scene, the setup is mostly pre-assigned. In the proc-gen scene, the setup is procedural.<br><br>Tip the table and let the objects slide and roll off of it. | `table_scripted.py --scenario tilt`<br>*and*<br>`table_proc_gen.py --scenario tilt` |
| Bouncing        | Objects collide with floors, ramps, and walls and bounce around. | `bouncing.py`                                                |
| Stability       | Stacks of objects that fall or don't; Objects balanced or not. *(See comments in controller)* | `stability.py`                                               |
| Draping         | A cloth falls on top of one or more rigid objects            |                                                              |
| Folding         | A cloth takes on different shapes by folding over itself     |                                                              |
| Dragging        | A rigid object is dragged or moved by pulling on a cloth under it |                                                              |
| Containment     | A small object is contained and rattles around in a larger object (such as a bowl). | `containment.py`                                             |
| Linking         | Multiple objects are connected, e.g. by chain links, and can only move a little relative to each other |                                                              |
| Squishing       | Squishy objects deform and are restored to original shape depending on applied forces (e.g. squished when something else is on top of them or when they impact a barrier) |                                                              |
| Submerging      | Objects sink or float in fluid                               |                                                              |
