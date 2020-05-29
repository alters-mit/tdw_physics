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
Drop a cloth object onto the floor, varying cloth parameters per trial.
"""

class Folding(TransformsDataset):

    def __init__(self):

        self.cloth_id = 0

        self.special_lib = ModelLibrarian("models_special.json")

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
                          "iteration_count": 5,
                          "substep_count": 8,
                          "radius": 0.1875,
                          "damping": 0,
                          "drag": 0}
                        ])

        return commands


    def get_trial_initialization_commands(self) -> List[dict]:
        """
        Perform a single trial -- randomly select an orientation and a set of cloth parameters.

        """
        trial_commands = []

        # Randomize cloth parameters on each trial.
        t_stiff = uniform(0.1, 1.0)        
        b_stiff = uniform(0.1, 1.0)        
        s_stiff = uniform(0.1, 1.0)

       # Recreate cloth.
        trial_commands.extend(self.create_cloth(t_stiff, s_stiff, b_stiff))

        # Position and aim avatar.
        trial_commands.extend([{"$type": "teleport_avatar_to",
                                "position": {"x": 2.0, "y": 1, "z": 1}},
                               {"$type": "look_at_position",
                                "position": {"x": -1.2, "y": 0.5, "z": -1.6}}])

        return trial_commands


    def get_per_frame_commands(self, frame: int, resp: List[bytes]) -> List[dict]:
        return [{"$type": "focus_on_object",
                 "object_id": self.cloth_id}]


    def get_field_of_view(self) -> float:
        return 65

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 200


    def create_cloth(self, t_stiff: float, s_stiff: float, bend_stiff: float) -> List[dict]:
        cloth_commands = []

        self.cloth_id = Controller.get_unique_id()
        record = self.special_lib.get_record("cloth_square")

        # Create the cloth.
        cloth_commands.append(self.add_transforms_object(record=record, 
                                                   position={"x": -1.2, "y": 1.5, "z": -1.6},
                                                   rotation={"x": uniform(0, 90.0), "y": uniform(-90.0, 90.0), "z": uniform(-90.0, 90.0)},
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
    Folding().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)