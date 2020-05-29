from typing import Dict, List, Optional, Tuple
import h5py
from abc import ABC
from tdw.librarian import ModelRecord
from tdw.output_data import FlexParticles
from tdw_physics.transforms_dataset import TransformsDataset


class _Actor(ABC):
    """
    Static data for a Flex Actor.
    """

    def __init__(self, o_id: int, mass_scale: float):
        self.o_id = o_id
        self.mass_scale = mass_scale


class _SolidActor(_Actor):
    """
    Static data for a Flex Solid Actor.
    """

    def __init__(self, o_id: int, mass_scale: float, mesh_expansion: float, particle_spacing: float):
        super().__init__(o_id, mass_scale)

        self.mesh_expansion = mesh_expansion
        self.particle_spacing = particle_spacing


class _SoftActor(_Actor):
    """
    Static data for a Flex Soft Actor.
    """

    def __init__(self, o_id: int, mass_scale: float, volume_sampling: float, surface_sampling: float,
                 cluster_spacing: float, cluster_radius: float, cluster_stiffness: float, link_radius: float,
                 link_stiffness: float, particle_spacing: float):
        super().__init__(o_id, mass_scale)
        self.volume_sampling = volume_sampling
        self.surface_sampling = surface_sampling
        self.cluster_spacing = cluster_spacing
        self.cluster_radius = cluster_radius
        self.cluster_stiffness = cluster_stiffness
        self.link_radius = link_radius
        self.link_stiffness = link_stiffness
        self.particle_spacing = particle_spacing


class _ClothActor(_Actor):
    """
    Static data for a Flex Cloth Actor.
    """

    def __init__(self, o_id: int, mass_scale: float, mesh_tesselation: int, stretch_stiffness: float,
                 bend_stiffness: float, tether_stiffness: float, tether_give: float, pressure: float):
        super().__init__(o_id, mass_scale)

        self.mesh_tesselation = mesh_tesselation
        self.stretch_stiffness = stretch_stiffness
        self.bend_stiffness = bend_stiffness
        self.tether_stiffness = tether_stiffness
        self.tether_give = tether_give
        self.pressure = pressure


