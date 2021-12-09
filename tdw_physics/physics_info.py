import io
import pkg_resources
import json
from typing import Dict
from tdw.librarian import ModelRecord, ModelLibrarian
from tdw.controller import Controller


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


def __get_default_physics_info() -> Dict[str, PhysicsInfo]:
    """
    :return: The default object physics info from `data/physics_info.json`.
    """

    info: Dict[str, PhysicsInfo] = {}

    with io.open(pkg_resources.resource_filename(__name__, "data/physics_info.json"), "rt", encoding="utf-8") as f:
        _data = json.load(f)
        for key in _data:
            obj = _data[key]
            # Cache the library.
            if obj["library"] not in Controller.MODEL_LIBRARIANS:
                Controller.MODEL_LIBRARIANS[obj["library"]] = ModelLibrarian(obj["library"])
            info[key] = PhysicsInfo(record=Controller.MODEL_LIBRARIANS[obj["library"]].get_record(obj["name"]),
                                    mass=obj["mass"],
                                    bounciness=obj["bounciness"],
                                    dynamic_friction=obj["dynamic_friction"],
                                    static_friction=obj["static_friction"])
    return info


# The default physics info.
PHYSICS_INFO: Dict[str, PhysicsInfo] = __get_default_physics_info()
