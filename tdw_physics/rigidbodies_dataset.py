import random
from typing import List, Tuple, Dict, Optional
from abc import ABC
import h5py
import numpy as np
import pkg_resources
import io
import json
from tdw.output_data import OutputData, Rigidbodies, Collision, EnvironmentCollision
from tdw.librarian import ModelRecord
from tdw.tdw_utils import TDWUtils
from tdw_physics.transforms_dataset import TransformsDataset
from tdw_physics.util import MODEL_LIBRARIES, str_to_xyz


def handle_random_transform_args(args):
    if args is not None:
        try:
            args = json.loads(args)
        except:
            args = str_to_xyz(args)

        if 'class' in args:
            data = args['data']
            modname, classname = args['class']
            mod = importlib.import_module(modname)
            klass = get_attr(mod, classname)
            args = klass(data)
            assert callable(args)
        elif hasattr(args, 'keys'):
            assert "x" in args, args
            assert "y" in args, args
            assert "z" in args, args
        elif hasattr(args, '__len__'):
            assert len(args) == 2, (args, len(args))
        else:
            args + 0.0
    return args


class PhysicsInfo:
    """
    Physics info for an object.
    """

    def __init__(self,
                 record: ModelRecord,
                 mass: float,
                 dynamic_friction: float,
                 static_friction: float,
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


def get_range(scl):
    if hasattr(scl, '__len__'):
        return scl[0], scl[1]
    else:
        scl + 0.0
        return scl, scl


def get_random_xyz_transform(generator):
    if callable(generator):
        s = generator()
    elif hasattr(generator, 'keys'):
        sx0, sx1 = get_range(generator["x"])
        sx = random.uniform(sx0, sx1)
        sy0, sy1 = get_range(generator["y"])
        sy = random.uniform(sy0, sy1)
        sz0, sz1 = get_range(generator["z"])
        sz = random.uniform(sz0, sz1)
        s = {"x": sx, "y": sy, "z": sz}
    elif hasattr(generator, '__len__'):
        s0 = random.uniform(generator[0], generator[1])
        s = {"x": s0, "y": s0, "z": s0}
    else:
        generator + 0.0
        s = {"x": generator, "y": generator, "z": generator}
    assert hasattr(s, 'keys'), s
    assert 'x' in s, s
    assert 'y' in s, s
    assert 'z' in s, s
    return s


class RigidbodiesDataset(TransformsDataset, ABC):
    """
    A dataset for Rigidbody (PhysX) physics.
    """

    def __init__(self, port: int = 1071, monochrome: bool = False, **kwargs):
        super().__init__(port=port, **kwargs)

        self.physics_info: Dict[int, PhysicsInfo] = {}

        # Whether the objects will be set to the same color
        self.monochrome = monochrome


    def clear_static_data(self) -> None:
        super().clear_static_data()

        self.masses = np.empty(dtype=np.float32, shape=0)
        self.static_frictions = np.empty(dtype=np.float32, shape=0)
        self.dynamic_frictions = np.empty(dtype=np.float32, shape=0)
        self.bouncinesses = np.empty(dtype=np.float32, shape=0)
        self.colors = np.empty(dtype=np.float32, shape=(0,3))
        self.scales = []

    def _xyz_to_arr(self, xyz : dict):
        arr = np.array(
            [xyz[k] for k in ["x","y","z"]], dtype=np.float32)
        return arr

    def _arr_to_xyz(self, arr : np.ndarray):
        xyz = {k:arr[i] for i,k in enumerate(["x","y","z"])}
        return xyz

    def random_color(self, exclude=None, exclude_range=0.25):
        rgb = [random.random(), random.random(), random.random()]
        if exclude is None:
            return rgb

        assert len(exclude) == 3, exclude
        while all([np.abs(exclude[i] - rgb[i]) < exclude_range for i in range(3)]):
            rgb = [random.random(), random.random(), random.random()]
        return rgb

    def get_random_scale_transform(self, scale):
        return get_random_xyz_transform(scale)

    def random_primitive(self,
                         object_types: List[ModelRecord],
                         scale: List[float] = [0.2, 0.3],
                         color: List[float] = None,
                         exclude_color: List[float] = None,
                         exclude_range: float = 0.25
    ) -> dict:
        obj_record = random.choice(object_types)
        s = self.get_random_scale_transform(scale)
        obj_data = {
            "id": self.get_unique_id(),
            "scale": s,
            "color": np.array(color if color is not None else self.random_color(exclude_color, exclude_range)),
            "name": obj_record.name
        }
        self.scales.append(obj_data["scale"])
        self.colors = np.concatenate([self.colors, obj_data["color"].reshape((1,3))], axis=0)
        return obj_record, obj_data

    def add_physics_object(self,
                           record: ModelRecord,
                           position: Dict[str, float],
                           rotation: Dict[str, float],
                           mass: float,
                           dynamic_friction: float,
                           static_friction: float,
                           bounciness: float,
                           o_id: Optional[int] = None) -> List[dict]:
        """
        Get commands to add an object and assign physics properties. Write the object's static info to the .hdf5 file.

        :param o_id: The unique ID of the object. If None, a random ID will be generated.
        :param record: The model record.
        :param position: The initial position of the object.
        :param rotation: The initial rotation of the object, in Euler angles.
        :param mass: The mass of the object.
        :param dynamic_friction: The dynamic friction of the object's physic material.
        :param static_friction: The static friction of the object's physic material.
        :param bounciness: The bounciness of the object's physic material.

        :return: A list of commands: `[add_object, set_mass, set_physic_material]`
        """

        if o_id is None:
            o_id: int = self.get_unique_id()

        # Get the add_object command.
        add_object = self.add_transforms_object(o_id=o_id,
                                                record=record,
                                                position=position,
                                                rotation=rotation
                                                )

        self.masses = np.append(self.masses, mass)
        self.dynamic_frictions = np.append(self.dynamic_frictions, dynamic_friction)
        self.static_frictions = np.append(self.static_frictions, static_friction)
        self.bouncinesses = np.append(self.bouncinesses, bounciness)

        # Log the physics info per object for easy reference in a controller.
        self.physics_info[o_id] = PhysicsInfo(record=record,
                                              mass=mass,
                                              dynamic_friction=dynamic_friction,
                                              static_friction=static_friction,
                                              bounciness=bounciness)

        # Return commands to create the object.
        return [add_object,
                {"$type": "set_mass",
                 "id": o_id,
                 "mass": mass},
                {"$type": "set_physic_material",
                 "id": o_id,
                 "dynamic_friction": dynamic_friction,
                 "static_friction": static_friction,
                 "bounciness": bounciness}]

    def add_physics_object_default(self,
                                   name: str,
                                   position: Dict[str, float],
                                   rotation: Dict[str, float],
                                   o_id: Optional[int] = None) -> List[dict]:
        """
        Add an object with default physics material values.

        :param o_id: The unique ID of the object. If None, a random ID number will be generated.
        :param name: The name of the model.
        :param position: The initial position of the object.
        :param rotation: The initial rotation of the object.

        :return: A list of commands: `[add_object, set_mass, set_physic_material]`
        """

        info = PHYSICS_INFO[name]
        return self.add_physics_object(o_id=o_id, record=info.record, position=position, rotation=rotation,
                                       mass=info.mass, dynamic_friction=info.dynamic_friction,
                                       static_friction=info.static_friction, bounciness=info.bounciness)

    def get_objects_by_mass(self, mass: float) -> List[int]:
        """
        :param mass: The mass threshold.

        :return: A list of object IDs for objects with mass <= the mass threshold.
        """

        return [o for o in self.physics_info.keys() if self.physics_info[o].mass < mass]

    def get_falling_commands(self, mass: float = 3) -> List[List[dict]]:
        """
        :param mass: Objects with <= this mass might receive a force.

        :return: A list of lists; per-frame commands to make small objects fly up.
        """

        per_frame_commands: List[List[dict]] = []

        # Get a list of all small objects.
        small_ids = self.get_objects_by_mass(mass)
        random.shuffle(small_ids)
        max_num_objects = len(small_ids) if len(small_ids) < 8 else 8
        min_num_objects = max_num_objects - 3
        if min_num_objects <= 0:
            min_num_objects = 1
        # Add some objects.
        for i in range(random.randint(min_num_objects, max_num_objects)):
            o_id = small_ids.pop(0)
            force_dir = np.array([random.uniform(-0.125, 0.125), random.uniform(0.7, 1), random.uniform(-0.125, 0.125)])
            force_dir = force_dir / np.linalg.norm(force_dir)
            min_force = self.physics_info[o_id].mass * 2
            max_force = self.physics_info[o_id].mass * 4
            force = TDWUtils.array_to_vector3(force_dir * random.uniform(min_force, max_force))
            per_frame_commands.append([{"$type": "apply_force_to_object",
                                        "force": force,
                                        "id": o_id}])
            # Wait some frames.
            for j in range(10, 30):
                per_frame_commands.append([])
        return per_frame_commands

    def _get_send_data_commands(self) -> List[dict]:
        commands = super()._get_send_data_commands()
        commands.extend([{"$type": "send_collisions",
                          "enter": True,
                          "exit": True,
                          "stay": True,
                          "collision_types": ["obj", "env"]},
                         {"$type": "send_rigidbodies",
                          "frequency": "always"}])
        return commands

    def _write_static_data(self, static_group: h5py.Group) -> None:
        super()._write_static_data(static_group)

        ## physical
        static_group.create_dataset("mass", data=self.masses)
        static_group.create_dataset("static_friction", data=self.static_frictions)
        static_group.create_dataset("dynamic_friction", data=self.dynamic_frictions)
        static_group.create_dataset("bounciness", data=self.bouncinesses)

        ## size and colors
        static_group.create_dataset("color", data=self.colors)
        static_group.create_dataset("scale_x", data=[_s["x"] for _s in self.scales])
        static_group.create_dataset("scale_y", data=[_s["y"] for _s in self.scales])
        static_group.create_dataset("scale_z", data=[_s["z"] for _s in self.scales])

    def _write_frame(self, frames_grp: h5py.Group, resp: List[bytes], frame_num: int) -> \
            Tuple[h5py.Group, h5py.Group, dict, bool]:
        frame, objs, tr, done = super()._write_frame(frames_grp=frames_grp, resp=resp, frame_num=frame_num)
        num_objects = len(self.object_ids)
        # Physics data.
        velocities = np.empty(dtype=np.float32, shape=(num_objects, 3))
        angular_velocities = np.empty(dtype=np.float32, shape=(num_objects, 3))
        # Collision data.
        collision_ids = np.empty(dtype=np.int32, shape=(0, 2))
        collision_relative_velocities = np.empty(dtype=np.float32, shape=(0, 3))
        collision_contacts = np.empty(dtype=np.float32, shape=(0, 2, 3))
        collision_states = np.empty(dtype=str, shape=(0, 1))
        # Environment Collision data.
        env_collision_ids = np.empty(dtype=np.int32, shape=(0, 1))
        env_collision_contacts = np.empty(dtype=np.float32, shape=(0, 2, 3))

        sleeping = True

        for r in resp[:-1]:
            r_id = OutputData.get_data_type_id(r)
            if r_id == "rigi":
                ri = Rigidbodies(r)
                ri_dict = dict()
                for i in range(ri.get_num()):
                    ri_dict.update({ri.get_id(i): {"vel": ri.get_velocity(i),
                                                   "ang": ri.get_angular_velocity(i)}})
                    # Check if any objects are sleeping that aren't in the abyss.
                    if not ri.get_sleeping(i) and tr[ri.get_id(i)]["pos"][1] >= -1:
                        sleeping = False
                # Add the Rigibodies data.
                for o_id, i in zip(self.object_ids, range(num_objects)):
                    velocities[i] = ri_dict[o_id]["vel"]
                    angular_velocities[i] = ri_dict[o_id]["ang"]
            elif r_id == "coll":
                co = Collision(r)
                collision_states = np.append(collision_states, co.get_state())
                collision_ids = np.append(collision_ids, [co.get_collider_id(), co.get_collidee_id()])
                collision_relative_velocities = np.append(collision_relative_velocities, co.get_relative_velocity())
                for i in range(co.get_num_contacts()):
                    collision_contacts = np.append(collision_contacts, (co.get_contact_normal(i),
                                                                        co.get_contact_point(i)))
            elif r_id == "enco":
                en = EnvironmentCollision(r)
                env_collision_ids = np.append(env_collision_ids, en.get_object_id())
                for i in range(en.get_num_contacts()):
                    env_collision_contacts = np.append(env_collision_contacts, (en.get_contact_normal(i),
                                                                                en.get_contact_point(i)))
        objs.create_dataset("velocities", data=velocities.reshape(num_objects, 3), compression="gzip")
        objs.create_dataset("angular_velocities", data=angular_velocities.reshape(num_objects, 3), compression="gzip")
        collisions = frame.create_group("collisions")
        collisions.create_dataset("object_ids", data=collision_ids.reshape((-1, 2)), compression="gzip")
        collisions.create_dataset("relative_velocities", data=collision_relative_velocities.reshape((-1, 3)),
                                  compression="gzip")
        collisions.create_dataset("contacts", data=collision_contacts.reshape((-1, 2, 3)), compression="gzip")
        collisions.create_dataset("states", data=collision_states.astype('S'), compression="gzip")
        env_collisions = frame.create_group("env_collisions")
        env_collisions.create_dataset("object_ids", data=env_collision_ids, compression="gzip")
        env_collisions.create_dataset("contacts", data=env_collision_contacts.reshape((-1, 2, 3)),
                                      compression="gzip")
        return frame, objs, tr, sleeping
