from abc import abstractmethod
import numpy as np
from typing import Dict, List, Tuple
import h5py
from abc import ABC
from tdw.output_data import FlexParticles
from tdw_physics.transforms_dataset import TransformsDataset
from tdw_physics.dataset import Dataset


class _Actor(ABC):
    """
    Static data for a Flex Actor.
    """

    def __init__(self, object_id: int, mass_scale: float):
        self.object_id = object_id
        self.mass_scale = mass_scale


class _SolidActor(_Actor):
    """
    Static data for a Flex Solid Actor.
    """

    def __init__(self, object_id: int, mass_scale: float, mesh_expansion: float, particle_spacing: float):
        super().__init__(object_id, mass_scale)

        self.mesh_expansion = mesh_expansion
        self.particle_spacing = particle_spacing


class _SoftActor(_Actor):
    """
    Static data for a Flex Soft Actor.
    """

    def __init__(self, object_id: int, mass_scale: float, volume_sampling: float, surface_sampling: float,
                 cluster_spacing: float, cluster_radius: float, cluster_stiffness: float, link_radius: float,
                 link_stiffness: float, particle_spacing: float):
        super().__init__(object_id, mass_scale)
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

    def __init__(self, object_id: int, mass_scale: float, mesh_tesselation: int, stretch_stiffness: float,
                 bend_stiffness: float, tether_stiffness: float, tether_give: float, pressure: float):
        super().__init__(object_id, mass_scale)

        self.mesh_tesselation = mesh_tesselation
        self.stretch_stiffness = stretch_stiffness
        self.bend_stiffness = bend_stiffness
        self.tether_stiffness = tether_stiffness
        self.tether_give = tether_give
        self.pressure = pressure


