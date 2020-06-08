import numpy as np
import random
from typing import List
from tdw.output_data import FlexParticles
from tdw.tdw_utils import TDWUtils
from tdw_physics.cloth_dataset import ClothDataset
from tdw_physics.util import get_args


class Dragging(ClothDataset):
    """
    Add a cloth. Place an object on the cloth. Add forces to a portion of the cloth to "drag" the object.
    """

    # Define the corners of the cloth.
    _CORNERS: List[np.array] = [np.array([1, 0, 1]),
                                np.array([1, 0, -1]),
                                np.array([-1, 0, -1]),
                                np.array([-1, 0, 1])]

    def __init__(self, port: int = 1071):
        super().__init__(port=port)
        # The number of frames during which a force will be applied.
        self._num_force_frames: int = 0
        self._corner: np.array = self._CORNERS[0]
        self._corner_radius = 0
        # The force magnitude per frame.
        self._force_per_frame: float = 0

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
                 "solid_rest": 0.03,
                 "damping": 0,
                 "drag": 0}]

    def get_trial_initialization_commands(self) -> List[dict]:
        self._num_force_frames = random.randint(5, 10)

        # Get a random corner.
        self._corner = random.choice(self._CORNERS)
        self._corner_radius = random.uniform(0.5, 0.85)

        self._force_per_frame = random.uniform(-30, -55)

        commands = []
        commands.extend(self.add_cloth_object(record=self.cloth_record,
                                              position={"x": 0, "y": 1, "z": 0},
                                              rotation=TDWUtils.VECTOR3_ZERO,
                                              o_id=self.cloth_id,
                                              mass_scale=10,
                                              mesh_tesselation=1,
                                              tether_stiffness=random.uniform(0.5, 1),
                                              bend_stiffness=random.uniform(0.5, 1),
                                              stretch_stiffness=random.uniform(0.5, 1)))
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
                                              mass_scale=random.uniform(0.25, 1),
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
                          "position": self.get_random_avatar_position(1.8, 2.1, 1, 1.3, TDWUtils.VECTOR3_ZERO)},
                         {"$type": "look_at",
                          "id": self.cloth_id,
                          "use_centroid": True}])
        return commands

    def get_per_frame_commands(self, resp: List[bytes], frame) -> List[dict]:
        commands = super().get_per_frame_commands(resp, frame)
        # Apply a force.
        if frame < self._num_force_frames:
            for r in resp[:-1]:
                if FlexParticles.get_data_type_id(r) == "flex":
                    fp = FlexParticles(r)
                    for i in range(fp.get_num_objects()):
                        # Find the cloth.
                        if fp.get_id(i) == self.cloth_id:
                            forces = []
                            p_id = 0
                            for p in fp.get_particles(i):
                                # Add a force if this is a "corner particle".
                                if np.abs(np.linalg.norm(p[:-1] - self._corner)) <= self._corner_radius:
                                    # Calculate the force.
                                    pos = np.array(p[:-1])
                                    force = ((pos - self._corner) / np.linalg.norm(pos - self._corner)) * self.\
                                        _force_per_frame
                                    # Add the force and particle ID.
                                    forces.extend(force)
                                    forces.append(p_id)
                                p_id += 1
                            # Encode and send the force.
                            commands.extend([{"$type": "apply_forces_to_flex_object_base64",
                                              "forces_and_ids_base64": TDWUtils.get_base64_flex_particle_forces(forces),
                                              "id": self.cloth_id}])
        return commands


if __name__ == "__main__":
    args = get_args("dragging")
    Dragging().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
