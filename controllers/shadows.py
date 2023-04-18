from typing import List, Dict
import numpy as np
import random
from pathlib import Path
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelLibrarian, HDRISkyboxLibrarian, MaterialLibrarian, MaterialRecord
from tdw.output_data import OutputData, Transforms
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset
from tdw_physics.util import get_args


class _Sector:
    """
    A sector has two points.

    A "sub-sector" is the circle defined by one of these points and RADIUS.
    """

    RADIUS = 0.1

    def __init__(self, c_0: Dict[str, float], c_1: Dict[str, float]):
        """
        :param c_0: Center of a subsector.
        :param c_1: Center of a subsector.
        """
        self.c_0 = TDWUtils.vector3_to_array(c_0)
        self.c_1 = TDWUtils.vector3_to_array(c_1)

    def get_p_0(self) -> Dict[str, float]:
        """
        :return: A position in the c_0 sub-sector.
        """

        return TDWUtils.array_to_vector3(TDWUtils.get_random_point_in_circle(center=self.c_0, radius=self.RADIUS))

    def get_p_1(self) -> Dict[str, float]:
        """
        :return: A position in the c_1 sub-sector.
        """

        return TDWUtils.array_to_vector3(TDWUtils.get_random_point_in_circle(center=self.c_1, radius=self.RADIUS))


