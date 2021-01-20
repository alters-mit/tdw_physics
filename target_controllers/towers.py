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
    parser.add_argument("--mscale",
                        type=str,
                        default="[0.5,0.5]",
                        help="Scale or scale range for rectangular blocks to sample from")
    parser.add_argument("--mgrad",
                        type=float,
                        default=0.0,
                        help="Size of block scale gradient going from top to bottom of tower")
    parser.add_argument("--tower_cap",
                        type=str,
                        default="bowl",
                        help="Object types to use as a capper on the tower")
    parser.add_argument("--spacing_jitter",
                        type=float,
                        default=0.25,
                        help="jitter in how to space middle objects, as a fraction of uniform spacing")
    parser.add_argument("--mrot",
                        type=str,
                        default="[-45,45]",
                        help="comma separated list of initial middle object rotation values")
    parser.add_argument("--probe",
                        type=str,
                        default="sphere",
                        help="comma-separated list of possible target objects")
    parser.add_argument("--pmass",
                        type=str,
                        default="[2.0,4.0]",
                        help="scale of probe objects")
    parser.add_argument("--pscale",
                        type=str,
                        default="[0.2,0.4]",
                        help="scale of probe objects")
    parser.add_argument("--fscale",
                        type=str,
                        default="[4.0,15.0]",
                        help="range of scales to apply to push force")
    parser.add_argument("--frot",
                        type=str,
                        default="[-10,10]",
                        help="range of angles in xz plane to apply push force")
    parser.add_argument("--foffset",
                        type=str,
                        default="0.0,0.5,0.0",
                        help="offset from probe centroid from which to apply force, relative to probe scale")
    parser.add_argument("--fjitter",
                        type=float,
                        default=0.0,
                        help="jitter around object centroid to apply force")
    parser.add_argument("--camera_distance",
                        type=float,
                        default=2.5,
                        help="radial distance from camera to centerpoint")
    parser.add_argument("--camera_min_angle",
                        type=float,
                        default=0,
                        help="minimum angle of camera rotation around centerpoint")
    parser.add_argument("--camera_max_angle",
                        type=float,
                        default=60,
                        help="maximum angle of camera rotation around centerpoint")


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
                 middle_scale_range=[0.5,0.5],
                 middle_scale_gradient=0.0,
                 tower_cap=[],
                 **kwargs):

        super().__init__(port=port, middle_scale_range=middle_scale_range, **kwargs)

        # probe and target different colors
        self.match_probe_and_target_color = False

        # block types
        self._middle_types = self.get_types(['cube'])
        self.middle_type = "cube"

        # how many blocks in tower, sans cap
        self.num_blocks = num_blocks

        # how to scale the blocks
        self.middle_scale_gradient = middle_scale_gradient

        # whether to use a cap
        if len(tower_cap):
            self.use_cap = True
            self._cap_types = self.get_types(tower_cap)
        else:
            self.use_cap = False

        # scale the camera height
        self.camera_min_height *= 0.5 * (self.num_blocks + int(self.use_cap))
        self.camera_max_height *= 0.5 * (self.num_blocks + int(self.use_cap))
        self.camera_aim = 0.25 * (self.num_blocks + int(self.use_cap))
        self.camera_aim = {"x": 0., "y": self.camera_aim, "z": 0.}

    def clear_static_data(self) -> None:
        super().clear_static_data()

        self.cap_type = None

    def _write_static_data(self, static_group: h5py.Group) -> None:
        Dominoes._write_static_data(self, static_group)

        static_group.create_dataset("cap_type", data=self.cap_type)
        static_group.create_dataset("use_cap", data=self.use_cap)

    def _build_intermediate_structure(self) -> List[dict]:
        self.middle_color = self.random_color(exclude=self.target_color) if self.monochrome else None
        self.cap_color = self.target_color
        commands = []

        commands.extend(self._build_stack())
        commands.extend(self._add_cap())

        return commands

    def _get_block_position(self, scale, y):
        jitter = lambda: random.uniform(-self.spacing_jitter, self.spacing_jitter)
        jx, jz = [scale["x"]*jitter(), scale["z"]*jitter()]
        return {"x": jx, "y": y, "z": jz}

    def _build_stack(self) -> List[dict]:
        commands = []
        height = 0.

        # build the block scales
        self.block_scales = [random.uniform(self.middle_scale_range[0], self.middle_scale_range[1])
                             for _ in range(self.num_blocks)]
        mid = self.num_blocks / 2.0
        self.block_scales = [s + (mid - i) * self.middle_scale_gradient for i,s in enumerate(self.block_scales)]

        # place the blocks
        for m in range(self.num_blocks):
            record, data = self.random_primitive(
                self._middle_types,
                scale=self.block_scales[m],
                color=self.middle_color,
                exclude_color=self.target_color)
            o_id, scale, rgb = [data[k] for k in ["id", "scale", "color"]]
            block_pos = self._get_block_position(scale, height)
            block_rot = self.get_y_rotation(self.middle_rotation_range)
            commands.extend(
                self.add_physics_object(
                    record=record,
                    position=block_pos,
                    rotation=block_rot,
                    mass=random.uniform(4.5,4.5),
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

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 350

if __name__ == "__main__":

    args = get_tower_args("towers")

    TC = Tower(
        # tower specific
        num_blocks=args.num_blocks,
        tower_cap=args.tower_cap,
        spacing_jitter=args.spacing_jitter,
        middle_rotation_range=args.mrot,
        middle_scale_range=args.mscale,
        middle_scale_gradient=args.mgrad,
        # domino specific
        target_objects=args.target,
        probe_objects=args.probe,
        target_scale_range=args.tscale,
        target_rotation_range=args.trot,
        probe_scale_range=args.pscale,
        probe_mass_range=args.pmass,
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
