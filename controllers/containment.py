from typing import List
from random import choice, uniform
from tdw.tdw_utils import TDWUtils
from tdw_physics.rigidbodies_dataset import RigidbodiesDataset, PHYSICS_INFO
from tdw_physics.util import MODEL_LIBRARIES, get_args


class Containment(RigidbodiesDataset):
    """
    Create a set of "Containment" trials, where a container object holds a smaller target
    object and is shaken violently, causing the target object to move around and possibly fall out.
    """

    CONTAINERS = ["woodbowl_a02",
                  "blue_basket",
                  "bucketnew",
                  "b04_at-0002",
                  "b04_plastic_bucket",
                  "b04_bowl_smooth",
                  "woven_box",
                  "teatray",
                  "b04_wicker_tray",
                  "b06_brass_ornate_tray",
                  "ceramic_pot",
                  "b05_coal_hod",
                  "b03_bucket",
                  "int_kitchen_accessories_le_creuset_bowl_30cm",
                  "serving_bowl",
                  "bowl_wood_a_01",
                  "wooden_box",
                  "wine_box_vray",
                  "b03_object05",
                  "b03_696615_object001",
                  "b04_fruit_basket_11",
                  "b03_basket"]
    OBJECTS = ["fanta_orange_can_12_fl_oz_vray",
               "hexagonal_toy",
               "b03_sphere_chocolate",
               "coca-cola_can_001",
               "b05_baseballnew_v03_12",
               "b06_green_new",
               "star_wood_block",
               "amphora_jar_vase",
               "b03_burger",
               "golf",
               "dice",
               "apple",
               "wine_bottle",
               "jug01",
               "b03_723329_croissant",
               "moet_chandon_bottle_vray",
               "b04_banana",
               "b04_orange_00",
               "orange",
               "vm_v2_015",
               "b03_dice",
               "bread_02",
               "bread_01"]
    O_X = -1.3
    O_Z = -2.15

    def __init__(self, port: int = 1071):
        super().__init__(port=port)

        for key in PHYSICS_INFO:
            # All containers have the same physics values. Set these manually.
            if key in Containment.CONTAINERS:
                PHYSICS_INFO[key].mass = 3

        # Commands to shake the container per frame.
        self._shake_commands: List[List[dict]] = []
        self._max_num_frames: int = 0

    def get_field_of_view(self) -> float:
        return 72

    def get_scene_initialization_commands(self) -> List[dict]:
        return [self.get_add_scene(scene_name="tdw_room"),
                {"$type": "set_aperture",
                 "aperture": 3.0},
                {"$type": "set_focus_distance",
                 "focus_distance": 2.25},
                {"$type": "set_post_exposure",
                 "post_exposure": 0.4},
                {"$type": "set_ambient_occlusion_intensity",
                 "intensity": 0.25},
                {"$type": "set_ambient_occlusion_thickness_modifier",
                 "thickness": 4.0}]

    def get_trial_initialization_commands(self) -> List[dict]:
        # Teleport the avatar.
        # Look at the target aim-point.
        commands = [{"$type": "teleport_avatar_to",
                     "position": {"x": -0.625, "y": 2.0, "z": -0.7}},
                    {"$type": "look_at_position",
                     "position": {"x": -1.0, "y": 1.0, "z": -1.5}}]

        # Select a container.
        # Manually set the mass of the container.
        container_name = choice(Containment.CONTAINERS)
        container_scale = TDWUtils.get_unit_scale(PHYSICS_INFO[container_name].record) * 0.6
        container_id = self.get_unique_id()
        commands.extend(self.add_physics_object_default(name=container_name,
                                                        position={"x": Containment.O_X,
                                                                  "y": 0.25,
                                                                  "z": Containment.O_Z},
                                                        rotation=TDWUtils.VECTOR3_ZERO,
                                                        o_id=container_id))
        commands.append({"$type": "scale_object",
                         "id": container_id,
                         "scale_factor": {"x": container_scale, "y": container_scale, "z": container_scale}})

        # Add a random target object, with random size, mass, bounciness and initial orientation.
        object_name = choice(Containment.OBJECTS)
        o_id = self.get_unique_id()
        o_record = MODEL_LIBRARIES["models_full.json"].get_record(object_name)
        commands.extend(self.add_physics_object(record=o_record,
                                                position={"x": Containment.O_X,
                                                          "y": 0.6,
                                                          "z": Containment.O_Z},
                                                rotation={"x": uniform(0, 360),
                                                          "y": uniform(0, 360),
                                                          "z": uniform(0, 360)},
                                                mass=uniform(0.1, 0.5),
                                                dynamic_friction=uniform(0.1, 0.5),
                                                static_friction=uniform(0.1, 0.5),
                                                bounciness=uniform(0.5, 0.95),
                                                o_id=o_id))
        o_scale = TDWUtils.get_unit_scale(o_record) * uniform(0.2, 0.3)
        commands.append({"$type": "scale_object",
                         "id": o_id,
                         "scale_factor": {"x": o_scale, "y": o_scale, "z": o_scale}})
        # Let the objects settle.
        commands.append({"$type": "step_physics",
                         "frames": 50})

        del self._shake_commands[:]
        # Set the shake commands.
        # Shake the container.
        for i in range(25):
            forceval = uniform(-1.5, 1.5)
            rot_axis = choice(["pitch", "roll", "yaw"])
            rotval = uniform(-2, 2)
            # Shake the container.
            for i in range(3):
                self._shake_commands.append([{"$type": "apply_force_to_object",
                                              "force": {"x": forceval, "y": 0, "z": 0},
                                              "id": container_id},
                                             {"$type": "rotate_object_by",
                                              "angle": rotval,
                                              "id": container_id,
                                              "axis": rot_axis,
                                              "is_world": False}])
            # Reset the rotation.
            for i in range(10):
                self._shake_commands.append([{"$type": "rotate_object_to",
                                              "rotation": {"w": 1, "x": 0, "y": 0, "z": 0},
                                              "id": container_id}])
            # Shake some more.
            for i in range(3):
                self._shake_commands.append([{"$type": "apply_force_to_object",
                                              "force": {"x": 0, "y": 0, "z": forceval},
                                              "id": container_id},
                                             {"$type": "rotate_object_by",
                                              "angle": rotval,
                                              "id": container_id,
                                              "axis": rot_axis,
                                              "is_world": False}])
            # Reset the rotation.
            for i in range(10):
                self._shake_commands.append([{"$type": "rotate_object_to",
                                              "rotation": {"w": 1, "x": 0, "y": 0, "z": 0},
                                              "id": container_id}])
            # Shake some more.
            for i in range(4):
                self._shake_commands.append([{"$type": "apply_force_to_object",
                                              "force": {"x": 0, "y": -forceval * 2.0, "z": 0},
                                              "id": container_id},
                                             {"$type": "rotate_object_by",
                                              "angle": rotval,
                                              "id": container_id,
                                              "axis": rot_axis,
                                              "is_world": False}])
            # Reset the rotation.
            for i in range(10):
                self._shake_commands.append([{"$type": "rotate_object_to",
                                              "rotation": {"w": 1, "x": 0, "y": 0, "z": 0},
                                              "id": container_id}])
        self._max_num_frames = len(self._shake_commands) + 500

        return commands

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        # Send the next list of shake commands.
        if len(self._shake_commands) > 0:
            return self._shake_commands.pop(0)
        else:
            return []

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > self._max_num_frames


if __name__ == "__main__":
    args = get_args("containment")
    Containment().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
