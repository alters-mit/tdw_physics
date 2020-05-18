from typing import Dict
import pkg_resources
import io
import json
from tdw_physics.util import MODEL_LIBRARIES


class _PhysicsInfo:
    """
    Physics info for an object.
    """

    def __init__(self, name: str, library: str, mass: float, dynamic_friction: float, static_friction: float,
                 bounciness: float):
        """
        :param name: The name of the object.
        :param library: The model library.
        :param mass: The mass of the object.
        :param dynamic_friction: The dynamic friction.
        :param static_friction: The static friction.
        :param bounciness: The object's bounciness.
        """

        self.record = MODEL_LIBRARIES[library].get_record(name)
        self.mass = mass
        self.dynamic_friction = dynamic_friction
        self.static_friction = static_friction
        self.bounciness = bounciness


def _get_default_physics_info() -> Dict[str, _PhysicsInfo]:
    """
    :return: The default object physics info from `data/physics_info.json`.
    """

    info: Dict[str, _PhysicsInfo] = {}

    with io.open(pkg_resources.resource_filename(__name__, "data/physics_info.json"), "rt", encoding="utf-8") as f:
        _data = json.load(f)
        for key in _data:
            obj = _data[key]
            info[key] = _PhysicsInfo(name=obj["name"],
                                     library=obj["library"],
                                     mass=obj["mass"],
                                     bounciness=obj["bounciness"],
                                     dynamic_friction=obj["dynamic_friction"],
                                     static_friction=obj["static_friction"])
    return info


# The default physics info
PHYSICS_INFO: Dict[str, _PhysicsInfo] = _get_default_physics_info()
