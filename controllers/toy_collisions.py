from pathlib import Path
import random
import numpy as np
from typing import List, Dict
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelLibrarian
from tdw_physics.dataset import Dataset
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset
from tdw_physics.object_position import ObjectPosition
from tdw_physics.util import get_args


class ToysDataset(RigidbodiesDataset):
    """
    Per trial, create 2-3 "toys". Apply a force to one of them, directed at another.
    Per frame, save object/physics metadata and image data.
    """

    def __init__(self, port: int = 1071):
        lib = ModelLibrarian(str(Path("toys.json").resolve()))
        self.records = lib.records
        self._target_id: int = 0

        super().__init__(port=port)

    def get_field_of_view(self) -> float:
        return 55

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
                 "thickness": 3.5}]

    def get_trial_initialization_commands(self) -> List[dict]:
        num_objects = random.choice([2, 3])
        # Positions where objects will be placed (used to prevent interpenetration).
        object_positions: List[ObjectPosition] = []

        # Randomize the order of the records and pick the first one.
        # This way, the objects are always different.
        random.shuffle(self.records)

        commands = []

        # Add 2-3 objects.
        for i in range(num_objects):
            o_id = Controller.get_unique_id()
            record = self.records[i]

            # Set randomized physics values and update the physics info.
            scale = TDWUtils.get_unit_scale(record) * random.uniform(0.8, 1.1)

            # Get a random position.
            o_pos = self._get_object_position(object_positions=object_positions)
            # Add the object and the radius, which is defined by its scale.
            object_positions.append(ObjectPosition(position=o_pos, radius=scale))
            commands.extend(self.get_add_physics_object(model_name=self.records[i].name,
                                                        library="models_full.json",
                                                        object_id=o_id,
                                                        position=self._get_object_position(
                                                            object_positions=object_positions),
                                                        rotation={"x": 0, "y": random.uniform(-90, 90), "z": 0},
                                                        default_physics_values=False,
                                                        mass=random.uniform(1, 5),
                                                        dynamic_friction=random.uniform(0, 0.9),
                                                        static_friction=random.uniform(0, 0.9),
                                                        bounciness=random.uniform(0, 1),
                                                        scale_factor={"x": scale, "y": scale, "z": scale}))
        # Point one object at the center, and then offset the rotation.
        # Apply a force allow the forward directional vector.
        # Teleport the avatar and look at the object that will be hit. Then slightly rotate the camera randomly.
        # Listen for output data.
        force_id = int(Dataset.OBJECT_IDS[0])
        self._target_id = int(Dataset.OBJECT_IDS[1])
        commands.extend([{"$type": "object_look_at",
                          "other_object_id": self._target_id,
                          "id": force_id},
                         {"$type": "rotate_object_by",
                          "angle": random.uniform(-5, 5),
                          "id": force_id,
                          "axis": "yaw",
                          "is_world": True},
                         {"$type": "apply_force_magnitude_to_object",
                          "magnitude": random.uniform(20, 60),
                          "id": force_id},
                         {"$type": "teleport_avatar_to",
                          "position": self.get_random_avatar_position(radius_min=0.9, radius_max=1.5, y_min=0.5,
                                                                      y_max=1.25, center=TDWUtils.VECTOR3_ZERO)},
                         {"$type": "look_at",
                          "object_id": self._target_id,
                          "use_centroid": True},
                         {"$type": "rotate_sensor_container_by",
                          "axis": "pitch",
                          "angle": random.uniform(-5, 5)},
                         {"$type": "rotate_sensor_container_by",
                          "axis": "yaw",
                          "angle": random.uniform(-5, 5)},
                         {"$type": "focus_on_object",
                          "object_id": self._target_id}])
        return commands

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return [{"$type": "focus_on_object",
                 "object_id": self._target_id}]

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 1000

    @staticmethod
    def _get_object_position(object_positions: List[ObjectPosition], max_tries: int = 1000, radius: float = 2) -> \
            Dict[str, float]:
        """
        Try to get a valid random position that doesn't interpentrate with other objects.

        :param object_positions: The positions and radii of all objects so far that will be added to the scene.
        :param max_tries: Try this many times to get a valid position before giving up.
        :param radius: The radius to pick a position in.

        :return: A valid position that doesn't interpentrate with other objects.
        """

        o_pos = TDWUtils.array_to_vector3(TDWUtils.get_random_point_in_circle(center=np.array([0, 0, 0]),
                                                                              radius=radius))
        # Pick a position away from other objects.
        ok = False
        count = 0
        while not ok and count < max_tries:
            count += 1
            ok = True
            for o in object_positions:
                # If the object is too close to another object, try another position.
                if TDWUtils.get_distance(o.position, o_pos) <= o.radius:
                    ok = False
                    o_pos = TDWUtils.array_to_vector3(TDWUtils.get_random_point_in_circle(center=np.array([0, 0, 0]),
                                                                                          radius=radius))
        return o_pos


if __name__ == "__main__":
    args = get_args("toy_collisions")
    td = ToysDataset()
    td.run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
