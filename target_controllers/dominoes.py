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


MODEL_NAMES = [r.name for r in MODEL_LIBRARIES['models_flex.json'].records]


def get_args(dataset_dir: str, parse=True):
    """
    Combine Domino-specific arguments with controller-common arguments
    """
    common = get_parser(dataset_dir, get_help=False)
    parser = ArgumentParser(parents=[common], add_help=parse)

    parser.add_argument("--num_middle_objects",
                        type=int,
                        default=0,
                        help="The number of middle objects to place")
    parser.add_argument("--target",
                        type=str,
                        default="cube",
                        help="comma-separated list of possible target objects")
    parser.add_argument("--probe",
                        type=str,
                        default="sphere",
                        help="comma-separated list of possible target objects")
    parser.add_argument("--middle",
                        type=str,
                        default=None,
                        help="comma-separated list of possible middle objects; default to same as target")
    parser.add_argument("--tscale",
                        type=str,
                        default="0.1,0.5,0.25",
                        help="scale of target objects")
    parser.add_argument("--trot",
                        type=str,
                        default="0.,0.,0.",
                        help="comma separated list of initial target rotation values")
    parser.add_argument("--mrot",
                        type=str,
                        default="[-60,60]",
                        help="comma separated list of initial middle object rotation values")
    parser.add_argument("--mscale",
                        type=str,
                        default=None,
                        help="Scale or scale range for middle objects")
    parser.add_argument("--pscale",
                        type=str,
                        default="0.2,0.2,0.2",
                        help="scale of probe objects")
    parser.add_argument("--pmass",
                        type=str,
                        default="[2.0,7.0]",
                        help="scale of probe objects")
    parser.add_argument("--fscale",
                        type=str,
                        default="[4.0,10.0]",
                        help="range of scales to apply to push force")
    parser.add_argument("--frot",
                        type=str,
                        default="[-30,30]",
                        help="range of angles in xz plane to apply push force")
    parser.add_argument("--foffset",
                        type=str,
                        default="0.0,0.75,0.0",
                        help="offset from probe centroid from which to apply force, relative to probe scale")
    parser.add_argument("--fjitter",
                        type=float,
                        default=0.0,
                        help="jitter around object centroid to apply force")
    parser.add_argument("--color",
                        type=str,
                        default=None,
                        help="comma-separated R,G,B values for the target object color. Defaults to random.")
    parser.add_argument("--collision_axis_length",
                        type=float,
                        default=1.,
                        help="Length of spacing between probe and target objects at initialization.")
    parser.add_argument("--spacing_jitter",
                        type=float,
                        default=0.25,
                        help="jitter in how to space middle objects, as a fraction of uniform spacing")
    parser.add_argument("--remove_target",
                        type=int,
                        default=0,
                        help="Don't actually put the target object in the scene.")
    parser.add_argument("--camera_distance",
                        type=float,
                        default=1.25,
                        help="radial distance from camera to centerpoint")
    parser.add_argument("--camera_min_height",
                        type=float,
                        default=0.25,
                         help="min height of camera as a fraction of drop height")
    parser.add_argument("--camera_max_height",
                        type=float,
                        default=1.0,
                        help="max height of camera as a fraction of drop height")
    parser.add_argument("--camera_min_angle",
                        type=float,
                        default=0,
                        help="minimum angle of camera rotation around centerpoint")
    parser.add_argument("--camera_max_angle",
                        type=float,
                        default=180,
                        help="maximum angle of camera rotation around centerpoint")

    def postprocess(args):
        # whether to set all objects same color
        args.monochrome = bool(args.monochrome)

        # scaling and rotating of objects
        args.tscale = handle_random_transform_args(args.tscale)
        args.trot = handle_random_transform_args(args.trot)
        args.pscale = handle_random_transform_args(args.pscale)
        args.pmass = handle_random_transform_args(args.pmass)
        args.mscale = handle_random_transform_args(args.mscale)
        args.mrot = handle_random_transform_args(args.mrot)

        # the push force scale and direction
        args.fscale = handle_random_transform_args(args.fscale)
        args.frot = handle_random_transform_args(args.frot)
        args.foffset = handle_random_transform_args(args.foffset)

        if args.target is not None:
            targ_list = args.target.split(',')
            assert all([t in MODEL_NAMES for t in targ_list]), \
                "All target object names must be elements of %s" % MODEL_NAMES
            args.target = targ_list
        else:
            args.target = MODEL_NAMES

        if args.probe is not None:
            probe_list = args.probe.split(',')
            assert all([t in MODEL_NAMES for t in probe_list]), \
                "All target object names must be elements of %s" % MODEL_NAMES
            args.probe = probe_list
        else:
            args.probe = MODEL_NAMES

        if args.middle is not None:
            middle_list = args.middle.split(',')
            assert all([t in MODEL_NAMES for t in middle_list]), \
                "All target object names must be elements of %s" % MODEL_NAMES
            args.middle = middle_list

        if args.color is not None:
            rgb = [float(c) for c in args.color.split(',')]
            assert len(rgb) == 3, rgb
            args.color = rgb

        return args

    if not parse:
        return (parser, postprocess)
    else:
        args = parser.parse_args()
        args = postprocess(args)
        return args