class Shadows(RigidbodiesDataset):
    """
    Move a ball to and from areas with different lighting.

    Use HDRI skyboxes and visual materials (for the ball) to change the lighting per trial.
    """

    _BALL_SCALE = 0.5
    _BALL_MATERIAL_RECORDS: List[MaterialRecord] = MaterialLibrarian(str(Path("ball_materials.json").resolve())).records

    # These sectors have different lighting at each point, e.g. c_0 is more shadowed than c_1.
    SECTORS = [_Sector(c_0={"x": 0.5, "y": 0, "z": 0}, c_1={"x": -0.5, "y": 0, "z": 0}),
               _Sector(c_0={"x": 0, "y": 0, "z": 3}, c_1={"x": -1.2, "y": 0, "z": 3.7}),
               _Sector(c_0={"x": 0, "y": 0, "z": -3}, c_1={"x": -1.2, "y": 0, "z": -3.7}),
               _Sector(c_0={"x": 2.15, "y": 0, "z": -2.6}, c_1={"x": 4, "y": 0, "z": -3}),
               _Sector(c_0={"x": 2.15, "y": 0, "z": 2.6}, c_1={"x": 4, "y": 0, "z": 3}),
               _Sector(c_0={"x": -2.15, "y": 0, "z": 2.6}, c_1={"x": -4, "y": 0, "z": 3}),
               _Sector(c_0={"x": -2.15, "y": 0, "z": -2.6}, c_1={"x": -4, "y": 0, "z": -3})]

    def __init__(self, port: int = 1071):
        super().__init__(port=port)

        # Cache the ball data.
        self._ball = ModelLibrarian("models_special.json").get_record("prim_sphere")
        self._ball_id = 0

        # The position the ball starts in and the position the ball is directed at.
        self._p0: Dict[str, float] = {}
        self._p1: Dict[str, float] = {}

        # Cache the skybox records.
        skybox_lib = HDRISkyboxLibrarian()
        self._skyboxes: List[str] = [r.name for r in skybox_lib.records if r.sun_intensity >= 0.8]

    def get_scene_initialization_commands(self) -> List[dict]:
        return [self.get_add_scene(scene_name="box_room_2018"),
                {"$type": "set_aperture",
                 "aperture": 4.8},
                {"$type": "set_focus_distance",
                 "focus_distance": 1.25},
                {"$type": "set_post_exposure",
                 "post_exposure": 0.4},
                {"$type": "set_ambient_occlusion_intensity",
                 "intensity": 0.175},
                {"$type": "set_ambient_occlusion_thickness_modifier",
                 "thickness": 3.5}]

    def get_trial_initialization_commands(self) -> List[dict]:
        # Select a random sector.
        sector: _Sector = random.choice(self.SECTORS)
        # Decide where the ball will go and in which direction.
        if random.random() < 0.5:
            self._p0 = sector.get_p_0()
            self._p1 = sector.get_p_1()
        else:
            self._p0 = sector.get_p_1()
            self._p1 = sector.get_p_0()
        self._p0["y"] = self._BALL_SCALE / 2
        self._p1["y"] = self._BALL_SCALE / 2

        commands = []
        # Add the ball.
        mass = random.uniform(1, 4)
        commands.extend(self.get_add_physics_object(model_name=self._ball.name,
                                                    library="models_special.json",
                                                    object_id=self._ball_id,
                                                    position=self._p0,
                                                    rotation=TDWUtils.VECTOR3_ZERO,
                                                    default_physics_values=False,
                                                    mass=mass,
                                                    scale_mass=False,
                                                    dynamic_friction=random.uniform(0, 0.1),
                                                    static_friction=random.uniform(0, 0.1),
                                                    bounciness=random.uniform(0, 0.1),
                                                    scale_factor={"x": self._BALL_SCALE,
                                                                  "y": self._BALL_SCALE,
                                                                  "z": self._BALL_SCALE}))
        ball_material: MaterialRecord = random.choice(self._BALL_MATERIAL_RECORDS)
        # Apply a force and a spin.
        # Set a random visual material.
        # Add a random skybox.
        commands.extend([{"$type": "rotate_object_by",
                          "angle": random.uniform(30, 45),
                          "id": self._ball_id,
                          "axis": "pitch",
                          "is_world": True},
                         {"$type": "apply_force_magnitude_to_object",
                          "magnitude": random.uniform(0.01, 0.03),
                          "id": self._ball_id},
                         {"$type": "object_look_at_position",
                          "position": self._p1,
                          "id": self._ball_id},
                         {"$type": "apply_force_magnitude_to_object",
                          "magnitude": random.uniform(5.2 * mass, 8 * mass),
                          "id": self._ball_id},
                         {"$type": "add_material",
                          "name": ball_material.name,
                          "url": ball_material.get_url()},
                         {"$type": "set_visual_material",
                          "id": self._ball_id,
                          "material_name": ball_material.name,
                          "object_name": "PrimSphere",
                          "material_index": 0},
                         self.get_add_hdri_skybox(skybox_name=random.choice(self._skyboxes)),
                         {"$type": "rotate_hdri_skybox_by",
                          "angle": random.uniform(0, 360)}])
        # Teleport the avatar such that it can see both points.
        d0 = TDWUtils.get_distance(self._p0, self._p1)
        p_med = np.array([(self._p0["x"] + self._p1["x"]) / 2, 0, (self._p0["z"] + self._p1["z"]) / 2])
        p_cen = np.array([0, 0, 0])
        a_pos = p_med + ((p_cen - p_med) / np.abs(np.linalg.norm(p_cen - p_med)) * (d0 + random.uniform(-0.01, -0.05)))
        a_pos[1] = random.uniform(1.2, 1.5)
        commands.extend([{"$type": "teleport_avatar_to",
                          "position": TDWUtils.array_to_vector3(a_pos)},
                         {"$type": "look_at_position",
                          "position": TDWUtils.array_to_vector3(p_med)}])
        return commands

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return [{"$type": "focus_on_object",
                 "object_id": self._ball_id,
                 "use_centroid": True}]

    def get_field_of_view(self) -> float:
        return 68

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        for r in resp[:-1]:
            r_id = OutputData.get_data_type_id(r)
            # If the ball reaches or overshoots the destination, the trial is done.
            if r_id == "tran":
                t = Transforms(r)
                d0 = TDWUtils.get_distance(TDWUtils.array_to_vector3(t.get_position(0)), self._p0)
                d1 = TDWUtils.get_distance(self._p0, self._p1)
                return d0 > d1 * 1.5
        return False


if __name__ == "__main__":
    args = get_args("shadows")
    td = Shadows()
    td.run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
