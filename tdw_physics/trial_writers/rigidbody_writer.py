import h5py
import numpy as np
from typing import Dict, List, Tuple
from tdw.librarian import ModelRecord
from tdw.output_data import OutputData, Rigidbodies, Collision, EnvironmentCollision
from tdw_physics.trial_writers.trial_writer import TrialWriter


class RigidbodyWriter(TrialWriter):
    def __init__(self, f: h5py.File):
        super().__init__(f)
        self.f = f

        # Static physics data.
        self.masses = np.empty(dtype=np.float32, shape=0)
        self.static_frictions = np.empty(dtype=np.float32, shape=0)
        self.dynamic_frictions = np.empty(dtype=np.float32, shape=0)
        self.bouncinesses = np.empty(dtype=np.float32, shape=0)

    def write_static_data(self) -> h5py.Group:
        static_group = super().write_static_data()
        static_group.create_dataset("mass", data=self.masses)
        static_group.create_dataset("static_friction", data=self.static_frictions)
        static_group.create_dataset("dynamic_friction", data=self.dynamic_frictions)
        static_group.create_dataset("bounciness", data=self.bouncinesses)
        return static_group

    def add_object(self, o_id: int, record: ModelRecord, position: Dict[str, float], rotation: Dict[str, float],
                   mass: float, dynamic_friction: float, static_friction: float, bounciness: float) -> List[dict]:
        """
        Get commands to add an object to the scene. In doing so, append static information about that object.

        :param o_id: The unique ID of the object.
        :param record: The model record.
        :param position: The initial position of the object.
        :param rotation: The initial rotation of the object, in Euler angles.
        :param mass: The mass of the object.
        :param dynamic_friction: The dynamic friction of the object's physic material.
        :param static_friction: The static friction of the object's physic material.
        :param bounciness: The bounciness of the object's physic material.

        :return: A list of commands: `[add_object, set_mass, set_physic_material]`
        """

        # Log the static data.
        self.object_ids = np.append(self.object_ids, o_id)
        self.masses = np.append(self.masses, mass)
        self.dynamic_frictions = np.append(self.dynamic_frictions, dynamic_friction)
        self.static_frictions = np.append(self.static_frictions, static_friction)
        self.bouncinesses = np.append(self.bouncinesses, bounciness)

        # Return commands to create the object.
        return [{"$type": "add_object",
                 "id": o_id,
                 "name": record.name,
                 "url": record.get_url(),
                 "position": position,
                 "rotation": rotation,
                 "scale_factor": record.scale_factor,
                 "category": record.wcategory},
                {"$type": "set_mass",
                 "id": o_id,
                 "mass": mass},
                {"$type": "set_physic_material",
                 "id": o_id,
                 "dynamic_friction": dynamic_friction,
                 "static_friction": static_friction,
                 "bounciness": bounciness},
                {"$type": "set_object_collision_detection_mode",
                 "id": o_id,
                 "mode": "continuous_dynamic"}]

    def get_send_data_commands(self) -> List[dict]:
        """
        :return: A list of commands: `[send_transforms, send_camera_matrices, send_collisions, send_rigidbodies]`.
        """

        commands = super().get_send_data_commands()
        commands.extend([{"$type": "send_collisions",
                          "enter": True,
                          "exit": False,
                          "stay": False,
                          "collision_types": ["obj", "env"]},
                         {"$type": "send_rigidbodies",
                          "frequency": "always"}])
        return commands

    def write_frame(self, resp: List[bytes], frame_num: int) -> Tuple[h5py.Group, h5py.Group, dict, bool]:
        frame, objs, tr, done = super().write_frame(resp=resp, frame_num=frame_num)
        num_objects = len(self.object_ids)
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
                for o_id, i in zip(self.object_ids, range(num_objects)):
                    velocities[i] = ri_dict[o_id]["vel"]
                    angular_velocities[i] = ri_dict[o_id]["ang"]
            elif r_id == "coll":
                co = Collision(r)
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
        env_collisions = frame.create_group("env_collisions")
        env_collisions.create_dataset("object_ids", data=env_collision_ids, compression="gzip")
        env_collisions.create_dataset("contacts", data=env_collision_contacts.reshape((-1, 2, 3)),
                                      compression="gzip")
        return frame, objs, tr, sleeping
