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

## Controllers

| Scenario        | Description                                                  | Script                                                       | Type                 |
| --------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | -------------------- |
| Toy Collisions  | Three randomly "toys" are created with random physics values. A force of randomized magnitude is applied to one toy, aimed at another. | `toy_collisions.py`                                          | `RigidbodiesDataset` |
| Occlusion       | Random "big" and "small" models are added. The small object is at random distance and angle from the big object. The camera is placed at a random distance and rotated such that the "big" model occludes the "small" model in some frames. | `occlusion.py`                                               | `TransformsDataset`  |
| Permanence      | A ball rolls behind an occluding object and then reemerges. The occluder is randomly chosen from a list. The ball has a random starting distance, visual material, physics values, and initial force. | `permanence.py`                                              | `RigidbodiesDataset` |
| Shadows         | A ball is added in a scene with a randomized lighting setup. The ball has a random initial position, force vector, physics values, and visual materials. The force vectors are such that the ball typically rolls through differently-lit areas, i.e. a bright spot to a shadowy spot. | `shadows.py`                                                 | `RigidbodiesDataset` |
| Falling         | Objects are added to a scene. "Small" objects are given a random upwards force vector, and fall downward under gravity. _Note: There are two controllers. One is a proc-gen setup and one is nicer-looking but assembled by-hand._ | `table_scripted.py --scenario fall`<br/>*and*<br/>`table_proc_gen.py --scenario fall` | `RigidbodiesDataset` |
| Sliding/Rolling | Objects are placed on a table. A random force is applied at a random point on the table. The objects slide or roll down. _Note: There are two controllers. One is a proc-gen setup and one is nicer-looking but assembled by-hand._ | `table_scripted.py --scenario tilt`<br>*and*<br>`table_proc_gen.py --scenario tilt` | `RigidbodiesDataset` |
| Bouncing        | 4 "ramp" objects are placed randomly in a room. 2-6 "toy" objects are added to the room in mid-air and given random physics values and force vectors such that they will bounce around the scene. | `bouncing.py`                                                | `RigidbodiesDataset` |
| Stability       | A stack of 4-7 objects is created. The objects are all simple shapes with random colors. The stack is built according to a "stability" algorithm; some algorithms yield more balanced stacks than others. The stack falls down, or doesn't. *(See comments in controller)* | `stability.py`                                               | `RigidbodiesDataset` |
| Draping/Folding | A cloth falls; 80% of the time onto another object. The cloth has random physics values. | `draping.py`                                                 | `FlexDataset`        |
| Dragging        | A rigid object is dragged or moved by pulling on a cloth under it. The cloth and the object have random physics values. The cloth is pulled in by a random force vector. | `dragging.py`                                                | `FlexDataset`        |
| Containment     | A small object is contained and rattles around in a larger object, such as a bowl. The small object has random physics values. The bowl has random force vectors. | `containment.py`                                             | `RigidbodiesDataset` |
| Linking         | *Multiple objects are connected, e.g. by chain links, and can only move a little relative to each other* | WIP                                                          |                      |
| Squishing       | Squishy objects deform and are restored to original shape depending on applied forces (e.g. squished when something else is on top of them or when they impact a barrier). Objects are given random "pressure" values. | `squishing.py`                                               | `FlexDataset`        |
| Submerging      | Objects sink or float in different types of fluids.          | `submerging.py`                                              | `FlexDataset`        |
