from typing import Dict, List
import random
import numpy as np
from tdw.librarian import ModelLibrarian
from tdw.tdw_utils import TDWUtils

# Every model library, sorted by name.
MODEL_LIBRARIES: Dict[str, ModelLibrarian] = {}
for filename in ModelLibrarian.get_library_filenames():
    MODEL_LIBRARIES.update({filename: ModelLibrarian(filename)})

def str_to_xyz(s: str, to_json=False):
    xyz = s.split(',')
    if len(xyz) == 3:
        s ={"x":float(xyz[0]), "y":float(xyz[1]), "z":float(xyz[2])}
    return s

def xyz_to_arr(xyz : dict):
    arr = np.array(
        [xyz[k] for k in ["x","y","z"]], dtype=np.float32)
    return arr

def arr_to_xyz(arr : np.ndarray):
    xyz = {k:arr[i] for i,k in enumerate(["x","y","z"])}
    return xyz

def get_move_along_direction(pos: Dict[str, float], target: Dict[str, float], d: float, noise: float = 0) -> \
        Dict[str, float]:
    """
    :param pos: The object's position.
    :param target: The target position.
    :param d: The distance to teleport.
    :param noise: Add a little noise to the teleport.

    :return: A position from pos by distance d along a directional vector defined by pos, target.
    """
    direction = TDWUtils.array_to_vector3((TDWUtils.vector3_to_array(target) - TDWUtils.vector3_to_array(pos)) /
                                          TDWUtils.get_distance(pos, target))

    return {"x": pos["x"] + direction["x"] * d + random.uniform(-noise, noise),
            "y": pos["y"],
            "z": pos["z"] + direction["z"] * d + random.uniform(-noise, noise)}


def get_object_look_at(o_id: int, pos: Dict[str, float], noise: float = 0) -> List[dict]:
    """
    :param o_id: The ID of the object to be rotated.
    :param pos: The position to look at.
    :param noise: Rotate the object randomly by this much after applying the look_at command.

    :return: A list of commands to rotate an object to look at the target position.
    """

    commands = [{"$type": "object_look_at_position",
                 "id": o_id,
                 "position": pos}]
    if noise > 0:
        commands.append({"$type": "rotate_object_by",
                         "angle": random.uniform(-noise, noise),
                         "axis": "yaw",
                         "id": o_id,
                         "is_world": True})
    return commands


def get_parser(dataset_dir: str, get_help: bool=False):
    """
    :param dataset_dir: The default name of the dataset.

    :return: Parsed command-line arguments common to all controllers.
    """

    import argparse
    parser = argparse.ArgumentParser(add_help=get_help)
    parser.add_argument("--dir", type=str, default=f"D:/{dataset_dir}", help="Root output directory.")
    parser.add_argument("--num", type=int, default=3, help="The number of trials in the dataset.")
    parser.add_argument("--temp", type=str, default="D:/temp.hdf5", help="Temp path for incomplete files.")
    parser.add_argument("--width", type=int, default=256, help="Screen width in pixels.")
    parser.add_argument("--height", type=int, default=256, help="Screen width in pixels.")
    parser.add_argument("--seed", type=int, default=0, help="Random seed with which to initialize scenario")
    parser.add_argument("--random", type=int, default=1, help="Whether to set trials randomly")
    parser.add_argument("--num_views", type=int, default=1, help="How many possible viewpoints to render trial from")
    parser.add_argument("--viewpoint", type=int, default=0, help="which viewpoint to render from")
    parser.add_argument("--run", type=int, default=1, help="run the simulation or not")
    parser.add_argument("--monochrome", type=int, default=0, help="whether to set all colorable objects to the same color")
    return parser

def get_args(dataset_dir: str):

    parser = get_parser(dataset_dir, get_help=True)
    return parser.parse_args()
