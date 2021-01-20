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
from tdw_physics.rigidbodies_dataset import (RigidbodiesDataset,
                                             get_random_xyz_transform,
                                             handle_random_transform_args)
from tdw_physics.util import MODEL_LIBRARIES, get_parser, xyz_to_arr, arr_to_xyz, str_to_xyz

from dominoes import Dominoes, MultiDominoes, get_args

MODEL_NAMES = [r.name for r in MODEL_LIBRARIES['models_flex.json'].records]

def get_tower_args(dataset_dir: str, parse=True):
    """
    Combine Tower-specific args with general Dominoes args
    """
    common = get_parser(dataset_dir, get_help=False)
    domino, domino_postproc = get_args(dataset_dir, parse=False)
    parser = ArgumentParser(parents=[common, domino], conflict_handler='resolve')

    parser.add_argument("--remove_target",
                        type=int,
                        default=1,
                        help="Whether to remove the target object")
    parser.add_argument("--collision_axis_length",
                        type=float,
                        default=3.0,
                        help="How far to put the probe and target")
    parser.add_argument("--num_blocks",
                        type=int,
                        default=3,
                        help="Number of rectangular blocks to build the tower base with")
    parser.add_argument("--tower_cap",
                        type=str,
                        default=None,
                        help="Object types to use as a capper on the tower")

    def postprocess(args):

        # whether to use a cap object on the tower
        if args.tower_cap is not None:
            cap_list = args.tower_cap.split(',')
            assert all([t in MODEL_NAMES for t in cap_list]), \
                "All target object names must be elements of %s" % MODEL_NAMES
            args.tower_cap = cap_list
        else:
            args.tower_cap = []

        return args

    args = parser.parse_args()
    args = domino_postproc(args)
    args = postprocess(args)

    return args

class Tower(MultiDominoes):

    def __init__(self,
                 port: int = 1071,
                 num_blocks=3,
                 tower_cap=[],
                 **kwargs):

        Dominoes.__init__(self, port=port, **kwargs)

        # block typs
        self._middle_types = self.get_types(['cube'])
        self.middle_type = "cube"

        # how many blocks in tower, sans cap
        self.num_blocks = num_blocks

        # whether to use a cap
        if len(tower_cap):
            self.use_cap = True
            self._cap_types = self.get_types(tower_cap)
        else:
            self.use_cap = False

    def clear_static_data(self) -> None:
        super().clear_static_data()

        self.cap_type = None

    def _write_static_data(self, static_group: h5py.Group) -> None:
        Dominoes._write_static_data(self, static_group)

        static_group.create_dataset("cap_type", data=self.cap_type)
        static_group.create_dataset("use_cap", data=self.use_cap)

    def _build_intermediate_structure(self) -> List[dict]:
        self.middle_color = self.probe_color if self.monochrome else None
        self.cap_color = self.target_color
        commands = []

        commands.extend(self._build_stack())
        commands.extend(self._add_cap())

        return commands

    def _build_stack(self) -> List[dict]:
        commands = []

        height = 0.
        for m in range(self.num_blocks):
            record, data = self.random_primitive(
                self._middle_types,
                scale={"x":0.5, "y":0.5, "z":0.5},
                color=self.middle_color,
                exclude_color=self.target_color)
            o_id, scale, rgb = [data[k] for k in ["id", "scale", "color"]]
            block_pos = {"x": 0., "y": height, "z": 0.}
            block_rot = {"x": 0., "y": 0., "z": 0.}
            commands.extend(
                self.add_physics_object(
                    record=record,
                    position=block_pos,
                    rotation=block_rot,
                    mass=random.uniform(2,7),
                    dynamic_friction=random.uniform(0, 0.9),
                    static_friction=random.uniform(0, 0.9),
                    bounciness=random.uniform(0, 1),
                    o_id=o_id))

            # Scale the object and set its color.
            commands.extend([
                {"$type": "set_color",
                 "color": {"r": rgb[0], "g": rgb[1], "b": rgb[2], "a": 1.},
                 "id": o_id},
                {"$type": "scale_object",
                 "scale_factor": scale,
                 "id": o_id}])

            print("placed middle object %s" % str(m+1))

            # update height
            height += scale["y"]

        self.tower_height = height

        return commands

    def _add_cap(self) -> List[dict]:
        commands = []

        record, data = self.random_primitive(
            self._cap_types,
            scale=[0.5,0.5],
            color=self.target_color)
        o_id, scale, rgb = [data[k] for k in ["id", "scale", "color"]]
        self.cap_type = data["name"]

        commands.extend(
            self.add_physics_object(
                record=record,
                position={
                    "x": 0.,
                    "y": self.tower_height,
                    "z": 0.
                },
                rotation={"x":0.,"y":0.,"z":0.},
                mass=random.uniform(2,7),
                dynamic_friction=random.uniform(0, 0.9),
                static_friction=random.uniform(0, 0.9),
                bounciness=random.uniform(0, 1),
                o_id=o_id))

        # Scale the object and set its color.
        commands.extend([
            {"$type": "set_color",
             "color": {"r": rgb[0], "g": rgb[1], "b": rgb[2], "a": 1.},
             "id": o_id},
            {"$type": "scale_object",
             "scale_factor": scale,
             "id": o_id}])

        if not self.use_cap:
            commands.append(
                {"$type": self._get_destroy_object_command_name(o_id),
                 "id": int(o_id)})
            self.object_ids = self.object_ids[:-1]
        else:
            self.tower_height += scale["y"]

        return commands

if __name__ == "__main__":

    args = get_tower_args("towers")

    TC = Tower(
        # tower specific
        num_blocks=args.num_blocks,
        tower_cap=args.tower_cap,
        # domino specific
        target_objects=args.target,
        probe_objects=args.probe,
        target_scale_range=args.tscale,
        target_rotation_range=args.trot,
        probe_scale_range=args.pscale,
        target_color=args.color,
        collision_axis_length=args.collision_axis_length,
        force_scale_range=args.fscale,
        force_angle_range=args.frot,
        force_offset=args.foffset,
        force_offset_jitter=args.fjitter,
        remove_target=bool(args.remove_target),
        ## not scenario-specific
        randomize=args.random,
        seed=args.seed,
        camera_radius=args.camera_distance,
        camera_min_angle=args.camera_min_angle,
        camera_max_angle=args.camera_max_angle,
        camera_min_height=args.camera_min_height,
        camera_max_height=args.camera_max_height,
        monochrome=args.monochrome
    )
    print(TC.num_blocks, [r.name for r in TC._cap_types])

    if bool(args.run):
        TC.run(num=args.num,
               output_dir=args.dir,
               temp_path=args.temp,
               width=args.width,
               height=args.height)
    else:
        TC.communicate({"$type": "terminate"})
