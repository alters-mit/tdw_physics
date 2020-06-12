# tdw_physics controllers

## Arguments

These arguments are common for every controller.

| Argument   | Type  | Default                                                      | Description                          |
| ---------- | ----- | ------------------------------------------------------------ | ------------------------------------ |
| `--dir`    | `str` | `"D:/" + dataset_dir` <br>`dataset_dir` is defined by each controller. | Root output directory.               |
| `--num`    | `int` | 3000                                                         | The number of trials in the dataset. |
| `--temp`   | `str` | D:/temp.hdf5                                                 | Temp path for incomplete files.      |
| `--width`  | `int` | 256                                                          | Screen width in pixels.              |
| `--height` | `int` | 256                                                          | Screen height in pixels.             |

## List of controllers

| Scenario        | Description                                                  | Script                                                       |
| --------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| Toy Collisions  | Objects with realistic shapes and textures move around a realistic playroom. (Imagine an invisible baby taking one object at a time and pushing it around, including colliding it with the other objects in the scene.) | `toy_collisions.py`                                          |
| Occlusion       | Two objects and a moving camera. One object occludes the other. | `occlusion.py`                                               |
| Permanence      | An object moves (e.g. rolls) behind an occluder, then reemerges on the other side; totally disappears for some time | `permanence.py`                                              |
| Shadows         | An object moves between areas of different lighting.         | `shadows.py`                                                 |
| Falling         | Objects are pushed upward and fall downward under gravity. _Note: There are two controllers. One is a proc-gen setup and one is nicer-looking but assembled by-hand._ | `table_scripted.py --scenario fall`<br/>*and*<br/>`table_proc_gen.py --scenario fall` |
| Sliding/Rolling | Objects are pushed horizontally or slide down a table. _Note: There are two controllers. One is a proc-gen setup and one is nicer-looking but assembled by-hand._ | `table_scripted.py --scenario tilt`<br>*and*<br>`table_proc_gen.py --scenario tilt` |
| Bouncing        | Objects collide with floors, ramps, and walls and bounce around. | `bouncing.py`                                                |
| Stability       | Stacks of objects that fall or don't; Objects balanced or not. *(See comments in controller)* | `stability.py`                                               |
| Draping/Folding | A cloth falls; 80% of the time onto another object.          | `draping.py`                                                 |
| Dragging        | A rigid object is dragged or moved by pulling on a cloth under it |                                                              |
| Containment     | A small object is contained and rattles around in a larger object, such as a bowl | `containment.py`                                             |
| Linking         | Multiple objects are connected, e.g. by chain links, and can only move a little relative to each other |                                                              |
| Squishing       | Squishy objects deform and are restored to original shape depending on applied forces (e.g. squished when something else is on top of them or when they impact a barrier) |                                                              |
| Submerging      | Objects sink or float in different types of fluids.          | `submerging.py`                                              |
