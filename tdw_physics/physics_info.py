from typing import Dict
import pkg_resources
import io
import json
from tdw.librarian import ModelRecord
from tdw_physics.util import MODEL_LIBRARIES


class PhysicsInfo:
    """
    Physics info for an object.
    """

    def __init__(self, record: ModelRecord, mass: float, dynamic_friction: float, static_friction: float,
                 bounciness: float):
        """
        :param record: The model's metadata record.
        :param mass: The mass of the object.
        :param dynamic_friction: The dynamic friction.
        :param static_friction: The static friction.
        :param bounciness: The object's bounciness.
        """

        self.record = record
        self.mass = mass
        self.dynamic_friction = dynamic_friction
        self.static_friction = static_friction
        self.bounciness = bounciness


def _get_default_physics_info() -> Dict[str, PhysicsInfo]:
    """
    :return: The default object physics info from `data/physics_info.json`.
    """

    info: Dict[str, PhysicsInfo] = {}

    with io.open(pkg_resources.resource_filename(__name__, "data/physics_info.json"), "rt", encoding="utf-8") as f:
        _data = json.load(f)
        for key in _data:
            obj = _data[key]
            info[key] = PhysicsInfo(record=MODEL_LIBRARIES[obj["library"]].get_record(obj["name"]),
                                    mass=obj["mass"],
                                    bounciness=obj["bounciness"],
                                    dynamic_friction=obj["dynamic_friction"],
                                    static_friction=obj["static_friction"])
    return info


# The default physics info
PHYSICS_INFO: Dict[str, PhysicsInfo] = _get_default_physics_info()
