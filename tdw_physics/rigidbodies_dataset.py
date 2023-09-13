import random
from pathlib import Path
from typing import List, Tuple, Dict
from abc import ABC
import h5py
import numpy as np
from tdw.controller import Controller
from tdw.output_data import OutputData, Rigidbodies, Collision, EnvironmentCollision
from tdw.tdw_utils import TDWUtils
from tdw_physics.transforms_dataset import TransformsDataset
from tdw_physics.dataset import Dataset
from tdw_physics.physics_info import PhysicsInfo, PHYSICS_INFO


class RigidbodiesDataset(TransformsDataset, ABC):
    """
    A dataset for Rigidbody (PhysX) physics.
    """

    # Static physics data.
    MASSES: np.array = np.empty(dtype=np.float32, shape=0)
    STATIC_FRICTIONS: np.array = np.empty(dtype=np.float32, shape=0)
    DYNAMIC_FRICTIONS: np.array = np.empty(dtype=np.float32, shape=0)
    BOUNCINESSES: np.array = np.empty(dtype=np.float32, shape=0)
    # The physics info of each object instance. Useful for referencing in a controller, but not written to disk.
    PHYSICS_INFO: Dict[int, PhysicsInfo] = dict()

    @staticmethod
    def get_add_physics_object(model_name: str, object_id: int, position: Dict[str, float] = None,
                               rotation: Dict[str, float] = None, library: str = "",
                               scale_factor: Dict[str, float] = None, kinematic: bool = False, gravity: bool = True,
                               default_physics_values: bool = True, mass: float = 1, dynamic_friction: float = 0.3,
                               static_friction: float = 0.3, bounciness: float = 0.7, scale_mass: bool = True) -> List[dict]:
        """
        Add an object to the scene with physics values (mass, friction coefficients, etc.).

        :param model_name: The name of the model.
        :param position: The position of the model. If None, defaults to `{"x": 0, "y": 0, "z": 0}`.
        :param rotation: The starting rotation of the model, in Euler angles. If None, defaults to `{"x": 0, "y": 0, "z": 0}`.
        :param library: The path to the records file. If left empty, the default library will be selected. See `ModelLibrarian.get_library_filenames()` and `ModelLibrarian.get_default_library()`.
        :param object_id: The ID of the new object.
        :param scale_factor: The [scale factor](../api/command_api.md#scale_object).
        :param kinematic: If True, the object will be [kinematic](../api/command_api.md#set_kinematic_state).
        :param gravity: If True, the object won't respond to [gravity](../api/command_api.md#set_kinematic_state).
        :param default_physics_values: If True, use default physics values. Not all objects have default physics values. To determine if object does: `has_default_physics_values = model_name in DEFAULT_OBJECT_AUDIO_STATIC_DATA`.
        :param mass: The mass of the object. Ignored if `default_physics_values == True`.
        :param dynamic_friction: The [dynamic friction](../api/command_api.md#set_physic_material) of the object. Ignored if `default_physics_values == True`.
        :param static_friction: The [static friction](../api/command_api.md#set_physic_material) of the object. Ignored if `default_physics_values == True`.
        :param bounciness: The [bounciness](../api/command_api.md#set_physic_material) of the object. Ignored if `default_physics_values == True`.
        :param scale_mass: If True, the mass of the object will be scaled proportionally to the spatial scale.

        :return: A list of commands to add the object and apply physics values.
        """

        # Use override physics values.
        if not default_physics_values and model_name in PHYSICS_INFO:
            default_physics_values = False
            mass = PHYSICS_INFO[model_name].mass
            dynamic_friction = PHYSICS_INFO[model_name].dynamic_friction
            static_friction = PHYSICS_INFO[model_name].static_friction
            bounciness = PHYSICS_INFO[model_name].bounciness
        commands = TransformsDataset.get_add_physics_object(model_name=model_name,
                                                            object_id=object_id,
                                                            position=position,
                                                            rotation=rotation,
                                                            library=library,
                                                            scale_factor=scale_factor,
                                                            kinematic=kinematic,
                                                            gravity=gravity,
                                                            default_physics_values=default_physics_values,
                                                            mass=mass,
                                                            dynamic_friction=dynamic_friction,
                                                            static_friction=static_friction,
                                                            bounciness=bounciness,
                                                            scale_mass=scale_mass)
        # Log the object ID.
        Dataset.OBJECT_IDS = np.append(Dataset.OBJECT_IDS, object_id)
        # Get the static data from the commands (these values might be automatically set).
        mass = 0
        dynamic_friction = 0
        static_friction = 0
        bounciness = 0
        for command in commands:
            if command["$type"] == "set_mass":
                mass = command["mass"]
            elif command["$type"] == "set_physic_material":
                dynamic_friction = command["dynamic_friction"]
                static_friction = command["static_friction"]
                bounciness = command["bounciness"]
        # Cache the static data.
        RigidbodiesDataset.MASSES = np.append(RigidbodiesDataset.MASSES, mass)
        RigidbodiesDataset.DYNAMIC_FRICTIONS = np.append(RigidbodiesDataset.DYNAMIC_FRICTIONS, dynamic_friction)
        RigidbodiesDataset.STATIC_FRICTIONS = np.append(RigidbodiesDataset.STATIC_FRICTIONS, static_friction)
        RigidbodiesDataset.BOUNCINESSES = np.append(RigidbodiesDataset.BOUNCINESSES, bounciness)
        # Cache the physics info.
        record = Controller.MODEL_LIBRARIANS[library].get_record(model_name)
        RigidbodiesDataset.PHYSICS_INFO[object_id] = PhysicsInfo(record=record,
                                                                 mass=mass,
                                                                 dynamic_friction=dynamic_friction,
                                                                 static_friction=static_friction,
                                                                 bounciness=bounciness)
        return commands

    def trial(self, filepath: Path, temp_path: Path, trial_num: int) -> None:
        # Clear data.
        RigidbodiesDataset.MASSES = np.empty(dtype=int, shape=0)
        RigidbodiesDataset.DYNAMIC_FRICTIONS = np.empty(dtype=int, shape=0)
        RigidbodiesDataset.STATIC_FRICTIONS = np.empty(dtype=int, shape=0)
        RigidbodiesDataset.BOUNCINESSES = np.empty(dtype=int, shape=0)
        super().trial(filepath=filepath, temp_path=temp_path, trial_num=trial_num)

    @staticmethod
    def get_objects_by_mass(mass: float) -> List[int]:
        """
        :param mass: The mass threshold.

        :return: A list of object IDs for objects with mass <= the mass threshold.
        """

        return [o for o in RigidbodiesDataset.PHYSICS_INFO.keys() if RigidbodiesDataset.PHYSICS_INFO[o].mass < mass]

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
            min_force = RigidbodiesDataset.PHYSICS_INFO[o_id].mass * 2
            max_force = RigidbodiesDataset.PHYSICS_INFO[o_id].mass * 4
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
                          "exit": False,
                          "stay": False,
                          "collision_types": ["obj", "env"]},
                         {"$type": "send_rigidbodies",
                          "frequency": "always"}])
        return commands

    def _write_static_data(self, static_group: h5py.Group) -> None:
        super()._write_static_data(static_group)

        static_group.create_dataset("mass", data=RigidbodiesDataset.MASSES)
        static_group.create_dataset("static_friction", data=RigidbodiesDataset.STATIC_FRICTIONS)
        static_group.create_dataset("dynamic_friction", data=RigidbodiesDataset.DYNAMIC_FRICTIONS)
        static_group.create_dataset("bounciness", data=RigidbodiesDataset.BOUNCINESSES)

    def _write_frame(self, frames_grp: h5py.Group, resp: List[bytes], frame_num: int) -> \
            Tuple[h5py.Group, h5py.Group, dict, bool]:
        frame, objs, tr, done = super()._write_frame(frames_grp=frames_grp, resp=resp, frame_num=frame_num)
        num_objects = len(Dataset.OBJECT_IDS)
        # Physics data.
        velocities = np.empty(dtype=np.float32, shape=(num_objects, 3))
        angular_velocities = np.empty(dtype=np.float32, shape=(num_objects, 3))
        # Collision data.
        collision_ids = np.empty(dtype=np.int32, shape=(0, 2))
        collision_relative_velocities = np.empty(dtype=np.float32, shape=(0, 3))
        collision_contacts = np.empty(dtype=np.float32, shape=(0, 2, 3))
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
                for o_id, i in zip(Dataset.OBJECT_IDS, range(num_objects)):
                    velocities[i] = ri_dict[o_id]["vel"]
                    angular_velocities[i] = ri_dict[o_id]["ang"]
            elif r_id == "coll":
                co = Collision(r)
                collision_ids = np.append(collision_ids, [co.get_collider_id(), co.get_collidee_id()])
                collision_relative_velocities = np.append(collision_relative_velocities, co.get_relative_velocity())
                for i in range(co.get_num_contacts()):
                    collision_contacts = np.append(collision_contacts, np.array([co.get_contact_normal(i),
                                                                                 co.get_contact_point(i)]))
            elif r_id == "enco":
                en = EnvironmentCollision(r)
                env_collision_ids = np.append(env_collision_ids, en.get_object_id())
                for i in range(en.get_num_contacts()):
                    env_collision_contacts = np.append(env_collision_contacts, np.array([en.get_contact_normal(i),
                                                                                         en.get_contact_point(i)]))
        objs.create_dataset("velocities", data=velocities.reshape(num_objects, 3), compression="gzip")
        objs.create_dataset("angular_velocities", data=angular_velocities.reshape(num_objects, 3), compression="gzip")
        collisions = frame.create_group("collisions")
        collisions.create_dataset("object_ids", data=collision_ids.reshape((-1, 2)), compression="gzip")
        collisions.create_dataset("relative_velocities", data=collision_relative_velocities.reshape((-1, 3)),
                                  compression="gzip")
        collisions.create_dataset("contacts", data=collision_contacts.reshape((-1, 2, 3)), compression="gzip")
        env_collisions = frame.create_group("env_collisions")
        env_collisions.create_dataset("object_ids", data=env_collision_ids, compression="gzip")
        env_collisions.create_dataset("contacts", data=env_collision_contacts.reshape((-1, 2, 3)),
                                      compression="gzip")
        return frame, objs, tr, sleeping
