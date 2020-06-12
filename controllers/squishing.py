import numpy as np
import random
from typing import List, Dict, Tuple
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelLibrarian
from tdw_physics.flex_dataset import FlexDataset
from tdw_physics.util import get_args


class Squishing(FlexDataset):
    def __init__(self, port: int = 1071):
        super().__init__(port=port)
        self.model_librarian = ModelLibrarian("models_flex.json")

        self.scenarios = [self.drop_onto_floor, self.drop_onto_object, self.push_into_wall, self.push_into_other]

        # Size of the room bounds (used for placing objects near walls).
        self.env_bounds = {"x": 4, "y": 0, "z": 2}
        # Padding near walls (used for placing objects near walls).
        self.env_padding = {"x": 0.5, "y": 0, "z": 0.5}

    def get_scene_initialization_commands(self) -> List[dict]:
        return [self.get_add_scene(scene_name="box_room_2018"),
                {"$type": "set_aperture",
                 "aperture": 4.8},
                {"$type": "set_post_exposure",
                 "post_exposure": 0.4},
                {"$type": "set_ambient_occlusion_intensity",
                 "intensity": 0.175},
                {"$type": "set_ambient_occlusion_thickness_modifier",
                 "thickness": 3.5},
                {"$type": "set_shadow_strength",
                 "strength": 1.0},
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
        # Select a random scenario.
        return random.choice(self.scenarios)()

    def get_field_of_view(self) -> float:
        return 68

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return []

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame >= 200

    def drop_onto_floor(self) -> List[dict]:
        """
        :return: A list of commands to drop a single object onto the floor.
        """

        commands, o_pos = self._drop()
        return commands

    def drop_onto_object(self) -> List[dict]:
        """
        :return: A list of commands to drop one object onto another.
        """

        commands, o_pos = self._drop()

        # Add a second object on the floor.
        second_object_commands, s_id = self._get_squishable(position={"x": o_pos["x"] + random.uniform(-0.125, 0.125),
                                                                      "y": 0,
                                                                      "z": o_pos["z"] + random.uniform(-0.125, 0.125)},
                                                            rotation={"x": 0,
                                                                      "y": random.uniform(0, 360),
                                                                      "z": 0})
        commands.extend(second_object_commands)
        return commands

    def push_into_wall(self) -> List[dict]:
        """
        :return: A list of commands to push an object into a wall.
        """

        # Pick a random position close to a wall and a random target position.
        if random.random() < 0.5:
            if random.random() < 0.5:
                x = self.env_bounds["x"]
                tx = x + 1
            else:
                x = -self.env_bounds["x"]
                tx = x - 1
            z = random.uniform(-self.env_bounds["z"], self.env_bounds["z"])
            tz = 0
        else:
            if random.random() < 0.5:
                z = self.env_bounds["z"]
                tz = z + 1
            else:
                z = -self.env_bounds["z"]
                tz = z - 1
            x = random.uniform(-self.env_bounds["x"], self.env_bounds["x"])
            tx = 0
        x += random.uniform(-0.5, 0.5)
        z += random.uniform(-0.5, 0.5)
        tx += random.uniform(-0.125, 0.125)
        tz += random.uniform(-0.125, 0.125)

        # Push the object.
        return self._push(position={"x": x, "y": 0, "z": z}, target={"x": tx, "y": 0, "z": tz})

    def push_into_other(self) -> List[dict]:
        """
        :return: A list of commands to push one object into another object.
        """

        # Get two points some distance from each other.
        p0 = np.array([0, 0, 0])
        p1 = np.array([0, 0, 0])
        center = np.array([0, 0, 0])
        count = 0
        while count < 1000 and np.linalg.norm(np.abs(p1 - p0)) < 1.5:
            p0 = TDWUtils.get_random_point_in_circle(center=center, radius=2)
            p1 = TDWUtils.get_random_point_in_circle(center=center, radius=2)
            count += 1
        # Get commands to create the first object and push it.
        commands = self._push(position=TDWUtils.array_to_vector3(p0), target=TDWUtils.array_to_vector3(p1))
        # Add commands for the second object.
        second_object_commands, s_id = self._get_squishable(position=TDWUtils.array_to_vector3(p1),
                                                            rotation={"x": 0,
                                                                      "y": random.uniform(0, 360),
                                                                      "z": 0})
        commands.extend(second_object_commands)
        return commands

    def _push(self, position: Dict[str, float], target: Dict[str, float]) -> List[dict]:
        """
        :param position: The initial position.
        :param target: The target position (used for the force vector).

        :return: A list of commands to push the object along the floor.
        """

        commands, soft_id = self._get_squishable(position=position,
                                                 rotation={"x": 0,
                                                           "y": random.uniform(0, 360),
                                                           "z": 0})
        # Apply a force towards the target.
        p0 = TDWUtils.vector3_to_array(position)
        p1 = TDWUtils.vector3_to_array(target)
        force = ((p1 - p0) / (np.linalg.norm(p1 - p0))) * random.uniform(4000, 6000)
        # Add a force.
        commands.append({"$type": "apply_force_to_flex_object",
                         "force": TDWUtils.array_to_vector3(force),
                         "id": soft_id})

        p_med = TDWUtils.array_to_vector3(np.array([(position["x"] + target["x"]) / 2, 0,
                                                    (position["z"] + target["z"]) / 2]))

        # Set the avatar.
        commands.extend(self._set_avatar(a_pos=self.get_random_avatar_position(radius_min=1.5,
                                                                               radius_max=1.8,
                                                                               y_min=1,
                                                                               y_max=1.5,
                                                                               center=p_med),
                                         cam_aim=p_med))
        return commands

    def _drop(self) -> Tuple[List[dict], Dict[str, float]]:
        """
        :return: A list of commands to drop the object, and the object's initial position.
        """

        o_pos = {"x": random.uniform(-0.5, 0.5),
                 "y": random.uniform(1.5, 3.5),
                 "z": random.uniform(-0.5, 0.5)}
        # Add the object.
        commands, soft_id = self._get_squishable(position=o_pos,
                                                 rotation={"x": random.uniform(0, 360),
                                                           "y": random.uniform(0, 360),
                                                           "z": random.uniform(0, 360)})
        # Teleport to the avatar to a random position using o_pos as a centerpoint.
        commands.extend(self._set_avatar(a_pos=self.get_random_avatar_position(radius_min=1.5,
                                                                               radius_max=1.8,
                                                                               y_min=1,
                                                                               y_max=1.5,
                                                                               center={"x": o_pos["x"],
                                                                                       "y": 0,
                                                                                       "z": o_pos["z"]}),
                                         cam_aim={"x": 0, "y": 0.125, "z": 0}))
        # Add a force.
        commands.append({"$type": "apply_force_to_flex_object",
                         "force": {"x": random.uniform(-100, 100),
                                   "y": random.uniform(0, -500),
                                   "z": random.uniform(-100, 100)},
                         "id": soft_id})
        return commands, o_pos

    def _get_squishable(self, position: Dict[str, float], rotation: [str, float]) -> Tuple[List[dict], int]:
        """
        Get a "squishable" soft-body object. The object is always a random Flex primitive with a random color.

        :param position: The initial position of the object.
        :param rotation: The initial rotation of the object.

        :return: A list of commands to create the object, and the object ID.
        """

        commands = []
        soft_id = self.get_unique_id()
        s = random.uniform(0.4, 0.6)
        # Add the soft-body (squishable) object.
        commands.extend(self.add_soft_object(record=random.choice(self.model_librarian.records),
                                             o_id=soft_id,
                                             position=position,
                                             rotation=rotation,
                                             scale={"x": s, "y": s, "z": s},
                                             particle_spacing=0.0625,
                                             cluster_stiffness=random.uniform(0.1, 0.2),
                                             link_stiffness=random.uniform(0.1, 0.6),
                                             mass_scale=random.uniform(1, 4)))
        commands.append({"$type": "set_color",
                         "color": {"r": random.random(), "g": random.random(), "b": random.random(), "a": 1.0},
                         "id": soft_id})
        return commands, soft_id

    @staticmethod
    def _set_avatar(a_pos: Dict[str, float], cam_aim: Dict[str, float]) -> List[dict]:
        """
        :param a_pos: The avatar position.
        :param cam_aim: The camera aim point.

        :return: A list of commands to teleport the avatar and rotate the sensor container.
        """

        return [{"$type": "teleport_avatar_to",
                 "position": a_pos},
                {"$type": "look_at_position",
                 "position": cam_aim},
                {"$type": "set_focus_distance",
                 "focus_distance": TDWUtils.get_distance(a_pos, cam_aim)},
                {"$type": "rotate_sensor_container_by",
                 "axis": "pitch",
                 "angle": random.uniform(-5, 5)},
                {"$type": "rotate_sensor_container_by",
                 "axis": "yaw",
                 "angle": random.uniform(-5, 5)}]


if __name__ == "__main__":
    args = get_args("squishing")
    Squishing().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
