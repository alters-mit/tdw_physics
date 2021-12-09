from typing import List, Tuple, Dict
from abc import ABC
import h5py
import numpy as np
from tdw.tdw_utils import TDWUtils
from tdw.output_data import OutputData, Transforms, Images, CameraMatrices
from tdw_physics.dataset import Dataset


class TransformsDataset(Dataset, ABC):
    """
    A dataset creator that receives and writes per frame: `Transforms`, `Images`, `CameraMatrices`.
    See README for more info.
    """

    @staticmethod
    def get_add_object(model_name: str, object_id: int, position: Dict[str, float] = None,
                       rotation: Dict[str, float] = None, library: str = "") -> dict:
        """
        Returns a valid add_object command.

        :param model_name: The name of the model.
        :param position: The position of the model. If None, defaults to `{"x": 0, "y": 0, "z": 0}`.
        :param rotation: The starting rotation of the model, in Euler angles. If None, defaults to `{"x": 0, "y": 0, "z": 0}`.
        :param library: The path to the records file. If left empty, the default library will be selected. See `ModelLibrarian.get_library_filenames()` and `ModelLibrarian.get_default_library()`.
        :param object_id: The ID of the new object.

        :return An add_object command that the controller can then send.
        """

        # Log the static data.
        Dataset.OBJECT_IDS = np.append(Dataset.OBJECT_IDS, object_id)

        return Dataset.get_add_object(model_name=model_name, object_id=object_id, position=position, rotation=rotation,
                                      library=library)

    def _get_send_data_commands(self) -> List[dict]:
        return [{"$type": "send_transforms",
                "frequency": "always"},
                {"$type": "send_camera_matrices",
                 "frequency": "always"}]

    def _write_frame(self, frames_grp: h5py.Group, resp: List[bytes], frame_num: int) -> \
            Tuple[h5py.Group, h5py.Group, dict, bool]:
        num_objects = len(Dataset.OBJECT_IDS)

        # Create a group for this frame.
        frame = frames_grp.create_group(TDWUtils.zero_padding(frame_num, 4))
        # Create a group for images.
        images = frame.create_group("images")

        # Transforms data.
        positions = np.empty(dtype=np.float32, shape=(num_objects, 3))
        forwards = np.empty(dtype=np.float32, shape=(num_objects, 3))
        rotations = np.empty(dtype=np.float32, shape=(num_objects, 4))

        camera_matrices = frame.create_group("camera_matrices")

        # Parse the data in an ordered manner so that it can be mapped back to the object IDs.
        tr_dict = dict()

        for r in resp[:-1]:
            r_id = OutputData.get_data_type_id(r)
            if r_id == "tran":
                tr = Transforms(r)
                for i in range(tr.get_num()):
                    pos = tr.get_position(i)
                    tr_dict.update({tr.get_id(i): {"pos": pos,
                                                   "for": tr.get_forward(i),
                                                   "rot": tr.get_rotation(i)}})
                # Add the Transforms data.
                for o_id, i in zip(Dataset.OBJECT_IDS, range(num_objects)):
                    if o_id not in tr_dict:
                        continue
                    positions[i] = tr_dict[o_id]["pos"]
                    forwards[i] = tr_dict[o_id]["for"]
                    rotations[i] = tr_dict[o_id]["rot"]
            elif r_id == "imag":
                im = Images(r)
                # Add each image.
                for i in range(im.get_num_passes()):
                    pass_mask = im.get_pass_mask(i)
                    # Reshape the depth pass array.
                    if pass_mask == "_depth":
                        image_data = TDWUtils.get_shaped_depth_pass(images=im, index=i)
                    else:
                        image_data = im.get_image(i)
                    images.create_dataset(pass_mask, data=image_data, compression="gzip")
            # Add the camera matrices.
            elif OutputData.get_data_type_id(r) == "cama":
                matrices = CameraMatrices(r)
                camera_matrices.create_dataset("projection_matrix", data=matrices.get_projection_matrix())
                camera_matrices.create_dataset("camera_matrix", data=matrices.get_camera_matrix())

        objs = frame.create_group("objects")
        objs.create_dataset("positions", data=positions.reshape(num_objects, 3), compression="gzip")
        objs.create_dataset("forwards", data=forwards.reshape(num_objects, 3), compression="gzip")
        objs.create_dataset("rotations", data=rotations.reshape(num_objects, 4), compression="gzip")

        return frame, objs, tr_dict, False