class _FluidActor(_Actor):
    """
    Static data for a Flex Fluid Actor.
    """

    def __init__(self, object_id: int, mass_scale: float, particle_spacing: float):
        super().__init__(object_id, mass_scale)
        self.particle_spacing = particle_spacing


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
        self._fluid_actors: List[_FluidActor] = []

        # List of IDs of non-Flex objects (required for correctly destroying them).
        self.non_flex_objects: List[int] = []

    def _write_static_data(self, static_group: h5py.Group) -> None:
        super()._write_static_data(static_group)

        # Write the Flex container info.
        container_group = static_group.create_group("container")
        for key in self._flex_container_command:
            if key == "$type":
                continue
            container_group.create_dataset(key, data=[self._flex_container_command[key]])

        # Flatten the actor data and write it.
        for actors, group_name in zip([self._solid_actors, self._soft_actors, self._cloth_actors, self._fluid_actors],
                                      ["solid_actors", "soft_actors", "cloth_actors", "fluid_actors"]):
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
                for o_id in Dataset.OBJECT_IDS:
                    if o_id not in flex_dict:
                        continue
                    particles_group.create_dataset(str(o_id), data=flex_dict[o_id]["par"])
                    velocities_group.create_dataset(str(o_id), data=flex_dict[o_id]["vel"])
        return frame, objs, tr, done

    def add_solid_object(self, model_name: str, object_id: int, position: Dict[str, float] = None,
                         rotation: Dict[str, float] = None, library: str = "", scale_factor: Dict[str, float] = None,
                         mesh_expansion: float = 0, particle_spacing: float = 0.125,
                         mass_scale: float = 1) -> List[dict]:
        """
        Add a Flex Solid Actor object and cache static data. See Command API for more Flex parameter info.

        :param model_name: The name of the model.
        :param position: The position of the model. If None, defaults to `{"x": 0, "y": 0, "z": 0}`.
        :param rotation: The starting rotation of the model, in Euler angles. If None, defaults to `{"x": 0, "y": 0, "z": 0}`.
        :param library: The path to the records file. If left empty, the default library will be selected. See `ModelLibrarian.get_library_filenames()` and `ModelLibrarian.get_default_library()`.
        :param object_id: The ID of the new object.
        :param scale_factor: The scale factor.
        :param mesh_expansion:
        :param particle_spacing:
        :param mass_scale:

        :return: `[add_object, scale_object, set_flex_solid_actor, assign_flex_container]`
        """

        # Get the add_object command.
        commands = [self.get_add_object(model_name=model_name, object_id=object_id, position=position,
                                        rotation=rotation, library=library)]
        # Set the scale.
        if scale_factor is not None:
            commands.append({"$type": "scale_object",
                             "scale_factor": scale_factor,
                             "id": object_id})
        # Make the object a solid actor.
        commands.extend([{"$type": "set_flex_solid_actor",
                          "id": object_id,
                          "mesh_expansion": mesh_expansion,
                          "particle_spacing": particle_spacing,
                          "mass_scale": mass_scale},
                         {"$type": "assign_flex_container",
                          "container_id": 0,
                          "id": object_id}])
        # Cache the static data.
        self._solid_actors.append(_SolidActor(object_id=object_id, mass_scale=mass_scale, mesh_expansion=mesh_expansion,
                                              particle_spacing=particle_spacing))
        return commands

    def add_soft_object(self, model_name: str, object_id: int, position: Dict[str, float] = None,
                        rotation: Dict[str, float] = None, library: str = "", scale_factor: Dict[str, float] = None,
                        volume_sampling: float = 2, surface_sampling: float = 0, cluster_spacing: float = 0.2,
                        cluster_radius: float = 0.2, cluster_stiffness: float = 0.2, link_radius: float = 0.1,
                        link_stiffness: float = 0.5, particle_spacing: float = 0.02,
                        mass_scale: float = 1) -> List[dict]:
        """
        Add a Flex Soft Actor object and cache static data. See Command API for more Flex parameter info.

        :param model_name: The name of the model.
        :param position: The position of the model. If None, defaults to `{"x": 0, "y": 0, "z": 0}`.
        :param rotation: The starting rotation of the model, in Euler angles. If None, defaults to `{"x": 0, "y": 0, "z": 0}`.
        :param library: The path to the records file. If left empty, the default library will be selected. See `ModelLibrarian.get_library_filenames()` and `ModelLibrarian.get_default_library()`.
        :param object_id: The ID of the new object.
        :param scale_factor: The scale factor.
        :param volume_sampling:
        :param surface_sampling:
        :param cluster_spacing:
        :param cluster_radius:
        :param cluster_stiffness:
        :param link_radius:
        :param link_stiffness:
        :param particle_spacing:
        :param mass_scale:

        :return: `[add_object, scale_object, set_flex_soft_actor, assign_flex_container]`
        """

        # Get the add_object command.
        commands = [self.get_add_object(model_name=model_name, object_id=object_id, position=position,
                                        rotation=rotation, library=library)]
        # Set the scale.
        if scale_factor is not None:
            commands.append({"$type": "scale_object",
                             "scale_factor": scale_factor,
                             "id": object_id})
        # Make the object a soft actor.
        commands.extend([{"$type": "set_flex_soft_actor",
                          "id": object_id,
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
                          "id": object_id}])
        # Cache the static data.
        self._soft_actors.append(_SoftActor(object_id=object_id, mass_scale=mass_scale,
                                            volume_sampling=volume_sampling, surface_sampling=surface_sampling,
                                            cluster_spacing=cluster_spacing, cluster_radius=cluster_radius,
                                            cluster_stiffness=cluster_stiffness, link_radius=link_radius,
                                            link_stiffness=link_stiffness, particle_spacing=particle_spacing))
        return commands

    def add_cloth_object(self, model_name: str, object_id: int, position: Dict[str, float] = None,
                         rotation: Dict[str, float] = None, library: str = "", scale_factor: Dict[str, float] = None,
                         mesh_tesselation: int = 1, stretch_stiffness: float = 0.1, bend_stiffness: float = 0.1,
                         tether_stiffness: float = 0, tether_give: float = 0, pressure: float = 0,
                         mass_scale: float = 1) -> List[dict]:
        """
        Add a Flex Cloth Actor object and cache static data. See Command API for more Flex parameter info.

        :param model_name: The name of the model.
        :param position: The position of the model. If None, defaults to `{"x": 0, "y": 0, "z": 0}`.
        :param rotation: The starting rotation of the model, in Euler angles. If None, defaults to `{"x": 0, "y": 0, "z": 0}`.
        :param library: The path to the records file. If left empty, the default library will be selected. See `ModelLibrarian.get_library_filenames()` and `ModelLibrarian.get_default_library()`.
        :param object_id: The ID of the new object.
        :param scale_factor: The scale factor.
        :param mesh_tesselation:
        :param stretch_stiffness:
        :param bend_stiffness:
        :param tether_stiffness:
        :param tether_give:
        :param pressure:
        :param mass_scale:

        :return: `[add_object, scale_object, set_flex_cloth_actor, assign_flex_container]`
        """

        # Get the add_object command.
        commands = [self.get_add_object(model_name=model_name, object_id=object_id, position=position,
                                        rotation=rotation, library=library)]
        # Set the scale.
        if scale_factor is not None:
            commands.append({"$type": "scale_object",
                             "scale_factor": scale_factor,
                             "id": object_id})
        # Make the object a cloth actor.
        commands.extend([{"$type": "set_flex_cloth_actor",
                          "id": object_id,
                          "mesh_tesselation": mesh_tesselation,
                          "stretch_stiffness": stretch_stiffness,
                          "bend_stiffness": bend_stiffness,
                          "tether_stiffness": tether_stiffness,
                          "tether_give": tether_give,
                          "pressure": pressure,
                          "mass_scale": mass_scale},
                         {"$type": "assign_flex_container",
                          "container_id": 0,
                          "id": object_id}])
        # Cache the static data.
        self._cloth_actors.append(_ClothActor(object_id=object_id, mass_scale=mass_scale,
                                              mesh_tesselation=mesh_tesselation, stretch_stiffness=stretch_stiffness,
                                              bend_stiffness=bend_stiffness, tether_stiffness=tether_stiffness,
                                              tether_give=tether_give, pressure=pressure))
        return commands

    def add_fluid_object(self, object_id: int, fluid_type: str, position: Dict[str, float], rotation: Dict[str, float],
                         mass_scale: float = 1, particle_spacing: float = 0.05) -> List[dict]:
        """
        Add a Flex Fluid Actor object and cache static data. See Command API for more Flex parameter info.

        :param object_id: The ID of the new object.
        :param position: The initial position of the object.
        :param rotation: The initial rotation of the object.
        :param fluid_type: The name of the fluid type.
        :param mass_scale:
        :param particle_spacing:

        :return: `[load_flex_fluid_from_resources, set_flex_fluid_actor, assign_flex_container, step_physics]`
        """

        # Cache the static data.
        self._fluid_actors.append(_FluidActor(object_id=object_id, mass_scale=mass_scale,
                                              particle_spacing=particle_spacing))
        Dataset.OBJECT_IDS = np.append(Dataset.OBJECT_IDS, object_id)
        return [{"$type": "load_flex_fluid_from_resources",
                 "id": object_id,
                 "orientation": rotation,
                 "position": position},
                {"$type": "set_flex_fluid_actor",
                 "id": object_id,
                 "mass_scale": mass_scale,
                 "particle_spacing": particle_spacing},
                {"$type": "assign_flex_container",
                 "id": object_id,
                 "container_id": 0,
                 "fluid_container": True,
                 "fluid_type": fluid_type},
                {"$type": "step_physics",
                 "frames": 500}]

    @abstractmethod
    def get_trial_initialization_commands(self) -> List[dict]:
        self._solid_actors.clear()
        self._soft_actors.clear()
        self._fluid_actors.clear()
        self._cloth_actors.clear()
        self.non_flex_objects.clear()

        return []

    def _get_send_data_commands(self) -> List[dict]:
        commands = super()._get_send_data_commands()
        commands.append({"$type": "send_flex_particles",
                         "frequency": "always"})
        return commands

    def _get_destroy_object_command_name(self, o_id: int) -> str:
        if o_id in self.non_flex_objects:
            return "destroy_object"
        else:
            return "destroy_flex_object"
