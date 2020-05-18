import h5py
from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np
from tdw.tdw_utils import TDWUtils
from tdw.output_data import OutputData, Transforms, Images, CameraMatrices


class TrialWriter(ABC):
    """
    Write output data from a physics trial to an hdf5 file.
    The data is divided into two components: static (never changes during the trial) and frame (per-frame dynamic data).
    """

    def __init__(self, f: h5py.File):
        """
        :param f: The trial's hdf5 file.
        """

        self.f = f

        self.object_ids = np.empty(dtype=int, shape=0)

        # hdf5 group for per-frame data.
        self._frames_grp = self.f.create_group("frames")

    @abstractmethod
    def write_static_data(self) -> h5py.Group:
        """
        Write static data to the .hdf5 file (any data that doesn't change per frame).
        This function writes object IDs. Override this function to add more static data.

        :return: The static data hd5f group.
        """

        static_group = self.f.create_group("static")
        static_group.create_dataset("object_ids", data=self.object_ids)
        return static_group

    @abstractmethod
    def get_send_data_commands(self) -> List[dict]:
        """
        :return: A list of commands: `[send_transforms, send_camera_matrices]`.
        """

        return[{"$type": "send_transforms",
                "frequency": "always"},
               {"$type": "send_camera_matrices",
                "frequency": "always"}]

    @abstractmethod
    def write_frame(self, resp: List[bytes], frame_num: int, object_ids: np.array) -> Tuple[h5py.Group, h5py.Group, dict, bool]:
        """
        Write a frame to the hdf5 file.

        :param resp: The response from the build.
        :param frame_num: The frame number.
        :param object_ids: An ordered list of object IDs.

        :return: Tuple: (The frame hdf5 group, the objects hdf5 group, an ordered dictionary of Transforms data, True if the trial is "done")
        """

        num_objects = len(object_ids)

        # Create a group for this frame.
        frame = self._frames_grp.create_group(TDWUtils.zero_padding(frame_num, 4))
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
                for o_id, i in zip(object_ids, range(num_objects)):
                    positions[i] = tr_dict[o_id]["pos"]
                    forwards[i] = tr_dict[o_id]["for"]
                    rotations[i] = tr_dict[o_id]["rot"]
            elif r_id == "imag":
                im = Images(r)
                # Add each image.
                for i in range(im.get_num_passes()):
                    images.create_dataset(im.get_pass_mask(i), data=im.get_image(i), compression="gzip")
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
