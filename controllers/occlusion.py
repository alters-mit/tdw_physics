import numpy as np
from typing import List
import random
from tdw.librarian import ModelRecord
from tdw.tdw_utils import TDWUtils
from tdw_physics.transforms_dataset import TransformsDataset
from tdw_physics.util import MODEL_LIBRARIES, get_args


class Occlusion(TransformsDataset):
    def __init__(self, port: int = 1071):
        self.small_models: List[ModelRecord] = []
        self.big_models: List[ModelRecord] = []
        for record in MODEL_LIBRARIES["models_full.json"].records:
            if record.do_not_use or record.composite_object or record.asset_bundle_sizes["Windows"] > 1000000:
                continue
            bounds = record.bounds
            s = max(bounds['top']['y'] - bounds['bottom']['y'],
                    bounds['front']['z'] - bounds['back']['z'],
                    bounds['right']['x'] - bounds['left']['x'])
            if 0.5 < s <= 1:
                self.small_models.append(record)
            if 0.75 < s <= 2.5:
                self.big_models.append(record)

        self.per_frame_commands: List[List[dict]] = []

        super().__init__(port=port)

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
                 "thickness": 4.0},
                {"$type": "simulate_physics",
                 "value": False}]

    def get_field_of_view(self) -> float:
        return 35

    def get_trial_initialization_commands(self) -> List[dict]:
        del self.per_frame_commands[:]

        commands = []

        # Add a big object in the center.
        big_id = self.get_unique_id()
        commands.append(self.add_transforms_object(record=random.choice(self.big_models),
                                                   position=TDWUtils.VECTOR3_ZERO,
                                                   rotation={"x": 0, "y": random.uniform(0, 360), "z": 0},
                                                   o_id=big_id))
        # Add a small object nearby.
        o_r = random.uniform(1, 2.)
        theta = np.radians(random.uniform(0, 360))
        commands.append(self.add_transforms_object(record=random.choice(self.small_models),
                                                   position={"x": np.cos(theta) * o_r,
                                                             "y": 0,
                                                             "z": np.sin(theta) * o_r},
                                                   rotation={"x": 0, "y": random.uniform(0, 360), "z": 0}))

        a_r = random.uniform(2.1, 3)
        d_theta = random.uniform(0.5, 3)
        a_y = random.uniform(0.4, 0.9)

        for theta in np.arange(0, 360, d_theta):
            self.per_frame_commands.append([{"$type": "teleport_avatar_to",
                                             "position": {"x": np.cos(np.radians(theta)) * a_r,
                                                          "y": a_y,
                                                          "z": np.sin(np.radians(theta)) * a_r}},
                                            {"$type": "look_at",
                                             "object_id": big_id,
                                             "use_centroid": True},
                                            {"$type": "focus_on_object",
                                             "object_id": big_id,
                                             "use_centroid": True}])

        commands.extend(self.per_frame_commands.pop(0))
        return commands

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return len(self.per_frame_commands) == 0

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return self.per_frame_commands.pop(0)


if __name__ == "__main__":
    args = get_args("occlusion")
    Occlusion().run(num=args.num, output_dir=args.dir, temp_path=args.temp, width=args.width, height=args.height)
