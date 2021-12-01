from typing import List
from pathlib import Path
from abc import ABC
from tdw.controller import Controller
from tdw.librarian import ModelLibrarian
from tdw_physics.flex_dataset import FlexDataset


class ClothDataset(FlexDataset, ABC):
    """
    A dataset that includes a Flex cloth object.
    """

    def __init__(self, port: int = 1071):
        Controller.MODEL_LIBRARIANS["models_special.json"] = ModelLibrarian("models_special.json")
        # Load the objects.
        self.object_records = ModelLibrarian(str(Path("flex.json").resolve())).records
        # Get the cloth record.
        self.cloth_record = Controller.MODEL_LIBRARIANS["models_special.json"].get_record("cloth_square")
        self.cloth_id = 0
        super().__init__(port=port)

    def get_field_of_view(self) -> float:
        return 65

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 150