class FlexDataset(TransformsDataset, ABC):
    """
    A dataset for Flex physics.
    """

    def __init__(self, port: int = 1071):
        super().__init__(port=port)

        self._flex_container_command: dict = {}
        self._solid_actors: List[_SolidActor] = []
        self._soft_actors: List[_SoftActor] = []
        self._cloth_actors: List[_ClothActor] = []

    def _write_static_data(self, static_group: h5py.Group) -> None:
        super()._write_static_data(static_group)

        # Write the Flex container info.
        for key in self._flex_container_command:
            if key == "$type":
                continue
            static_group.create_dataset(key, data=[self._flex_container_command[key]])

        # Flatten the actor data and write it.
        for actors, group_name in zip([self._solid_actors, self._soft_actors, self._cloth_actors],
                                      ["solid_actors", "soft_actors", "cloth_actors"]):
            actor_data = dict()
            for actor in actors:
                for key in actor.__dict__:
                    if key not in actor_data:
                        actor_data.update({key: []})
                    actor_data[key].append(actor.__dict__[key])
            # Write the data.
            actors_group = static_group.create_group(group_name)
            for key in actor_data:
                actors_group.create_dataset(key, data=actor_data[key])

    def _write_frame(self, frames_grp: h5py.Group, resp: List[bytes], frame_num: int) -> \
            Tuple[h5py.Group, h5py.Group, dict, bool]:
        frame, objs, tr, done = super()._write_frame(frames_grp=frames_grp, resp=resp, frame_num=frame_num)
        particles_group = frame.create_group("particles")
        velocities_group = frame.create_group("velocities")
        for r in resp[:-1]:
            if FlexParticles.get_data_type_id(r) == "flex":
                f = FlexParticles(r)
                flex_dict = dict()
                for i in range(f.get_num_objects()):
                    flex_dict.update({f.get_id(i): {"par": f.get_particles(i),
                                                    "vel": f.get_velocities(i)}})
                # Add the Flex data.
                for o_id in self.object_ids:
                    particles_group.create_dataset(str(o_id), data=flex_dict[o_id]["par"])
                    velocities_group.create_dataset(str(o_id), data=flex_dict[o_id]["vel"])
        return frame, objs, tr, done
                
    def get_create_flex_container(self, radius: float = 0.1875, solid_rest: float = 0.125, fluid_rest: float = 0.1125,
                                  static_friction: float = 0.5, dynamic_friction: float = 0.5,
                                  particle_friction: float = 0.5, collision_distance: float = 0.0625,
                                  substep_count: int = 3, iteration_count: int = 8, damping: float = 1, drag: float = 0,
                                  shape_collision_margin: float = 0, planes: list = None, cohesion: float = 0.025,
                                  surface_tension: float = 0, viscocity: float = 0, vorticity: float = 0,
                                  buoyancy: float = 1, adhesion: float = 0, anisotropy_scale: float = 0,
                                  max_particles: int = 10000, max_neighbors: int = 100) -> dict:
        """
        Create a valid `create_flex_container` command writes all of the parameters to the .hdf5 file.
        The parameters of this function are identical to that of the `create_flex_container` command.
        See the TDW Command API for more information.

        :return: A valid `create_flex_container` command
        """

        if planes is None:
            planes = []
        self._flex_container_command = {"$type": "create_flex_container",
                                        "radius": radius,
                                        "solid_rest": solid_rest,
                                        "fluid_rest": fluid_rest,
                                        "static_friction": static_friction,
                                        "dynamic_friction": dynamic_friction,
                                        "particle_friction": particle_friction,
                                        "collision_distance": collision_distance,
                                        "substep_count": substep_count,
                                        "iteration_count": iteration_count,
                                        "damping": damping,
                                        "drag": drag,
                                        "shape_collision_margin": shape_collision_margin,
                                        "planes": planes,
                                        "cohesion": cohesion,
                                        "surface_tension": surface_tension,
                                        "viscocity": viscocity,
                                        "vorticity": vorticity,
                                        "buoyancy": buoyancy,
                                        "adhesion": adhesion,
                                        "anisotropy_scale": anisotropy_scale,
                                        "max_particles": max_particles,
                                        "max_neighbors": max_neighbors}
        return self._flex_container_command

    def add_solid_object(self, record: ModelRecord, position: Dict[str, float], rotation: Dict[str, float],
                         scale: Dict[str, float] = None, mesh_expansion: float = 0, particle_spacing: float = 0.125,
                         mass_scale: float = 1, o_id: Optional[int] = None) -> List[dict]:
        """
        Add a Flex Solid Actor object and cache static data. See Command API for more Flex parameter info.

        :param record: The model record.
        :param position: The initial position of the object.
        :param rotation: The initial rotation of the object.
        :param scale: The object scale factor. If None, the scale is (1, 1, 1).
        :param mesh_expansion:
        :param particle_spacing:
        :param mass_scale:
        :param o_id: The object ID. If None, a random ID is created.

        :return: `[add_object, scale_object, set_flex_solid_actor, set_flex_object_mass, assign_flex_container]`
        """

        if o_id is None:
            o_id = self.get_unique_id()
        if scale is None:
            scale = {"x": 1, "y": 1, "z": 1}

        # Get the add_object command.
        add_object = self.add_transforms_object(record=record, position=position, rotation=rotation, o_id=o_id)
        # Cache the static data.
        self._solid_actors.append(_SolidActor(o_id=o_id, mass_scale=mass_scale, mesh_expansion=mesh_expansion,
                                              particle_spacing=particle_spacing))
        return [add_object,
                {"$type": "scale_object",
                 "scale_factor": scale,
                 "id": o_id},
                {"$type": "set_flex_solid_actor",
                 "id": o_id,
                 "mesh_expansion": mesh_expansion,
                 "particle_spacing": particle_spacing,
                 "mass_scale": mass_scale},
                {"$type": "assign_flex_container",
                 "container_id": 0,
                 "id": o_id}]

    def add_soft_object(self, record: ModelRecord, position: Dict[str, float], rotation: Dict[str, float],
                        scale: Dict[str, float] = None, volume_sampling: float = 2, surface_sampling: float = 0,
                        cluster_spacing: float = 0.2, cluster_radius: float = 0.2, cluster_stiffness: float = 0.2,
                        link_radius: float = 0.1, link_stiffness: float = 0.5, particle_spacing: float = 0.02,
                        mass_scale: float = 1, o_id: Optional[int] = None) -> List[dict]:
        """
        Add a Flex Soft Actor object and cache static data. See Command API for more Flex parameter info.

        :param record: The model record.
        :param position: The initial position of the object.
        :param rotation: The initial rotation of the object.
        :param scale: The object scale factor. If None, the scale is (1, 1, 1).
        :param volume_sampling:
        :param surface_sampling:
        :param cluster_spacing:
        :param cluster_radius:
        :param cluster_stiffness:
        :param link_radius:
        :param link_stiffness:
        :param particle_spacing:
        :param mass_scale:
        :param o_id: The object ID. If None, a random ID is created.

        :return: `[add_object, scale_object, set_flex_soft_actor, set_flex_object_mass, assign_flex_container]`
        """

        if o_id is None:
            o_id = self.get_unique_id()
        if scale is None:
            scale = {"x": 1, "y": 1, "z": 1}

        # Get the add_object command.
        add_object = self.add_transforms_object(record=record, position=position, rotation=rotation, o_id=o_id)
        # Cache the static data.
        self._soft_actors.append(_SoftActor(o_id=o_id, mass_scale=mass_scale,
                                            volume_sampling=volume_sampling, surface_sampling=surface_sampling,
                                            cluster_spacing=cluster_spacing, cluster_radius=cluster_radius,
                                            cluster_stiffness=cluster_stiffness, link_radius=link_radius,
                                            link_stiffness=link_stiffness, particle_spacing=particle_spacing))
        return [add_object,
                {"$type": "scale_object",
                 "scale_factor": scale,
                 "id": o_id},
                {"$type": "set_flex_soft_actor",
                 "id": o_id,
                 "volume_sampling": volume_sampling,
                 "surface_sampling": surface_sampling,
                 "cluster_spacing": cluster_spacing,
                 "cluster_radius": cluster_radius,
                 "cluster_stiffness": cluster_stiffness,
                 "link_radius": link_radius,
                 "link_stiffness": link_stiffness,
                 "particle_spacing": particle_spacing,
                 "mass_scale": mass_scale},
                {"$type": "assign_flex_container",
                 "container_id": 0,
                 "id": o_id}]

    def add_cloth_object(self, record: ModelRecord, position: Dict[str, float], rotation: Dict[str, float],
                         scale: Dict[str, float] = None, mesh_tesselation: int = 1, stretch_stiffness: float = 0.1,
                         bend_stiffness: float = 0.1, tether_stiffness: float = 0, tether_give: float = 0,
                         pressure: float = 0, mass_scale: float = 1, o_id: Optional[int] = None) -> List[dict]:
        """
        Add a Flex Cloth Actor object and cache static data. See Command API for more Flex parameter info.

        :param record: The model record.
        :param position: The initial position of the object.
        :param rotation: The initial rotation of the object.
        :param scale: The object scale factor. If None, the scale is (1, 1, 1).
        :param mesh_tesselation:
        :param stretch_stiffness:
        :param bend_stiffness:
        :param tether_stiffness:
        :param tether_give:
        :param pressure:
        :param mass_scale:
        :param o_id: The object ID. If None, a random ID is created.

        :return: `[add_object, scale_object, set_flex_cloth_actor, set_flex_object_mass, set_kinematic_state, assign_flex_container]`
        """

        if o_id is None:
            o_id = self.get_unique_id()
        if scale is None:
            scale = {"x": 1, "y": 1, "z": 1}

        # Get the add_object command.
        add_object = self.add_transforms_object(record=record, position=position, rotation=rotation, o_id=o_id)
        # Cache the static data.
        self._cloth_actors.append(_ClothActor(o_id=o_id, mass_scale=mass_scale,
                                              mesh_tesselation=mesh_tesselation, stretch_stiffness=stretch_stiffness,
                                              bend_stiffness=bend_stiffness, tether_stiffness=tether_stiffness,
                                              tether_give=tether_give, pressure=pressure))
        return [add_object,
                {"$type": "scale_object",
                 "scale_factor": scale,
                 "id": o_id},
                {"$type": "set_flex_cloth_actor",
                 "id": o_id,
                 "mesh_tesselation": mesh_tesselation,
                 "stretch_stiffness": stretch_stiffness,
                 "bend_stiffness": bend_stiffness,
                 "tether_stiffness": tether_stiffness,
                 "tether_give": tether_give,
                 "pressure": pressure,
                 "mass_scale": mass_scale},
                {"$type": "set_kinematic_state",
                 "id": o_id,
                 "is_kinematic": True,
                 "use_gravity": False},
                {"$type": "assign_flex_container",
                 "container_id": 0,
                 "id": o_id}]

    def _get_send_data_commands(self) -> List[dict]:
        commands = super()._get_send_data_commands()
        commands.append({"$type": "send_flex_particles",
                         "frequency": "always"})
        return commands

    @staticmethod
    def _get_destroy_object_command_name() -> str:
        return "destroy_flex_object"
