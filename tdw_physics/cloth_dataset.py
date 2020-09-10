from typing import List
from pathlib import Path
from abc import ABC
from tdw.librarian import ModelLibrarian
from tdw_physics.flex_dataset import FlexDataset
from tdw_physics.util import MODEL_LIBRARIES


class ClothDataset(FlexDataset, ABC):
    """
    A dataset that includes a Flex cloth object.
    """

    def __init__(self, port: int = 1071, launch_build: bool = True):
        # Load the objects.
        self.object_records = ModelLibrarian(str(Path("flex.json").resolve())).records
        # Get the cloth record.
        self.cloth_record = MODEL_LIBRARIES["models_special.json"].get_record("cloth_square")
        self.cloth_id = 0

        super().__init__(port=port, launch_build=launch_build)

    def get_field_of_view(self) -> float:
        return 65

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        return frame > 150
