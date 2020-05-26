from typing import List
import random
from pathlib import Path
from tdw.librarian import ModelLibrarian, ModelRecord, MaterialLibrarian
from tdw.tdw_utils import TDWUtils
from tdw.output_data import OutputData, Transforms, IdPassSegmentationColors
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset
from tdw_physics.util import get_args


class Permanence(RigidbodiesDataset):
    """
    An object goes behind another object and reappears.
    """

    _BALL_SCALE = 0.3
    _BALL_MATERIALS = ["aluminium_brushed", "aluminium_clean", "anodized_aluminium", "concrete_chipped_cracked",
                       "concrete_terrazzo", "fabric_vinyl_heavy", "gold_natural", "marble_crema_valencia",
                       "marble_griotte", "plastic_stripes", "plastic_vinyl_glossy_green", "plastic_vinyl_glossy_blue",
                       "plastic_vinyl_glossy_orange"]

    def __init__(self, port: int = 1071):
        super().__init__(port=port)

        self._occluders: List[ModelRecord] = ModelLibrarian(str(Path("occluders.json").resolve())).records
        self._ball = ModelLibrarian("models_flex.json").get_record("sphere")
        self._ball_id = 0
        self._occ_id = 1
        self.material_librarian = MaterialLibrarian()

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return [{"$type": "focus_on_object",
                 "object_id": self._ball_id}]

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
                 "thickness": 3.5},
                {"$type": "unload_asset_bundles",
                 "bundle_type": "materials"},
                {"$type": "send_id_pass_segmentation_colors",
                 "frequency": "always"}]

    def get_field_of_view(self) -> float:
        return 68

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        # The ball must have a positive x coordinate (moving away from occluder) and be out of frame.
        positive_x = False
        segmentation_color = False
        for r in resp:
            r_id = OutputData.get_data_type_id(r)
            if r_id == "tran":
                t = Transforms(r)
                for i in range(t.get_num()):
                    if t.get_id(i) == self._ball_id:
                        positive_x = t.get_position(i)[0] >= 2
            elif r_id == "ipsc":
                ip = IdPassSegmentationColors(r)
                segmentation_color = ip.get_num_segmentation_colors() == 1

        return positive_x and segmentation_color

    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Add the ball.
        commands.extend(self.add_physics_object(record=self._ball,
                                                position={"x": random.uniform(-2.2, -2.6),
                                                          "y": 0,
                                                          "z": random.uniform(1.5, 1.6)},
                                                rotation=TDWUtils.VECTOR3_ZERO,
                                                o_id=self._ball_id,
                                                mass=random.uniform(1, 4),
                                                dynamic_friction=random.uniform(0, 0.1),
                                                static_friction=random.uniform(0, 0.1),
                                                bounciness=random.uniform(0, 0.1)))
        # Set a random material.
        commands.extend(TDWUtils.set_visual_material(self, self._ball.substructure, self._ball_id,
                                                     random.choice(self._BALL_MATERIALS)))
        # Set a random mass and color.
        # Rotate the object and apply a force twice (to give it a spin).
        commands.extend([{"$type": "scale_object",
                          "scale_factor": {"x": self._BALL_SCALE, "y": self._BALL_SCALE, "z": self._BALL_SCALE},
                          "id": self._ball_id},
                         {"$type": "object_look_at_position",
                          "position": {"x": 100, "y": 0, "z": 0},
                          "id": self._ball_id},
                         {"$type": "rotate_object_by",
                          "angle": random.uniform(30, 45),
                          "id": self._ball_id,
                          "axis": "pitch",
                          "is_world": True},
                         {"$type": "apply_force_magnitude_to_object",
                          "magnitude": random.uniform(1, 3),
                          "id": self._ball_id},
                         {"$type": "object_look_at_position",
                          "position": {"x": 100, "y": 0, "z": 0},
                          "id": self._ball_id},
                         {"$type": "apply_force_magnitude_to_object",
                          "magnitude": random.uniform(20, 30),
                          "id": self._ball_id}])
        # Add an occluder.
        occ_record: ModelRecord = random.choice(self._occluders)
        commands.extend(self.add_physics_object(record=occ_record,
                                                position={"x": 0, "y": 0, "z": 0},
                                                rotation={"x": 0, "y": random.uniform(0, 360), "z": 0},
                                                o_id=self._occ_id,
                                                mass=random.uniform(100, 150),
                                                dynamic_friction=random.uniform(0.9, 1),
                                                static_friction=random.uniform(0.9, 1),
                                                bounciness=random.uniform(0, 0.1)))
        s_occ = TDWUtils.get_unit_scale(occ_record) * random.uniform(1.25, 1.5)
        commands.extend([{"$type": "scale_object",
                          "scale_factor": {"x": s_occ, "y": s_occ, "z": s_occ},
                          "id": self._occ_id},
                         {"$type": "set_object_collision_detection_mode",
                          "mode": "continuous_speculative",
                          "id": self._occ_id},
                         {"$type": "set_kinematic_state",
                          "id": self._occ_id,
                          "is_kinematic": True,
                          "use_gravity": False}])
        # Reset the avatar.
        occ_y = occ_record.bounds["top"]["y"] * s_occ
        commands.extend([{"$type": "teleport_avatar_to",
                          "position": {"x": random.uniform(-0.05, 0.05),
                                       "y": random.uniform(occ_y * 0.3, occ_y * 0.8),
                                       "z": random.uniform(-2.2, -2.4)}},
                         {"$type": "look_at",
                          "object_id": self._occ_id,
                          "use_centroid": True},
                         {"$type": "rotate_sensor_container_by",
                          "axis": "pitch",
                          "angle": random.uniform(-5, 5)},
                         {"$type": "rotate_sensor_container_by",
                          "axis": "yaw",
                          "angle": random.uniform(-5, 5)}])
        return commands


if __name__ == "__main__":
    args = get_args("permanence")
    td = Permanence()
    td.run(num=args.num, output_dir=args.dir, temp_path=args.temp)
