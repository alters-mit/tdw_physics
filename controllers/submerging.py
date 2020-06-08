from tdw_physics.transforms_dataset import TransformsDataset
from tdw_physics.rigidbodies_dataset import PHYSICS_INFO
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelLibrarian
from tdw_physics.util import MODEL_LIBRARIES, get_args
from tdw.controller import Controller
from time import sleep
from random import choice, uniform
from platform import system
from tdw.flex.fluid_types import FluidTypes
from typing import Dict, List




"""
Create a fluid "container" with the NVIDIA Flex physics engine. Run several trials, dropping ball objects of increasing mass into the fluid.
"""

class Submerge(TransformsDataset):

    def __init__(self):
        self.model_list = [
                      #"b03_db_apps_tech_08_04",
                      #"trashbin",
                      #"trunck",
                      #"whirlpool_akzm7630ix",
                      #"satiro_sculpture",
                      #"towel-radiator-2",
                      #"b03_folding-screen-panel-room-divider",
                      #"naughtone_pinch_stool_chair",
                      #"microwave",
                      #"trunk_6810-0009",
                      "suitcase",
                      #"kayak_small",
                      #"elephant_bowl",
                      #"trapezoidal_table",
                      #"b05_pc-computer-printer-1",
                      #"dishwasher_4",
                      #"chista_slice_of_teak_table",
                      #"buddah",
                      #"b05_elsafe_infinity_ii",
                      #"backpack",
                      #"b06_firehydrant_lod0",
                      #"b05_ticketmachine",
                      #"b05_trophy",
                      #"b05_kitchen_aid_toster",
                      #"b05_heavybag",
                      #"bongo_drum_hr_blend",
                      #"b03_worldglobe",
                      #"ceramic_pot",
                      #"b04_kenmore_refr_70419",
                      #"b03_zebra",
                      #"b05_gibson_j-45",
                      #"b03_cow",
                      #"b03_sheep",
                      #"b04_stringer"
                     ]

        self.fluid_id = None
        self.pool_id = None

        ft = FluidTypes()
        self.fluid_types = ft.get_fluid_types()
        self.fluid_type_names = ft.get_fluid_type_names()

        self.fluid_type_selection = "water"

        self.special_lib = ModelLibrarian("models_special.json")
        self.full_lib = ModelLibrarian("models_full.json")

        super().__init__()


    def get_scene_initialization_commands(self) -> List[dict]:
        if system() != "Windows":
            raise Exception("Flex fluids are only supported in Windows (see Documentation/misc_frontend/flex.md)")

        

        # Randomly select a fluid type
        #self.fluid_type_selection = choice(self.fluid_types.fluid_type_names)

        commands = [self.get_add_scene(scene_name="tdw_room_2018"),
                    {"$type": "set_aperture",
                     "aperture": 4.8},
                    {"$type": "set_focus_distance",
                     "focus_distance": 2.25},
                    {"$type": "set_post_exposure",
                     "post_exposure": 0.4},
                    {"$type": "set_ambient_occlusion_intensity",
                     "intensity": 0.175},
                    {"$type": "set_ambient_occlusion_thickness_modifier",
                     "thickness": 3.5}]

        # Create the container, set up for fluids.
        # Slow down physics so the water can settle without splashing out of the container.
        commands.extend([{"$type": "create_flex_container",
                          "collision_distance": 0.04,
                          "static_friction": 0.1,
                          "dynamic_friction": 0.1,
                          "particle_friction": 0.1,
                          "viscocity": self.fluid_types[self.fluid_type_selection].viscosity,
                          "adhesion": self.fluid_types[self.fluid_type_selection].adhesion,
                          "cohesion": self.fluid_types[self.fluid_type_selection].cohesion,
                          "radius": 0.1,
                          "fluid_rest": 0.05,
                          "damping": 0.01,
                          "substep_count": 5,
                          "iteration_count": 8,
                          "buoyancy": 1.0},
                         {"$type": "set_time_step", 
                         "time_step": 0.005}
                        ])
 
        return commands

    def get_trial_initialization_commands(self) -> List[dict]:
        trial_commands = []

        # Load a pool container for the fluid.
        self.pool_id = Controller.get_unique_id()
        record = self.special_lib.get_record("fluid_receptacle1x1")
        trial_commands.append(self.add_transforms_object(record=record, 
                                                   position={"x": 0, "y": 0, "z": 0},
                                                   rotation={"x": 0, "y": 0, "z": 0},
                                                   o_id=self.pool_id))
        trial_commands.extend([{"$type": "scale_object", 
                                "id": self.pool_id, 
                                "scale_factor": {"x": 1.5, "y": 2.5, "z":1.5}}, 
                               {"$type": "set_kinematic_state", 
                                "id": self.pool_id, 
                                "is_kinematic": True, 
                                "use_gravity": False}])


        # Destroy the previous fluid object, if is has been assigned.
        if self.fluid_id != None:
            trial_commands.append({"$type": "destroy_flex_object", "id": self.fluid_id})
            
        # Select an object at random.
        model = choice(self.model_list)
        model_record = self.full_lib.get_record(model)

        # Recreate fluid.
        trial_commands.extend(self.create_fluid())

        # Randomly select an object, and randomly orient it.
        # Set the object to kinematic.
        # Set the solid actor and assign the container.
        # Reset physics time-step to a more normal value.
        info = PHYSICS_INFO[model] 
        o_id = Controller.get_unique_id()
        trial_commands.extend([self.add_transforms_object(record=model_record, 
                                                       position={"x": 0, "y": 2, "z": 0},
                                                       rotation={"x": uniform(-45.0, 45.0), "y": uniform(-45.0, 45.0), "z": uniform(-45.0, 45.0)},
                                                       o_id=o_id)])
        scale_val = uniform(0.25, 0.5)
        trial_commands.extend([{"$type": "scale_object", 
                                "id": o_id, 
                                "scale_factor": {"x": 0.5, "y": 0.5, "z": 0.5}}, 
                                {"$type": "set_kinematic_state", "id": o_id},
                                {"$type": "set_flex_solid_actor",
                                 "id": o_id,
                                 "mass_scale": info.mass,
                                 "particle_spacing": 0.05},
                                {"$type": "assign_flex_container",
                                 "id": o_id,
                                 "container_id": 0},
                                {"$type": "set_time_step", 
                                 "time_step": 0.03}])

        # Position and aim avatar.
        trial_commands.extend([{"$type": "teleport_avatar_to",
                                "position": {"x": -2.675, "y": 1.375, "z": 0}},
                               {"$type": "look_at",
                                "object_id": self.pool_id,
                                "use_centroid": True}])
        
        return trial_commands


    def create_fluid(self) -> List[dict]:
        # Add the fluid actor, using the FluidPrimitive. Allow 500 frames 
        #  for the fluid to settle before continuing.
        fluid_id = Controller.get_unique_id()
        # Cache the ID so we can destroy it at the start of each trial.
        self.fluid_id = fluid_id
        command = [{"$type": "load_flex_fluid_from_resources", 
                          "id": fluid_id, 
                          "orientation": {"x": 0, "y": 0, "z": 0}, 
                          "position": {"x": 0, "y": 1.0, "z": 0}},
                         {"$type": "create_flex_fluid_object",
                          "id": fluid_id,
                          "mass_scale": 1.0,
                          "particle_spacing": 0.05},
                         {"$type": "assign_flex_container",
                           "id": fluid_id,
                           "container_id": 0, 
                           "fluid_container": True,
                           "fluid_type": self.fluid_type_selection},
                         {"$type": "step_physics", "frames": 500}]

        return command


    def get_per_frame_commands(self, frame: int, resp: List[bytes]) -> List[dict]:
        return [{"$type": "focus_on_object",
                 "object_id": self.pool_id}]


    def get_field_of_view(self) -> float:
        return 35


    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 200

		
if __name__ == "__main__":
    args = get_args("submerging")
    Submerge().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)