from argparse import ArgumentParser
import h5py
import json
import copy
import importlib
import numpy as np
from enum import Enum
import random
from typing import List, Dict, Tuple
from weighted_collection import WeightedCollection
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelRecord
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset
from tdw_physics.util import MODEL_LIBRARIES, get_parser, xyz_to_arr, arr_to_xyz

MODEL_NAMES = [r.name for r in MODEL_LIBRARIES['models_flex.json'].records]
RAMP_NAMES = [r.name for r in MODEL_LIBRARIES['models_full.json'].records if r.name.startswith('ramp')]

def get_args(dataset_dir: str):
    """
    Combine Drop-specific arguments with controller-common arguments
    """
    common = get_parser(dataset_dir, get_help=False)
    parser = ArgumentParser(parents=[common])

    parser.add_argument("--ramp",
                        type=str,
                        default=None,
                        help="comma-separated list of possible target objects")

    args = parser.parse_args()

    if args.ramp is not None:
        ramp_list = args.ramp.split(',')
        assert all([t in RAMP_NAMES for t in ramp_list]), \
            "All target object names must be elements of %s" % RAMP_NAMES
        args.ramp = ramp_list
    else:
        args.ramp = RAMP_NAMES

    return args

class RampCollide(RigidbodiesDataset):

    def __init__(self,
                port: int = 1071,
                ramp_objects=RAMP_NAMES,
                **kwargs):

        ## initializes static data and RNG
        super().__init__(port=port, **kwargs)

        self.ramp_objects = ramp_objects
        print("ramp objects", self.ramp_objects)

    def clear_static_data(self) -> None:
        super().clear_static_data()
        self.ramp_type = None

    def get_field_of_view(self) -> float:
        return 55

    def get_scene_initialization_commands(self) -> List[dict]:
        return [self.get_add_scene(scene_name="box_room_2018"),
                {"$type": "set_aperture",
                 "aperture": 8},
                {"$type": "set_post_exposure",
                 "post_exposure": 0.4},
                {"$type": "set_ambient_occlusion_intensity",
                 "intensity": 0.175},
                {"$type": "set_ambient_occlusion_thickness_modifier",
                 "thickness": 3.5}]

    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []

        # place a ramp
        commands.extend(self._place_ramp_object())

        # Choose and place a target object.
        # commands.extend(self._place_target_object())

        # Choose and drop an object.
        #commands.extend(self._place_drop_object())

        # Teleport the avatar to a reasonable position based on the drop height.
        a_pos = self.get_random_avatar_position(radius_min=0.5,
                                                radius_max=1,
                                                angle_min=0,
                                                angle_max=10,
                                                y_min=0.5,
                                                y_max=1,
                                                center=TDWUtils.VECTOR3_ZERO)
        print("avatar pos", a_pos)

        cam_aim = {"x": 0, "y": 0, "z": 0}
        commands.extend([
            {"$type": "teleport_avatar_to",
             "position": a_pos},
            {"$type": "look_at_position",
             "position": cam_aim},
            {"$type": "set_focus_distance",
             "focus_distance": TDWUtils.get_distance(a_pos, cam_aim)}
        ])
        return commands

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return []

    def _write_static_data(self, static_group: h5py.Group) -> None:
        super()._write_static_data(static_group)
        static_group.create_dataset("ramp_type", data=self.ramp_type)

    def _write_frame(self,
                     frames_grp: h5py.Group,
                     resp: List[bytes],
                     frame_num: int) -> \
            Tuple[h5py.Group, h5py.Group, dict, bool]:
        frame, objs, tr, sleeping = super()._write_frame(frames_grp=frames_grp, resp=resp, frame_num=frame_num)
        # If this is a stable structure, disregard whether anything is actually moving.
        return frame, objs, tr, sleeping and frame_num < 300

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 300

    def _place_ramp_object(self) -> List[dict]:
        """
        Place a ramp at the room center.
        """
        recs = MODEL_LIBRARIES["models_full.json"].records
        self._ramp_types = [r for r in recs if r.name in self.ramp_objects]

        record, data = self.random_primitive(self._ramp_types)
        o_id, scale, rgb = [data[k] for k in ["id", "scale", "color"]]
        self.ramp_type = data["name"]
        print("obj scale",scale)
        print("obj name:", self.ramp_type)

        # add the object
        commands = []

        commands.append(
            # self.add_physics_object(
            self.add_transforms_object(
                record=record,
                position={
                    "x": 0.,
                    "y": 0.,
                    "z": 0.
                },
                rotation=TDWUtils.VECTOR3_ZERO,
                # mass=10,
                # dynamic_friction=random.uniform(0, 0.9),
                # static_friction=random.uniform(0, 0.9),
                # bounciness=0,
                o_id=o_id))

        print(commands)

        # Scale the object and set its color.
        # commands.extend([
        #     {"$type": "scale_object",
        #      "scale_factor": scale,
        #      "id": o_id}])

        return commands

if __name__ == "__main__":
    args = get_args("ramp_scene")
    rc = RampCollide(ramp_objects=args.ramp)

    if bool(args.run):
        rc.run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
    else:
        rc.communicate({"$type": "terminate"})
