from random import choice, uniform, random
from typing import List
from tdw_physics.cloth_dataset import ClothDataset
from tdw_physics.util import get_args


class Draping(ClothDataset):
    """
    Using NVIDIA Flex, drape a randomly-selected object with a cloth object.
    20% of the time, no object is selected.
    """

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
                 "damping": 0,
                 "drag": 0}]

    def get_trial_initialization_commands(self) -> List[dict]:
        """
        Randomly select an object and orientation, and drape it using a given set of cloth parameters.

        """
        # Position and aim avatar.
        trial_commands = [{"$type": "teleport_avatar_to",
                           "position": {"x": 2.0, "y": 1, "z": 1}},
                          {"$type": "look_at_position",
                           "position": {"x": -1.2, "y": 0.5, "z": -1.6}}]

        # 20% of the time, don't add another object.
        another_object = random() > 0.2
        if another_object:
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
        if another_object:
            rotation = {"x": 0, "y": 0, "z": 0}
        else:
            rotation = {"x": uniform(0, 90.0), "y": uniform(-90.0, 90.0), "z": uniform(-90.0, 90.0)}
        trial_commands.extend(self.add_cloth_object(record=self.cloth_record,
                                                    position={"x": -1.2, "y": 2.0, "z": -1.6},
                                                    rotation=rotation,
                                                    o_id=self.cloth_id,
                                                    mass_scale=1,
                                                    mesh_tesselation=1,
                                                    tether_stiffness=uniform(0.5, 1.0),
                                                    bend_stiffness=uniform(0.5, 1.0),
                                                    stretch_stiffness=uniform(0.5, 1.0)))

        return trial_commands

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return [{"$type": "focus_on_object",
                 "object_id": self.cloth_id}]


if __name__ == "__main__":
    args = get_args("draping")
    Draping().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