class Dominoes(RigidbodiesDataset):
    """
    Drop a random Flex primitive object on another random Flex primitive object
    """

    def __init__(self,
                 port: int = 1071,
                 probe_objects=MODEL_NAMES,
                 target_objects=MODEL_NAMES,
                 probe_scale_range=[0.2, 0.3],
                 probe_mass_range=[2.,7.],
                 target_scale_range=[0.2, 0.3],
                 target_rotation_range=None,
                 target_color=None,
                 collision_axis_length=1.,
                 force_scale_range=[0.,8.],
                 force_angle_range=[-60,60],
                 force_offset={"x":0.,"y":0.5,"z":0.0},
                 force_offset_jitter=0.1,
                 remove_target=False,
                 camera_radius=1.0,
                 camera_min_angle=0,
                 camera_max_angle=360,
                 camera_min_height=1./3,
                 camera_max_height=2./3,
                 **kwargs):

        ## initializes static data and RNG
        super().__init__(port=port, **kwargs)

        ## allowable object types
        self.set_probe_types(probe_objects)
        self.set_target_types(target_objects)
        self.remove_target = remove_target

        ## object generation properties
        self.target_scale_range = target_scale_range
        self.target_color = target_color
        self.target_rotation_range = target_rotation_range

        self.probe_scale_range = probe_scale_range
        self.probe_mass_range = probe_mass_range
        self.match_probe_and_target_color = True

        ## Scenario config properties
        self.collision_axis_length = collision_axis_length
        self.force_scale_range = force_scale_range
        self.force_angle_range = force_angle_range
        self.force_offset = get_random_xyz_transform(force_offset)
        self.force_offset_jitter = force_offset_jitter

        ## camera properties
        self.camera_radius = camera_radius
        self.camera_min_angle = camera_min_angle
        self.camera_max_angle = camera_max_angle
        self.camera_min_height = camera_min_height
        self.camera_max_height = camera_max_height
        self.camera_aim = {"x": 0., "y": 0.5, "z": 0.} # fixed aim

    def get_types(self, objlist):
        recs = MODEL_LIBRARIES["models_flex.json"].records
        tlist = [r for r in recs if r.name in objlist]
        return tlist

    def set_probe_types(self, olist):
        tlist = self.get_types(olist)
        self._probe_types = tlist

    def set_target_types(self, olist):
        tlist = self.get_types(olist)
        self._target_types = tlist

    def clear_static_data(self) -> None:
        super().clear_static_data()

        ## scenario-specific metadata: object types and drop position
        self.target_type = None
        self.target_rotation = None

        self.probe_type = None
        self.probe_mass = None
        self.push_force = None
        self.push_position = None

    def get_field_of_view(self) -> float:
        return 55

    def get_scene_initialization_commands(self) -> List[dict]:
        return [self.get_add_scene(scene_name="box_room_2018"),
                {"$type": "set_aperture",
                 "aperture": 8.0},
                {"$type": "set_post_exposure",
                 "post_exposure": 0.4},
                {"$type": "set_ambient_occlusion_intensity",
                 "intensity": 0.175},
                {"$type": "set_ambient_occlusion_thickness_modifier",
                 "thickness": 3.5}]

    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []

        # Choose and place a target object.
        commands.extend(self._place_target_object())

        # Set the probe color
        self.probe_color = self.target_color if (self.monochrome and self.match_probe_and_target_color) else None

        # Choose, place, and push a probe object.
        commands.extend(self._place_and_push_probe_object())

        # Build the intermediate structure that captures some aspect of "intuitive physics."
        commands.extend(self._build_intermediate_structure())

        # Teleport the avatar to a reasonable position based on the drop height.
        a_pos = self.get_random_avatar_position(radius_min=self.camera_radius,
                                                radius_max=self.camera_radius,
                                                angle_min=self.camera_min_angle,
                                                angle_max=self.camera_max_angle,
                                                y_min=self.camera_min_height,
                                                y_max=self.camera_max_height,
                                                center=TDWUtils.VECTOR3_ZERO)
        print("avatar position", a_pos)

        commands.extend([
            {"$type": "teleport_avatar_to",
             "position": a_pos},
            {"$type": "look_at_position",
             "position": self.camera_aim},
            {"$type": "set_focus_distance",
             "focus_distance": TDWUtils.get_distance(a_pos, self.camera_aim)}
        ])
        return commands

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return []

    def _write_static_data(self, static_group: h5py.Group) -> None:
        super()._write_static_data(static_group)

        ## color and scales of primitive objects
        static_group.create_dataset("target_type", data=self.target_type)
        static_group.create_dataset("target_rotation", data=xyz_to_arr(self.target_rotation))
        static_group.create_dataset("probe_type", data=self.probe_type)
        static_group.create_dataset("probe_mass", data=self.probe_mass)
        static_group.create_dataset("push_force", data=xyz_to_arr(self.push_force))
        static_group.create_dataset("push_position", data=xyz_to_arr(self.push_position))

    def _write_frame(self,
                     frames_grp: h5py.Group,
                     resp: List[bytes],
                     frame_num: int) -> \
            Tuple[h5py.Group, h5py.Group, dict, bool]:
        frame, objs, tr, sleeping = super()._write_frame(frames_grp=frames_grp,
                                                         resp=resp,
                                                         frame_num=frame_num)
        # If this is a stable structure, disregard whether anything is actually moving.
        return frame, objs, tr, sleeping and frame_num < 300

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 250

    def get_rotation(self, rot_range):
        if rot_range is None:
            return {"x": 0,
                    "y": random.uniform(0, 360),
                    "z": 0.}
        else:
            return get_random_xyz_transform(rot_range)

    def get_y_rotation(self, rot_range):
        if rot_range is None:
            return self.get_rotation(rot_range)
        else:
            return {"x": 0.,
                    "y": random.uniform(rot_range[0], rot_range[1]),
                    "z": 0.}

    def get_push_force(self, scale_range, angle_range):
        # rotate a unit vector initially pointing in positive-x direction
        theta = np.radians(random.uniform(angle_range[0], angle_range[1]))
        push = np.array([np.cos(theta), 0., np.sin(theta)])

        # scale it
        push *= random.uniform(scale_range[0], scale_range[1])

        # convert to xyz
        return arr_to_xyz(push)

    def _place_target_object(self) -> List[dict]:
        """
        Place a primitive object at one end of the collision axis.
        """

        # create a target object
        # XXX TODO: Why is scaling part of random primitives
        # but rotation and translation are not?
        # Consider integrating!
        record, data = self.random_primitive(self._target_types,
                                             scale=self.target_scale_range,
                                             color=self.target_color)
        o_id, scale, rgb = [data[k] for k in ["id", "scale", "color"]]
        self.target = record
        self.target_type = data["name"]
        self.target_color = rgb
        # self.probe_color = rgb if self.monochrome else None

        # add the object
        commands = []
        if self.target_rotation is None:
            self.target_rotation = self.get_rotation(self.target_rotation_range)

        commands.extend(
            self.add_physics_object(
                record=record,
                position={
                    "x": 0.5 * self.collision_axis_length,
                    "y": 0. if not self.remove_target else 10.0,
                    "z": 0. if not self.remove_target else 10.0
                },
                rotation=self.target_rotation,
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
             "scale_factor": scale if not self.remove_target else TDWUtils.VECTOR3_ZERO,
             "id": o_id}])

        if self.remove_target:
            commands.append(
                {"$type": self._get_destroy_object_command_name(o_id),
                 "id": int(o_id)})
            self.object_ids = self.object_ids[:-1]

        return commands

    def _place_and_push_probe_object(self) -> List[dict]:
        """
        Place a probe object at the other end of the collision axis, then apply a force to push it.
        """
        exclude = not (self.monochrome and self.match_probe_and_target_color)
        record, data = self.random_primitive(self._probe_types,
                                             scale=self.probe_scale_range,
                                             color=self.probe_color,
                                             exclude_color=(self.target_color if exclude else None),
                                             exclude_range=0.25)
        o_id, scale, rgb = [data[k] for k in ["id", "scale", "color"]]
        self.probe = record
        self.probe_type = data["name"]

        print("target", self.target.bounds)

        # Add the object with random physics values
        commands = []

        ### TODO: better sampling of random physics values
        self.probe_mass = random.uniform(self.probe_mass_range[0], self.probe_mass_range[1])
        self.probe_initial_position = {"x": -0.5*self.collision_axis_length, "y": 0., "z": 0.}
        commands.extend(
            self.add_physics_object(
                record=record,
                position=self.probe_initial_position,
                rotation=TDWUtils.VECTOR3_ZERO,
                mass=self.probe_mass,
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

        # Apply a force to the probe object
        self.push_force = self.get_push_force(
            scale_range=self.probe_mass * np.array(self.force_scale_range),
            angle_range=self.force_angle_range)
        print("pos, force, scales", self.probe_initial_position, self.force_offset, self.scales[-1])
        self.push_position = {
            k:v+self.force_offset[k]*self.scales[-1][k]
            for k,v in self.probe_initial_position.items()}
        self.push_position = {
            k:v+random.uniform(-self.force_offset_jitter, self.force_offset_jitter)
            for k,v in self.push_position.items()}
        push = {
            "$type": "apply_force_at_position",
            "force": self.push_force,
            "position": self.push_position,
            "id": int(o_id)
        }
        commands.append(push)

        return commands

    def _build_intermediate_structure(self) -> List[dict]:
        """
        Abstract method for building a physically interesting intermediate structure between the probe and the target.
        """
        commands = []
        return commands

class MultiDominoes(Dominoes):

    def __init__(self,
                 port: int = 1071,
                 middle_objects=None,
                 num_middle_objects=1,
                 middle_scale_range=None,
                 middle_rotation_range=None,
                 middle_color=None,
                 spacing_jitter=0.25,
                 **kwargs):

        super().__init__(port=port, **kwargs)

        # Default to same type as target
        self.set_middle_types(middle_objects)

        # Appearance of middle objects
        self.middle_scale_range = middle_scale_range or self.target_scale_range
        self.middle_rotation_range = middle_rotation_range
        self.middle_color = middle_color

        # How many middle objects and their spacing
        self.num_middle_objects = num_middle_objects
        self.spacing = self.collision_axis_length / (self.num_middle_objects + 1.)
        self.spacing_jitter = spacing_jitter

    def set_middle_types(self, olist):
        if olist is None:
            self._middle_types = self._target_types
        else:
            tlist = self.get_types(olist)
            self._middle_types = tlist

    def clear_static_data(self) -> None:
        super().clear_static_data()

        self.middle_type = None
        self.middle_color = None

    def _write_static_data(self, static_group: h5py.Group) -> None:
        super()._write_static_data(static_group)

        static_group.create_dataset("middle_type", data=self.middle_type)

    def _build_intermediate_structure(self) -> List[dict]:
        # set the middle object color
        self.middle_color = self.middle_color or (self.probe_color if self.monochrome else self.random_color())

        return self._place_middle_objects() if bool(self.num_middle_objects) else []

    def _place_middle_objects(self) -> List[dict]:

        offset = -0.5 * self.collision_axis_length
        min_offset = offset + self.scales[-1]["x"]
        max_offset = 0.5 * self.collision_axis_length - self.scales[0]["x"]

        commands = []
        for m in range(self.num_middle_objects):
            offset += self.spacing * random.uniform(1.-self.spacing_jitter, 1.+self.spacing_jitter)
            offset = np.minimum(np.maximum(offset, min_offset), max_offset)
            if offset >= max_offset:
                print("couldn't place middle object %s" % str(m+1))
                break

            print("middle color", self.middle_color)
            record, data = self.random_primitive(self._middle_types,
                                                 scale=self.middle_scale_range,
                                                 color=self.middle_color)
            o_id, scale, rgb = [data[k] for k in ["id", "scale", "color"]]
            rot = self.get_y_rotation(self.middle_rotation_range)
            self.middle_type = data["name"]

            commands.extend(
                self.add_physics_object(
                    record=record,
                    position={
                        "x": offset,
                        "y": 0.,
                        "z": 0.
                    },
                    rotation=rot,
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

        return commands

if __name__ == "__main__":

    args = get_args("dominoes")
    print("all object types", MODEL_NAMES)
    print("target objects", args.target)
    print("probe objects", args.probe)

    DomC = MultiDominoes(
        num_middle_objects=args.num_middle_objects,
        randomize=args.random,
        seed=args.seed,
        target_objects=args.target,
        probe_objects=args.probe,
        middle_objects=args.middle,
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
        spacing_jitter=args.spacing_jitter,
        middle_rotation_range=args.mrot,
        remove_target=bool(args.remove_target),
        ## not scenario-specific
        camera_radius=args.camera_distance,
        camera_min_angle=args.camera_min_angle,
        camera_max_angle=args.camera_max_angle,
        camera_min_height=args.camera_min_height,
        camera_max_height=args.camera_max_height,
        monochrome=args.monochrome
    )

    if bool(args.run):
        DomC.run(num=args.num,
               output_dir=args.dir,
               temp_path=args.temp,
               width=args.width,
               height=args.height)
    else:
        DomC.communicate({"$type": "terminate"})
