from random import choice, uniform
from typing import List
from tdw_physics.flex_dataset import FlexDataset
from tdw_physics.util import MODEL_LIBRARIES, get_args


class Draping(FlexDataset):
    """
    Using NVIDIA Flex, drape a randomly-selected object with a cloth object.
    """

    def __init__(self, port: int = 1071):
        object_names = ["linbrazil_diz_armchair",
                        "whirlpool_akzm7630ix",
                        "12_01_010",
                        "12_01_015",
                        "b05_trophy",
                        "b05_elsafe_infinity_ii",
                        "b03_cylinder004",
                        "naughtone_pinch_stool_chair",
                        "b04_bowl_smooth",
                        "b03_bfg_silvertoown",
                        "backpack",
                        "amphora_jar_vase",
                        "suitcase",
                        "microwave",
                        "towel-radiator-2",
                        "chista_slice_of_teak_table",
                        "bongo_drum_hr_blend",
                        "b03_worldglobe",
                        "elephant_bowl",
                        "trapezoidal_table"]
        # Load the objects.
        self.object_records = [MODEL_LIBRARIES["models_full.json"].get_record(n) for n in object_names]
        # Get the cloth record.
        self.cloth_record = MODEL_LIBRARIES["models_special.json"].get_record("cloth_square")
        self.cloth_id = 0

        super().__init__(port=port)

    def get_scene_initialization_commands(self) -> List[dict]:
        return [self.get_add_scene(scene_name="tdw_room_2018"),
                {"$type": "set_aperture",
                 "aperture": 3.0},
                {"$type": "set_focus_distance",
                 "focus_distance": 2.25},
                {"$type": "set_post_exposure",
                 "post_exposure": 0.4},
                {"$type": "set_ambient_occlusion_intensity",
                 "intensity": 0.25},
                {"$type": "set_ambient_occlusion_thickness_modifier",
                 "thickness": 4.0},
                {"$type": "create_flex_container",
                 "collision_distance": 0.001,
                 "static_friction": 1.0,
                 "dynamic_friction": 1.0,
                 "iteration_count": 12,
                 "substep_count": 12,
                 "radius": 0.1875,
                 "damping": 0.25,
                 "drag": 0},
                {"$type": "set_time_step",
                 "time_step": 0.03}]

    def get_trial_initialization_commands(self) -> List[dict]:
        """
        Randomly select an object and orientation, and drape it using a given set of cloth parameters.

        """
        # Position and aim avatar.
        trial_commands = [{"$type": "teleport_avatar_to",
                           "position": {"x": 2.0, "y": 1, "z": 1}},
                          {"$type": "look_at_position",
                           "position": {"x": -1.2, "y": 0.5, "z": -1.6}}]

        # Add object and convert to Flex SolidActor.
        # Give the object a high mass, for stability.
        trial_commands.extend(self.add_solid_object(record=choice(self.object_records),
                                                    position={"x": -1.2, "y": 0, "z": -1.6},
                                                    rotation={"x": 0.0, "y": uniform(0, 360.0), "z": 0.0},
                                                    mass_scale=500,
                                                    particle_spacing=0.035))
        # Let the object settle.
        trial_commands.append({"$type": "step_physics",
                               "frames": 100})
        # Add the cloth with random parameters.
        trial_commands.extend(self.add_cloth_object(record=self.cloth_record,
                                                    position={"x": -1.2, "y": 2.0, "z": -1.6},
                                                    rotation={"x": 0, "y": 0, "z": 0},
                                                    o_id=self.cloth_id,
                                                    mass_scale=1,
                                                    mesh_tesselation=1,
                                                    tether_stiffness=uniform(0.5, 1.0),
                                                    bend_stiffness=uniform(0.5, 1.0),
                                                    stretch_stiffness=uniform(0.5, 1.0)))

        return trial_commands

    def get_per_frame_commands(self, frame: int, resp: List[bytes]) -> List[dict]:
        return [{"$type": "focus_on_object",
                 "object_id": self.cloth_id}]

    def get_field_of_view(self) -> float:
        return 65

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 150


if __name__ == "__main__":
    args = get_args("draping")
    Draping().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
