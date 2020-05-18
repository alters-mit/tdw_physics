from abc import ABC
from typing import List, Dict
import h5py
import random
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw_physics.physics_dataset import PhysicsDataset
from tdw_physics.trial_writers.rigidbody_writer import RigidbodyWriter
from tdw_physics.trial_writers.trial_writer import TrialWriter
from tdw_physics.physics_info import PHYSICS_INFO
from tdw_physics.util import get_move_along_direction, get_object_look_at, MODEL_LIBRARIES


class _TableProcGen(PhysicsDataset, ABC):
    _TABLES = ["quatre_dining_table",
               "restoration_hardware_salvaged_tables"]
    _CHAIRS = ["b04_chair_02",
               "brown_leather_dining_chair",
               "chair_annabelle",
               "chair_billiani_doll",
               "chair_thonet_marshall",
               "chair_willisau_riale",
               "emeco_navy_chair",
               "lapalma_stil_chair",
               "linen_dining_chair",
               "wood_chair"]
    _SPOONS = ["spoon1",
               "vk0002_teaspoon",
               "vk0054_teaspoon",
               "vk0058_tablespoon",
               "vk0060_dessertspoon",
               "vk0075_sodaspoon",
               "vk0078_fruitspoon",
               "vk0080_soupspoon"]
    _FORKS = ["fork",
              "fork1",
              "fork2",
              "vk0010_dinner_fork_subd0",
              "vk0011_dessert_fork_subd0",
              "vk0016_tea_fork_subd0",
              "vk0056_tablefork",
              "vk0056_tablefork",
              "vk0067_fishfork",
              "vk0073_teafork",
              "vk0076_fruitfork"
              ]
    _KNIVES = ["knife1",
               "vk0007_steak_knife",
               "vk0009_butter_knife_subd0",
               "vk0014_dinner_knife_subd2",
               "vk0055_tableknife",
               "vk0072_steakknife"]
    _CUPS = ["b04_cantate_crystal_wine_glass",
             "b04_wineglass",
             "b05_champagne_cup_vray",
             "coffeemug",
             "cup",
             "glass1",
             "glass2",
             "glass3"]
    _PLATES = ["plate05",
               "plate06"]
    _CENTERPIECES = ["int_kitchen_accessories_le_creuset_bowl_30cm",
                     "serving_bowl",
                     "showroomfinland_tuisku_50",
                     "b04_bowl_smooth",
                     "b03_pot",
                     "ceramic_pot",
                     "skillet_open_no_lid"]
    _FOOD = ["bread",
             "bread_01",
             "bread_02",
             "bread_03",
             "b03_loafbread",
             "b04_mesh",
             "orange"]
    _FLOOR_MATERIALS = ["ceramic_tiles_beige_tan",
                        "ceramic_tiles_brazilian",
                        "ceramic_tiles_brown_tomato",
                        "ceramic_tiles_copper",
                        "ceramic_tiles_floral_white",
                        "concrete",
                        "concrete_01",
                        "concrete_raw_panels",
                        "concrete_spotted",
                        "fieldstone_italian",
                        "parquet_alternating_orange",
                        "parquet_european_ash_grey",
                        "parquet_long_horizontal_clean",
                        "parquet_wood_ipe",
                        "parquet_wood_mahogany",
                        "parquet_wood_oak_brown",
                        "parquet_wood_olive",
                        "parquet_wood_red_cedar"]
    _WALL_MATERIALS = ["arabesque_tile_wall",
                       "basalt_brick_wall",
                       "bricks_ashmont_combined",
                       "bricks_basalt_combined",
                       "bricks_bond_variations",
                       "bricks_red_regular",
                       "ceramic_tiles_grey",
                       "church_wall_chamfered_cracks",
                       "cinderblock_wall",
                       "concrete_worn_scratched"]

    def __init__(self, port: int = 1071):
        super().__init__(port=port)

        self._table_id = 0
        self._a_pos: Dict[str, float] = {}

    def _get_scene_initialization_commands(self) -> List[dict]:
        return [self.get_add_scene(scene_name="box_room_2018"),
                {"$type": "set_aperture",
                 "aperture": 1.6},
                {"$type": "set_focus_distance",
                 "focus_distance": 2.25},
                {"$type": "set_post_exposure",
                 "post_exposure": 0.4},
                {"$type": "set_ambient_occlusion_intensity",
                 "intensity": 0.175},
                {"$type": "set_ambient_occlusion_thickness_modifier",
                 "thickness": 3.5}]

    def _get_field_of_view(self) -> float:
        return 68

    def _get_writer(self, f: h5py.File) -> TrialWriter:
        return RigidbodyWriter(f)

    def _get_trial_initialization_commands(self, writer: RigidbodyWriter) -> List[dict]:
        self._table_id = Controller.get_unique_id()

        self._a_pos = self._get_random_avatar_position(radius_min=1.7, radius_max=2.3, y_min=1.8, y_max=2.5,
                                                       center=TDWUtils.VECTOR3_ZERO)

        # Teleport the avatar.
        commands = [{"$type": "teleport_avatar_to",
                     "position": self._a_pos},
                    {"$type": "look_at",
                     "object_id": self._table_id,
                     "use_centroid": True},
                    {"$type": "focus_on_object",
                     "object_id": self._table_id,
                     "use_centroid": True}]

        # Add the table.
        table_name = self._TABLES[random.randint(0, len(self._TABLES))]
        commands.extend(writer.add_object_default(name=table_name,
                                                  position=TDWUtils.VECTOR3_ZERO,
                                                  rotation=TDWUtils.VECTOR3_ZERO,
                                                  o_id=self._table_id))
        table_record = PHYSICS_INFO[table_name].record
        top = table_record.bounds["top"]

        # Select random model names.
        chair_name = self._CHAIRS[random.randint(0, len(self._CHAIRS))]
        plate_name = self._PLATES[random.randint(0, len(self._PLATES))]
        fork_name = self._FORKS[random.randint(0, len(self._FORKS))]
        spoon_name = self._SPOONS[random.randint(0, len(self._SPOONS))]
        knife_name = self._KNIVES[random.randint(0, len(self._KNIVES))]
        cup_name = self._CUPS[random.randint(0, len(self._CUPS))]
        # Get the chair positions.
        chair_positions = [table_record.bounds["left"],
                           table_record.bounds["right"],
                           table_record.bounds["front"],
                           table_record.bounds["back"]]
        # Add 4 chairs around the table.
        for setting_pos in chair_positions:
            chair_id = Controller.get_unique_id()
            chair_pos = {"x": setting_pos["x"], "y": 0, "z": setting_pos["z"]}
            commands.extend(writer.add_object_default(position=chair_pos,
                                                      rotation=TDWUtils.VECTOR3_ZERO,
                                                      o_id=chair_id,
                                                      name=chair_name))
            # Move the chair back a bit.
            chair_pos = get_move_along_direction(pos=chair_pos,
                                                 target=TDWUtils.VECTOR3_ZERO,
                                                 d=-random.uniform(0.4, 0.55),
                                                 noise=0.01)
            commands.append({"$type": "teleport_object",
                             "id": chair_id,
                             "position": chair_pos})
            # Look at the center.
            commands.extend(get_object_look_at(o_id=chair_id,
                                               pos=TDWUtils.VECTOR3_ZERO,
                                               noise=5))

            # Set the plates on top of the table and moved in a bit.
            plate_pos = get_move_along_direction(pos={"x": setting_pos["x"], "y": top["y"], "z": setting_pos["z"]},
                                                 target={"x": 0, "y": top["y"], "z": 0},
                                                 d=random.uniform(0.1, 0.125),
                                                 noise=0.01)
            # Add a plate.
            commands.extend(writer.add_object_default(position=plate_pos,
                                                      rotation=TDWUtils.VECTOR3_ZERO,
                                                      name=plate_name))
            # Maybe add food on the plate.
            if random.random() > 0.33:
                # Use the plate bounds to add the food on top of the plate.
                plate_bounds = MODEL_LIBRARIES["models_full.json"].get_record(plate_name).bounds
                food_id = Controller.get_unique_id()
                commands.extend(writer.add_object_default(position={"x": plate_pos["x"] + random.uniform(-0.02, 0.02),
                                                                    "y": top["y"] + plate_bounds["top"]["y"] + 0.001,
                                                                    "z": plate_pos["z"] + random.uniform(-0.02, 0.02)},
                                                          rotation={"x": 0,
                                                                    "y": random.uniform(-89, 89),
                                                                    "z": 0},
                                                          name=self._FOOD[random.randint(0, len(self._FOOD))],
                                                          o_id=food_id))
                # Make the food small.
                c_s = random.uniform(0.2, 0.45)
                commands.append({"$type": "scale_object",
                                 "id": food_id,
                                 "scale_factor": {"x": c_s, "y": c_s, "z": c_s}})
            # Define the direction to move the cutlery by.
            c_rot = 0
            if setting_pos["x"] > 0:
                c_dz = 1
                c_rot = -90
            elif setting_pos["x"] < 0:
                c_dz = -1
                c_rot = 90
            else:
                c_dz = 0
            if setting_pos["z"] > 0:
                c_dx = 1
                c_rot = 180
            elif setting_pos["z"] < 0:
                c_dx = -1
                c_rot = 0
            else:
                c_dx = 0

            for cutlery, offset in zip([fork_name, knife_name, spoon_name], [-0.1, 0.1, 0.15]):
                # Maybe add cutlery at this position.
                if random.random() > 0.5:
                    c_id = Controller.get_unique_id()
                    # Add the object. Slide it offset from the plate.
                    commands.extend(writer.add_object_default(position={"x": plate_pos["x"] + offset * c_dx,
                                                              "y": top["y"],
                                                              "z": plate_pos["z"] + offset * c_dz},
                                                              rotation=TDWUtils.VECTOR3_ZERO,
                                                              name=cutlery,
                                                              o_id=c_id))
                    # Look at the center.
                    commands.append({"$type": "rotate_object_by",
                                     "angle": c_rot,
                                     "axis": "yaw",
                                     "id": c_id,
                                     "is_world": True})

            # Move the cups in.
            cup_pos = get_move_along_direction(pos={"x": plate_pos["x"] + 0.15 * c_dx,
                                                    "y": top["y"],
                                                    "z": plate_pos["z"] + 0.15 * c_dz},
                                               target={"x": 0, "y": top["y"], "z": 0},
                                               d=random.uniform(0.1, 0.125),
                                               noise=0.01)
            # Add a cup.
            commands.extend(writer.add_object_default(position=cup_pos, rotation=TDWUtils.VECTOR3_ZERO, name=cup_name))

        # Add a centerpiece.
        if random.random() > 0.25:
            centerpiece_id = Controller.get_unique_id()
            commands.extend(writer.add_object_default(position={"x": 0, "y": top["y"], "z": 0},
                                                      rotation={"x": 0,
                                                                "y": random.uniform(-89, 89),
                                                                "z": 0},
                                                      name=self._CENTERPIECES[random.randint(0,
                                                                                             len(self._CENTERPIECES))],
                                                      o_id=centerpiece_id))
            # Make the centerpiece small.
            c_s = random.uniform(0.3, 0.5)
            commands.append({"$type": "scale_object",
                             "id": centerpiece_id,
                             "scale_factor": {"x": c_s, "y": c_s, "z": c_s}})

        return commands


