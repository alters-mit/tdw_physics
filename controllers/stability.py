import h5py
import numpy as np
from enum import Enum
import random
from typing import List, Dict, Tuple
from weighted_collection import WeightedCollection
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelRecord
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset
from tdw_physics.util import MODEL_LIBRARIES, get_args

class _StackType(Enum):
    """
    The stability type.
    """

    stable = 1
    maybe_stable = 2
    base_stable = 3
    unstable = 4


class Stability(RigidbodiesDataset):
    """
    Create a stack of primitives of varying stabilities.
    The controller will randomly pick one of four stability options per-trial:

    1. Stable: The controller will try to choose objects that are "stable" (can support objects above and below).
       The top object can be a maybe-stable or base-stable object (objects with a flat bottom face, e.g. a cone).
    2. Maybe Stable: The controller will prefer "stable" objects but will sometimes add less-stable objects.
    3. Base Stable: The controller will add stable, maybe-stable, or base-stable objects.
    4. Unstable: The controller will randomly select objects regardless of stability.
    """

    # The objects are reliably stable.
    STABLE: List[ModelRecord] = []
    # These objects are only sometimes stable.
    MAYBE_STABLE: List[ModelRecord] = []
    # These objects only stable at their base.
    BASE_STABLE: List[ModelRecord] = []
    # These objects are generally unstable.
    UNSTABLE: List[ModelRecord] = []
    for record in MODEL_LIBRARIES["models_flex.json"].records:
        if record.name in ["cube", "cylinder", "pentagon"]:
            STABLE.append(record)
        elif record.name in ["bowl", "pipe", "torus"]:
            MAYBE_STABLE.append(record)
        elif record.name in ["cone", "pyramid", "triangular_prism"]:
            BASE_STABLE.append(record)
        else:
            UNSTABLE.append(record)
    STABLE_LISTS: Dict[_StackType, List[ModelRecord]] = {_StackType.stable: STABLE,
                                                         _StackType.maybe_stable: MAYBE_STABLE,
                                                         _StackType.base_stable: BASE_STABLE,
                                                         _StackType.unstable: UNSTABLE}

    def __init__(self, port: int = 1071):
        self._stack_type: _StackType = _StackType.stable

        super().__init__(port=port)

        ## object colors
        self.colors = np.empty(dtype=np.float32, shape=(0,3))

    def clear_static_data(self) -> None:
        super().clear_static_data()

        ## object colors
        self.colors = np.empty(dtype=np.float32, shape=(0,3))

    def get_field_of_view(self) -> float:
        return 55

    def get_scene_initialization_commands(self) -> List[dict]:
        return [self.get_add_scene(scene_name="box_room_2018"),
                {"$type": "set_aperture",
                 "aperture": 4.8},
                {"$type": "set_post_exposure",
                 "post_exposure": 0.4},
                {"$type": "set_ambient_occlusion_intensity",
                 "intensity": 0.175},
                {"$type": "set_ambient_occlusion_thickness_modifier",
                 "thickness": 3.5}]

    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Get a random stack type.
        self._stack_type = random.choice([st for st in _StackType])
        num_objects = random.randint(4, 7)

        maybe_stable = WeightedCollection(_StackType)
        maybe_stable.add_many({_StackType.stable: 4,
                               _StackType.maybe_stable: 4,
                               _StackType.base_stable: 1,
                               _StackType.unstable: 1})
        y = 0
        for i in range(num_objects):
            # Choose the next object based on the target stability of the stack.
            if self._stack_type == _StackType.stable:
                # Every object expect the top is "stable".
                if i < num_objects - 1:
                    record = random.choice(self.STABLE)
                # Pick something with a stable bottom for the top of the stack.
                else:
                    records = random.choice([self.STABLE, self.MAYBE_STABLE, self.BASE_STABLE])
                    record = random.choice(records)
            elif self._stack_type == _StackType.maybe_stable:
                # Get an object that is *likely* to be "stable".
                if i < num_objects - 1:
                    records = self.STABLE_LISTS[maybe_stable.get()]
                    record = random.choice(records)
                # The top object can be anything.
                else:
                    records = random.choice([self.STABLE, self.MAYBE_STABLE, self.BASE_STABLE, self.UNSTABLE])
                    record = random.choice(records)
            elif self._stack_type == _StackType.base_stable:
                # Every object except the top *might* be "stable".
                if i < num_objects - 1:
                    records = random.choice([self.STABLE, self.MAYBE_STABLE])
                    record = random.choice(records)
                # The top object can be anything stable.
                else:
                    records = random.choice([self.STABLE, self.MAYBE_STABLE, self.BASE_STABLE])
                    record = random.choice(records)
            elif self._stack_type == _StackType.unstable:
                # The record can be anything.
                records = random.choice([self.STABLE, self.MAYBE_STABLE, self.BASE_STABLE, self.UNSTABLE])
                record = random.choice(records)
            else:
                raise Exception(f"Not defined: {self._stack_type}")

            # Add the object.
            scale = random.uniform(0.2, 0.23)
            commands.extend(self._add_object_to_stack(record=record, y=y, scale=scale))
            # Increment the starting y positional coordinate by the previous object's height.
            y += record.bounds['top']['y'] * scale

        # Teleport the avatar to a reasonable position based on the height of the stack.
        # Look at the center of the stack, then jostle the camera rotation a bit.
        # Apply a slight force to the base object.
        a_pos = self.get_random_avatar_position(radius_min=y,
                                                radius_max=1.3 * y,
                                                y_min=y / 4,
                                                y_max=y / 3,
                                                center=TDWUtils.VECTOR3_ZERO)
        cam_aim = {"x": 0, "y": y * 0.5, "z": 0}
        commands.extend([{"$type": "teleport_avatar_to",
                          "position": a_pos},
                         {"$type": "look_at_position",
                          "position": cam_aim},
                         {"$type": "set_focus_distance",
                          "focus_distance": TDWUtils.get_distance(a_pos, cam_aim)},
                         {"$type": "rotate_sensor_container_by",
                          "axis": "pitch",
                          "angle": random.uniform(-5, 5)},
                         {"$type": "rotate_sensor_container_by",
                          "axis": "yaw",
                          "angle": random.uniform(-5, 5)},
                         {"$type": "apply_force_to_object",
                          "force": {"x": random.uniform(-0.05, 0.05),
                                    "y": 0,
                                    "z": random.uniform(-0.05, 0.05)},
                          "id": int(self.object_ids[0])}])
        return commands

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return []

    def _write_static_data(self, static_group: h5py.Group) -> None:
        super()._write_static_data(static_group)

        ## color of primitive objects
        static_group.create_dataset("color", data=self.colors)

    def _write_frame(self, frames_grp: h5py.Group, resp: List[bytes], frame_num: int) -> \
            Tuple[h5py.Group, h5py.Group, dict, bool]:
        frame, objs, tr, sleeping = super()._write_frame(frames_grp=frames_grp, resp=resp, frame_num=frame_num)
        # If this is a stable structure, disregard whether anything is actually moving.
        return frame, objs, tr, sleeping and frame_num < 300

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 500

    def _add_object_to_stack(self, record: ModelRecord, y: float, scale: float) -> List[dict]:
        """
        Add a primitive to the stack. Assign random physics values and colors.

        :param record: The model record.
        :param y: The object's y positional coordinate.
        :param scale: The object's scale.

        :return: A list of commands to add the object.
        """

        o_id = self.get_unique_id()

        # Set a random color.
        rgb = np.array([random.random(), random.random(), random.random()])
        self.colors = np.concatenate([self.colors, rgb.reshape((1,3))], axis=0)
        print("object %s color: %s" % (o_id, rgb))

        # Add the object with random physics values.
        commands = []
        commands.extend(self.add_physics_object(record=record,
                                                position={"x": random.uniform(-0.02, 0.02),
                                                          "y": y,
                                                          "z": random.uniform(-0.02, 0.02)},
                                                rotation={"x": 0,
                                                          "y": random.uniform(0, 360),
                                                          "z": 0},
                                                mass=random.uniform(2, 7),
                                                dynamic_friction=random.uniform(0, 0.9),
                                                static_friction=random.uniform(0, 0.9),
                                                bounciness=random.uniform(0, 1),
                                                o_id=o_id))

        # Scale the object.
        commands.extend([{"$type": "set_color",
                          "color": {"r": rgb[0], "g": rgb[1], "b": rgb[2], "a": 1.0},
                          "id": o_id},
                         {"$type": "scale_object",
                          "id": o_id,
                          "scale_factor": {"x": scale, "y": scale, "z": scale}}])
        return commands


if __name__ == "__main__":
    args = get_args("stability")
    ## if using random trials
    if not bool(args.random):
        print("seed", args.seed)
        random.seed(args.seed)
    Stability().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
