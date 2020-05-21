import numpy as np
from typing import List
import random
from pathlib import Path
from tdw.librarian import ModelLibrarian
from tdw.tdw_utils import TDWUtils
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset
from tdw_physics.util import MODEL_LIBRARIES


class Bouncing(RigidbodiesDataset):
    CAM_POSITIONS = [{"x": -5.85, "y": 1.0, "z": 2.7},
                     {"x": -5.35, "y": 1.0, "z": -1},
                     {"x": 4.3, "y": 1.0, "z": 2.3},
                     {"x": 4.95, "y": 2.0, "z": -1.65},
                     {"x": 1.95, "y": 2.0, "z": -3.25},
                     {"x": -4.2, "y": 1.0, "z": -3}]

    RAMPS = [MODEL_LIBRARIES["models_full.json"].get_record("ramp_with_platform_30"),
             MODEL_LIBRARIES["models_full.json"].get_record("ramp_with_platform_60")]
    RAMP_MASS = 500

    def __init__(self, port: int = 1071):
        self.toy_records = ModelLibrarian(str(Path("toys.json").resolve())).records
        self.ramp_positions = [{"x": 3.5, "y": 0.02, "z": 1.5},
                               {"x": -1, "y": 0.02, "z": 2.38},
                               {"x": 4.58, "y": 0.02, "z": -2.85},
                               {"x": -0.94, "y": 0.02, "z": -2.83},
                               {"x": -3.4, "y": 0.02, "z": 0}]
        self.ramp_rotations = [{"x": 0, "y": -45, "z": 0},
                               {"x": 0, "y": -90, "z": 0},
                               {"x": 0, "y": 30, "z": 0},
                               {"x": -90, "y": -190, "z": 0},
                               {"x": -90, "y": -120, "z": 0},
                               {"x": 0, "y": 120, "z": 0}]

        super().__init__(port=port)

    def get_field_of_view(self) -> float:
        return 65

    def get_scene_initialization_commands(self) -> List[dict]:
        return [self.get_add_scene("box_room_2018"),
                {"$type": "set_aperture",
                 "aperture": 3.0},
                {"$type": "set_post_exposure",
                 "post_exposure": 0.4},
                {"$type": "set_ambient_occlusion_intensity",
                 "intensity": 0.25},
                {"$type": "set_ambient_occlusion_thickness_modifier",
                 "thickness": 4.0}]

    def get_trial_initialization_commands(self) -> List[dict]:
        commands = []
        lib = MODEL_LIBRARIES["models_full.json"]

        random.shuffle(self.ramp_positions)
        random.shuffle(self.ramp_rotations)

        # Add ramps.
        for i in range(4):
            ramp_id = self.get_unique_id()
            commands.extend(self.add_physics_object(record=lib.get_record("ramp_with_platform_30"),
                                                    position=self.ramp_positions[i],
                                                    rotation=self.ramp_rotations[i],
                                                    mass=self.RAMP_MASS,
                                                    dynamic_friction=random.uniform(0.1, 0.9),
                                                    static_friction=random.uniform(0.1, 0.9),
                                                    bounciness=random.uniform(0.1, 0.9),
                                                    o_id=ramp_id))
            commands.extend([{"$type": "scale_object",
                              "id": ramp_id,
                              "scale_factor": {"x": 0.75, "y": 0.75, "z": 0.75}},
                             {"$type": "set_object_collision_detection_mode",
                              "mode": "continuous_speculative",
                              "id": ramp_id},
                             {"$type": "set_kinematic_state",
                              "id": ramp_id,
                              "is_kinematic": True,
                              "use_gravity": True}])
        # Teleport the avatar.
        cam_pos = random.choice(self.CAM_POSITIONS)
        cam_aim = {"x": 0, "y": 0.45, "z": 0}
        commands.extend([{"$type": "teleport_avatar_to",
                          "position": cam_pos},
                         {"$type": "look_at_position",
                          "position": cam_aim}])
        # Rotate the sensor container a little.
        for axis in ["pitch", "yaw"]:
            commands.extend([{"$type": "rotate_sensor_container_by",
                              "axis": axis,
                              "angle": random.uniform(-10, 10)},
                             {"$type": "set_focus_distance",
                              "focus_distance": TDWUtils.get_distance(cam_pos, cam_aim)}])

        # Add bouncing objects.
        random.shuffle(self.toy_records)
        for i in range(random.randint(2, 6)):
            toy_id = self.get_unique_id()
            pos = TDWUtils.get_random_point_in_circle(center=np.array([0, 0, 0]), radius=1.5)
            pos[1] = random.uniform(0.7, 2)
            record = self.toy_records[i]
            commands.extend(self.add_physics_object(record=record,
                                                    position=TDWUtils.array_to_vector3(pos),
                                                    rotation=TDWUtils.VECTOR3_ZERO,
                                                    mass=random.uniform(0.5, 4),
                                                    dynamic_friction=random.uniform(0.1, 0.7),
                                                    static_friction=random.uniform(0.1, 0.7),
                                                    bounciness=random.uniform(0.7, 1),
                                                    o_id=toy_id))
            s = TDWUtils.get_unit_scale(record) * random.uniform(0.85, 1.12)
            look_at = TDWUtils.array_to_vector3(TDWUtils.get_random_point_in_circle(center=np.array([0, 0, 0]),
                                                                                    radius=5))
            # Scale to "toy size" and look at a random point on the ground.
            commands.extend([{"$type": "scale_object",
                              "scale_factor": {"x": s, "y": s, "z": s},
                              "id": toy_id},
                             {"$type": "object_look_at_position",
                              "position": look_at,
                              "id": toy_id}])
            # Rotate the object randomly.
            for axis in ["yaw", "roll"]:
                commands.append({"$type": "rotate_object_by",
                                 "angle": random.uniform(-15, 15),
                                 "id": toy_id,
                                 "axis": axis,
                                 "is_world": False})
            # Apply a force.
            commands.append({"$type": "apply_force_magnitude_to_object",
                             "magnitude": random.uniform(20, 40),
                             "id": toy_id})
        return commands

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return []

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame >= 500


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("--dir", type=str, default="D:/bouncing", help="Root output directory.")
    parser.add_argument("--num", type=int, default=3000, help="The number of trials in the dataset.")
    parser.add_argument("--temp", type=str, default="D:/temp.hdf5", help="Temp path for incomplete files.")
    args = parser.parse_args()

    Bouncing().run(num=args.num, output_dir=args.dir, temp_path=args.temp)
