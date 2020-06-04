import base64
import numpy as np
import random
from typing import List
from tdw.output_data import FlexParticles
from tdw.tdw_utils import TDWUtils
from tdw_physics.cloth_dataset import ClothDataset
from tdw_physics.util import get_args


class Drag(ClothDataset):
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
                 "iteration_count": 5,
                 "substep_count": 8,
                 "radius": 0.1875,
                 "damping": 0,
                 "drag": 0}]

    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Add another object.
        commands.extend(self.add_cloth_object(record=self.cloth_record,
                                              position={"x": 0, "y": 1, "z": 0},
                                              rotation=TDWUtils.VECTOR3_ZERO,
                                              o_id=self.cloth_id,
                                              mass_scale=10,
                                              mesh_tesselation=1,
                                              tether_stiffness=random.uniform(0.5, 1.0),
                                              bend_stiffness=random.uniform(0.5, 1.0),
                                              stretch_stiffness=random.uniform(0.5, 1.0)))
        # Let the cloth settle.
        # Position and aim avatar.
        commands.extend([{"$type": "set_kinematic_state",
                          "id": self.cloth_id,
                          "is_kinematic": True,
                          "use_gravity": False},
                         {"$type": "step_physics",
                         "frames": 100}])
        # Add the other object.
        o_id = self.get_unique_id()
        commands.extend(self.add_solid_object(record=random.choice(self.object_records),
                                              position={"x": 0, "y": 0.2, "z": 0},
                                              rotation={"x": 0.0, "y": random.uniform(0, 360.0), "z": 0.0},
                                              mass_scale=1,
                                              particle_spacing=0.035,
                                              o_id=o_id))
        # Let the object settle.
        # Position and aim the camera.
        commands.extend([{"$type": "set_kinematic_state",
                          "id": o_id,
                          "is_kinematic": True,
                          "use_gravity": False},
                         {"$type": "step_physics",
                          "frames": 100},
                         {"$type": "teleport_avatar_to",
                          "position": self.get_random_avatar_position(2, 2.3, 1, 1.3, TDWUtils.VECTOR3_ZERO)},
                         {"$type": "look_at",
                          "id": self.cloth_id,
                          "use_centroid": True}])
        return commands

    def get_per_frame_commands(self, resp: List[bytes], frame) -> List[dict]:
        commands = super().get_per_frame_commands(resp, frame)
        # Apply a force.
        if frame == 1:
            for r in resp[:-1]:
                if FlexParticles.get_data_type_id(r) == "flex":
                    fp = FlexParticles(r)
                    forces = []
                    center = np.array(([0, 0, 0]))
                    for p in fp.get_particles(0):
                        if p[2] < 0.5 or p[0] < 0.5:
                            pos = np.array(p[:-1])
                            force = ((pos - center) / np.linalg.norm(pos - center)) * 300
                            forces.extend(force)
                            forces.append(p[3])

                    forces = np.array(forces, dtype=np.float32)
                    forces = base64.b64encode(forces)
                    commands.extend([{"$type": "apply_forces_to_flex_object_base64",
                                      "forces_and_ids_base64": forces.decode(),
                                      "id": self.cloth_id}])
        return commands


if __name__ == "__main__":
    args = get_args("drag")
    Drag().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
