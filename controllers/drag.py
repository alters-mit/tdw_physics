import base64
import numpy as np
import random
from typing import List
from tdw.output_data import FlexParticles
from tdw.tdw_utils import TDWUtils
from tdw_physics.cloth_dataset import ClothDataset
from tdw_physics.util import get_args


class Drag(ClothDataset):
    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        # Add another object.
        commands.extend(self.add_cloth_object(record=self.cloth_record,
                                              position={"x": 0, "y": 0.01, "z": 0},
                                              rotation=TDWUtils.VECTOR3_ZERO,
                                              o_id=self.cloth_id,
                                              mass_scale=1,
                                              mesh_tesselation=1,
                                              tether_stiffness=random.uniform(0.5, 1.0),
                                              bend_stiffness=random.uniform(0.5, 1.0),
                                              stretch_stiffness=random.uniform(0.5, 1.0)))
        # Let the objects settle.
        # Position and aim avatar.
        commands.extend([{"$type": "step_physics",
                         "frames": 10},
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
            o_id = self.get_unique_id()
            commands.extend(self.add_solid_object(record=random.choice(self.object_records),
                                                  position={"x": 0, "y": 0.02, "z": 0},
                                                  rotation={"x": 0.0, "y": random.uniform(0, 360.0), "z": 0.0},
                                                  mass_scale=1000,
                                                  particle_spacing=0.035,
                                                  o_id=o_id))
            commands.append({"$type": "set_kinematic_state",
                             "id": o_id,
                             "is_kinematic": False})
            for r in resp[:-1]:
                if FlexParticles.get_data_type_id(r) == "flex":
                    fp = FlexParticles(r)
                    forces = []
                    center = np.array(([0, 0, 0]))
                    for p in fp.get_particles(0):
                        if p[2] < 0.5 or p[0] < 0.5:
                            pos = np.array(p[:-1])
                            force = ((pos - center) / np.linalg.norm(pos - center)) * -30
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