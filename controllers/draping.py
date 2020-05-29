from tdw_physics.transforms_dataset import TransformsDataset
from tdw_physics.rigidbodies_dataset import PHYSICS_INFO
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelLibrarian
from tdw_physics.util import MODEL_LIBRARIES, get_args
from tdw.controller import Controller
from time import sleep
from random import choice, uniform
from typing import List, Dict, Tuple
import h5py

"""
Using NVIDIA Flex, drape a randomly-selected object with a cloth object.
"""

class Draping(TransformsDataset):

    def __init__(self):
        self.object_list = ["linbrazil_diz_armchair", 
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

        self.object_pos = {"x": -1.2, "y": 0, "z": -1.6}

        self.cloth_id = 0

        self.special_lib = ModelLibrarian("models_special.json")
        self.full_lib = ModelLibrarian("models_full.json")

        super().__init__()


    def get_scene_initialization_commands(self) -> List[dict]:
        commands = [self.get_add_scene(scene_name="tdw_room_2018"),
                    {"$type": "set_aperture",
                     "aperture": 3.0},
                    {"$type": "set_focus_distance",
                     "focus_distance": 2.25},
                    {"$type": "set_post_exposure",
                     "post_exposure": 0.4},
                    {"$type": "set_ambient_occlusion_intensity",
                     "intensity": 0.25},
                    {"$type": "set_ambient_occlusion_thickness_modifier",
                     "thickness": 4.0}]

        # Create the Flex container.
        commands.extend([{"$type": "create_flex_container",
                          "collision_distance": 0.001,
                          "static_friction": 1.0,
                          "dynamic_friction": 1.0,
                          "iteration_count": 12,
                          "substep_count": 12,
                          "radius": 0.1875,
                          "damping": 0.25,
                          "drag": 0}
                        ])

        return commands


    def get_trial_initialization_commands(self) -> List[dict]:
        """
        Perform a single trial -- randomly select an object and orientation, and drape it using a given set of cloth parameters.

        """
        trial_commands = []

        # Randomize cloth parameters on each trial.
        t_stiff = uniform(0.5, 1.0)        
        b_stiff = uniform(0.5, 1.0)        
        s_stiff = uniform(0.5, 1.0)

        o_id = Controller.get_unique_id()
        object_name = choice(self.object_list)
        print("Working on object: " + object_name)
        record = self.full_lib.get_record(object_name)

        # Add object and convert to Flex SolidActor.
        trial_commands.append(self.add_transforms_object(record=record, 
                                                   position=self.object_pos,
                                                   rotation={"x": 0.0, "y": uniform(0, 360.0), "z": 0.0},
                                                   o_id=o_id))

        # Create the Flex actor, and give it some time to settle before dropping the cloth.
        # Give the object a high mass, for stability.
        trial_commands.extend([{"$type": "set_flex_solid_actor",
                                 "id": o_id,
                                 "mass_scale": 500.0,
                                 "particle_spacing": 0.035},
                                {"$type": "assign_flex_container",
                                 "id": o_id,
                                 "container_id": 0},
                                {"$type": "set_time_step", 
                                 "time_step": 0.03},
                                {"$type": "step_physics", "frames": 100}])

        # Position and aim avatar.
        trial_commands.extend([{"$type": "teleport_avatar_to",
                                "position": {"x": 2.0, "y": 1, "z": 1}},
                               {"$type": "look_at_position",
                                "position": {"x": -1.2, "y": 0.5, "z": -1.6}}])

        # Create cloth.
        trial_commands.extend(self.create_cloth(t_stiff, s_stiff, b_stiff))

        return trial_commands


    def get_per_frame_commands(self, frame: int, resp: List[bytes]) -> List[dict]:
        return [{"$type": "focus_on_object",
                 "object_id": self.cloth_id}]

    def get_field_of_view(self) -> float:
        return 65

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 150


    def create_cloth(self, t_stiff: float, s_stiff: float, bend_stiff: float) -> List[dict]:
        cloth_commands = []

        self.cloth_id = Controller.get_unique_id()
        record = self.special_lib.get_record("cloth_square")

        # Create the cloth.
        cloth_commands.append(self.add_transforms_object(record=record, 
                                                   position={"x": -1.2, "y": 2.0, "z": -1.6},
                                                   rotation={"x": 0, "y": 0, "z": 0},
                                                   o_id=self.cloth_id))

        # Create the Flex actor, and give it some time to settle before dropping the cloth.
        cloth_commands.extend([{"$type": "set_kinematic_state", "id": self.cloth_id, "is_kinematic": True, "use_gravity": False},
                               {"$type": "set_flex_cloth_actor",
                                "id": self.cloth_id,
                                "mass_scale": 1,
                                "mesh_tesselation": 1,
                                "tether_stiffness": t_stiff,
                                "bend_stiffness": bend_stiff,
                                "self_collide": False,
                                "stretch_stiffness": s_stiff},
                                {"$type": "assign_flex_container",
                                 "id": self.cloth_id,
                                 "container_id": 0}])

        return cloth_commands


		
if __name__ == "__main__":
    args = get_args("draping")
    Draping().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)