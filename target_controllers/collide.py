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
from tdw.librarian import ModelRecord, MaterialLibrarian
from tdw_physics.rigidbodies_dataset import (RigidbodiesDataset,
                                             get_random_xyz_transform,
                                             handle_random_transform_args)
from tdw_physics.util import MODEL_LIBRARIES, get_parser, xyz_to_arr, arr_to_xyz, str_to_xyz

from dominoes import Dominoes, MultiDominoes, get_args

MODEL_NAMES = [r.name for r in MODEL_LIBRARIES['models_flex.json'].records]

def get_collide_args(dataset_dir: str, parse=True):
    """
    Combine Tower-specific args with general Dominoes args
    """
    common = get_parser(dataset_dir, get_help=False)
    domino, domino_postproc = get_args(dataset_dir, parse=False)
    parser = ArgumentParser(parents=[common, domino], conflict_handler='resolve')

    parser.add_argument("--collision_axis_length",
                        type=float,
                        default=2.0,
                        help="How far to put the probe and target")
    parser.add_argument("--middle",
                        type=str,
                        default="cylinder",
                        help="comma-separated list of possible middle objects")
    parser.add_argument("--mscale",
                        type=str,
                        default="0.1,0.5,0.25",
                        help="Scale or scale range for middle object to sample from")
    parser.add_argument("--mrot",
                        type=str,
                        default="[-45,45]",
                        help="comma separated list of initial middle object rotation values")
    parser.add_argument("--horizontal",
                        type=int,
                        default=1,
                        help="whether to place the middle object horizontally (on its side)")
    parser.add_argument("--spacing_jitter",
                        type=float,
                        default=0.25,
                        help="jitter in how to space middle object in xz plane")
    parser.add_argument("--probe",
                        type=str,
                        default="sphere",
                        help="comma-separated list of possible probe objects")
    parser.add_argument("--pmass",
                        type=str,
                        default="[2.0,4.0]",
                        help="scale of probe objects")
    parser.add_argument("--pscale",
                        type=str,
                        default="[0.2,0.4]",
                        help="scale of probe objects")
    parser.add_argument("--tscale",
                        type=str,
                        default="[0.5,0.5]",
                        help="scale of target objects")
    parser.add_argument("--fscale",
                        type=str,
                        default="[4.0,10.0]",
                        help="range of scales to apply to push force")
    parser.add_argument("--frot",
                        type=str,
                        default="[-20,20]",
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
                        default=1.5,
                        help="radial distance from camera to centerpoint")
    parser.add_argument("--camera_min_angle",
                        type=float,
                        default=0,
                        help="minimum angle of camera rotation around centerpoint")
    parser.add_argument("--camera_max_angle",
                        type=float,
                        default=180,
                        help="maximum angle of camera rotation around centerpoint")


    def postprocess(args):
        args.horizontal = bool(args.horizontal)

        return args

    args = parser.parse_args()
    args = domino_postproc(args)
    args = postprocess(args)

    print(vars(parser.parse_args()))

    return args


if __name__ == '__main__':

    # args = get_collide_args("collide")

    c = MaterialLibrarian()
    ms = c.get_material_types()
    print(ms)
    print([m.name for m in c.get_all_materials_of_type("Wood")])
    # metal = [m for m in c.get_all_materials_of_type("Metal") if "steel_rusty" in m.name]
    # print(metal[0], metal[0].name)
    # for m in ms:
    #     more_ms = c.get_all_materials_of_type(m)
    #     print(m, [_m.name for _m in more_ms])

    # C = MultiDominoes()
    # m = C.get_add_material("steel_rusty")
    # print(m)
