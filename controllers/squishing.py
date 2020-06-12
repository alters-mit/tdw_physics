import random
from abc import ABC, abstractmethod
from typing import List, Dict
from tdw.tdw_utils import TDWUtils
from tdw.librarian import ModelLibrarian
from tdw_physics.flex_dataset import FlexDataset
from tdw_physics.util import get_args


class _Scenario(ABC):
    @abstractmethod
    def get_soft_object_position(self) -> Dict[str, float]:
        """
        :return: The initial position of the soft (squishing) object.
        """

        raise Exception()

    @abstractmethod
    def get_soft_object_rotation(self) -> Dict[str, float]:
        """
        :return: The initial rotation of the soft (squishing) object.
        """

        raise Exception()

    @abstractmethod
    def get_camera_aim(self) -> Dict[str, float]:
        """
        :return: The position to aim the camera at.
        """

        raise Exception()

    @abstractmethod
    def get_other_object(self, c: FlexDataset) -> List[dict]:
        """
        :param c: The FlexDataset controller.

        :return: Commands to add another object.
        """

        raise Exception()

    @abstractmethod
    def get_force(self) -> dict:
        """
        :return: The force command.
        """

        raise Exception()

    @staticmethod
    def _get_random_other_object(c: FlexDataset, pos: Dict[str, float], rot: Dict[str, float]) -> List[dict]:
        """
        :param c: The FlexDataset controller.
        :param pos: The position of the object.
        :param rot: The rotation of the object.

        :return: Commands to random soft or solid object.
        """

        record = random.choice(c.model_librarian.records)
        commands = []
        s = random.uniform(0.4, 0.6)
        scale = {"x": s, "y": s, "z": s}
        o_id = c.get_unique_id()
        commands.extend(c.add_soft_object(record=record,
                                          position=pos,
                                          rotation=rot,
                                          scale=scale,
                                          cluster_stiffness=random.uniform(0.1, 0.2),
                                          link_stiffness=random.uniform(0.1, 0.6),
                                          mass_scale=random.uniform(1, 4),
                                          particle_spacing=0.0625,
                                          o_id=o_id))
        commands.append({"$type": "set_color",
                         "color": {"r": random.random(), "g": random.random(), "b": random.random(), "a": 1.0},
                         "id": o_id})
        return commands

class Drop(_Scenario):
    """
    Drop an object. Sometimes, drop it onto another object.
    """

    def get_soft_object_position(self) -> Dict[str, float]:
        return {"x": random.uniform(-0.125, 0.125), "y": random.uniform(1.5, 3.5), "z": random.uniform(-0.125, 0.125)}

    def get_soft_object_rotation(self) -> Dict[str, float]:
        return {"x": random.uniform(0, 360), "y": random.uniform(0, 360), "z": random.uniform(0, 360)}

    def get_other_object(self, c: FlexDataset) -> List[dict]:
        return []

    def get_force(self) -> dict:
        return {"$type": "do_nothing"}

    def get_camera_aim(self) -> Dict[str, float]:
        return {"x": 0, "y": 0.125, "z": 0}


class DropOnto(Drop):
    """
    Drop an object onto another object.
    """

    def get_other_object(self, c: FlexDataset) -> List[dict]:
        pos = {"x": random.uniform(-0.05, 0.05), "y": 0, "z": random.uniform(-0.05, 0.05)}
        rot = {"x": 0, "y": random.uniform(0, 360), "z": 0}
        return self._get_random_other_object(c=c, pos=pos, rot=rot)


class Squishing(FlexDataset):
    SCENARIOS = [Drop(), DropOnto()]

    def __init__(self, port: int = 1071):
        super().__init__(port=port)
        self.model_librarian = ModelLibrarian("models_flex.json")

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
        scenario: _Scenario = random.choice(self.SCENARIOS)

        commands = []
        soft_id = self.get_unique_id()
        s = random.uniform(0.4, 0.6)
        # Add the soft-body (squishable) object.
        commands.extend(self.add_soft_object(record=random.choice(self.model_librarian.records),
                                             o_id=soft_id,
                                             position=scenario.get_soft_object_position(),
                                             rotation=scenario.get_soft_object_rotation(),
                                             scale={"x": s, "y": s, "z": s},
                                             particle_spacing=0.0625,
                                             cluster_stiffness=random.uniform(0.1, 0.2),
                                             link_stiffness=random.uniform(0.1, 0.6),
                                             mass_scale=random.uniform(1, 4)))
        commands.append({"$type": "set_color",
                         "color": {"r": random.random(), "g": random.random(), "b": random.random(), "a": 1.0},
                         "id": soft_id})
        # Maybe add another object.
        commands.extend(scenario.get_other_object(self))

        # Add the force.
        commands.append(scenario.get_force())

        # Teleport the avatar to a reasonable position based on the height of the stack.
        # Look at the center of the stack, then jostle the camera rotation a bit.
        # Apply a slight force to the base object.
        a_pos = self.get_random_avatar_position(radius_min=1.5,
                                                radius_max=1.8,
                                                y_min=1,
                                                y_max=1.5,
                                                center=TDWUtils.VECTOR3_ZERO)

        # Move the avatar.
        cam_aim = scenario.get_camera_aim()
        commands.extend([{"$type": "teleport_avatar_to",
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
                          "angle": random.uniform(-5, 5)}])
        return commands

    def get_field_of_view(self) -> float:
        return 55

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return []

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame >= 200


if __name__ == "__main__":
    args = get_args("squishing")
    Squishing().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