class TableScriptedTilt(_TableProcGen):
    """
    Tilt a table in a pre-scripted room.
    """

    def __init__(self, port: int = 1071):
        super().__init__(port=port)

        self._tip_table_frames = 0
        self._tip_table_force = 0
        self._tip_pos: Dict[str, float] = {}

    def _get_trial_initialization_commands(self, writer: RigidbodyWriter) -> List[dict]:
        commands = super()._get_trial_initialization_commands(writer)
        table_record = writer.physics_info[self._table_id].record

        tip_positions = [table_record.bounds["front"],
                         table_record.bounds["back"],
                         table_record.bounds["left"],
                         table_record.bounds["right"]]
        # Get the tip position furthest from the avatar (to ensure a good camera angle).
        t_i = 0
        max_d = 0
        for i in range(len(tip_positions)):
            d = TDWUtils.get_distance(self._a_pos, tip_positions[i])
            if d > max_d:
                max_d = d
                t_i = i

        self._tip_pos = tip_positions[t_i]
        self._tip_pos["y"] = 0
        self._tip_table_frames = random.randint(70, 90)
        # Calculate the table force from a pre-determined value using quatre_dining_table's mass.
        self._tip_table_force = random.uniform(15, 16.5) * PHYSICS_INFO[table_record.name].mass / 200

        return commands

    def _get_per_frame_commands(self, frame: int) -> List[dict]:
        commands = [{"$type": "focus_on_object",
                     "object_id": self._table_id,
                     "use_centroid": True}]
        # Tip the table up.
        if frame < self._tip_table_frames:
            commands.extend([{"$type": "apply_force_at_position",
                              "id": self._table_id,
                              "position": self._tip_pos,
                              "force": {"x": 0, "y": self._tip_table_force, "z": 0}}])
        elif frame == self._tip_table_frames:
            # Make the table kinematic to allow it to hang in the air.
            # Set the detection mode to continuous speculative in order to continue to detect collisions.
            commands.extend([{"$type": "set_object_collision_detection_mode",
                              "id": self._table_id,
                              "mode": "continuous_speculative"},
                             {"$type": "set_kinematic_state",
                              "use_gravity": False,
                              "is_kinematic": True,
                              "id": self._table_id}])
        return commands
