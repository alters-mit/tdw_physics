from typing import List
from pathlib import Path
from abc import ABC
from tdw.librarian import ModelLibrarian
from tdw_physics.flex_dataset import FlexDataset
from tdw_physics.util import MODEL_LIBRARIES


class ClothDataset(FlexDataset, ABC):
    """
    Using NVIDIA Flex, drape a randomly-selected object with a cloth object.
    20% of the time, no object is selected.
    """

    def __init__(self, port: int = 1071):
        # Load the objects.
        self.object_records = ModelLibrarian(str(Path("flex.json").resolve())).records
        # Get the cloth record.
        self.cloth_record = MODEL_LIBRARIES["models_special.json"].get_record("cloth_square")
        self.cloth_id = 0

        super().__init__(port=port)

    def get_scene_initialization_commands(self) -> List[dict]:
        return [self.get_add_scene(scene_name="tdw_room_2018"),
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
                {"$type": "create_flex_container",
                 "collision_distance": 0.001,
                 "static_friction": 1.0,
                 "dynamic_friction": 1.0,
                 "iteration_count": 12,
                 "substep_count": 12,
                 "radius": 0.1875,
                 "damping": 0,
                 "drag": 0}]

    def get_field_of_view(self) -> float:
        return 65

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 150

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return [{"$type": "focus_on_object",
                 "object_id": self.cloth_id}]
