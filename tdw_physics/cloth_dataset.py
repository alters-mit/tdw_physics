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

    def get_field_of_view(self) -> float:
        return 65

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 150

    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        return [{"$type": "focus_on_object",
                 "object_id": self.cloth_id}]
