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
| Drop  | Three randomly "toys" are created with random physics values. A force of randomized magnitude is applied to one toy, aimed at another. | `toy_collisions.py`
