from typing import List, Dict, Tuple
from abc import ABC, abstractmethod
from pathlib import Path
from tqdm import tqdm
import h5py
import numpy as np
import random
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils


class Dataset(Controller, ABC):
    """
    Abstract class for a physics dataset.

    1. Create a dataset .hdf5 file.
    2. Send commands to initialize the scene.
    3. Run a series of trials. Per trial, do the following:
        1. Get commands to initialize the trial. Write "static" data (which doesn't change between trials).
        2. Run the trial until it is "done" (defined by output from the writer). Write per-frame data to disk,.
        3. Clean up the scene and start a new trial.
    """

    def __init__(self, port: int = 1071, launch_build: bool = True):
        super().__init__(port=port, launch_build=launch_build)

        # IDs of the objects in the current trial.
        self.object_ids = np.empty(dtype=int, shape=0)

    def run(self, num: int, output_dir: str, temp_path: str, width: int, height: int) -> None:
        """
        Create the dataset.

        :param num: The number of trials in the dataset.
        :param output_dir: The root output directory.
        :param temp_path: Temporary path to a file being written.
        :param width: Screen width in pixels.
        :param height: Screen height in pixels.
        """

        pbar = tqdm(total=num)
        output_dir = Path(output_dir)
        if not output_dir.exists():
            output_dir.mkdir(parents=True)
        temp_path = Path(temp_path)
        if not temp_path.parent.exists():
            temp_path.parent.mkdir(parents=True)
        # Remove an incomplete temp path.
        if temp_path.exists():
            temp_path.unlink()

        # Global commands for all physics datasets.
        commands = [{"$type": "set_screen_size",
                     "width": width,
                     "height": height},
                    {"$type": "set_render_quality",
                     "render_quality": 5},
                    {"$type": "set_physics_solver_iterations",
                     "iterations": 32},
                    {"$type": "set_vignette",
                     "enabled": False},
                    {"$type": "set_shadow_strength",
                     "strength": 1.0},
                    {"$type": "set_sleep_threshold",
                     "sleep_threshold": 0.1}]

        commands.extend(self.get_scene_initialization_commands())
        # Add the avatar.
        commands.extend([{"$type": "create_avatar",
                          "type": "A_Img_Caps_Kinematic",
                          "id": "a"},
                         {"$type": "set_pass_masks",
                          "pass_masks": ["_img", "_id", "_depth", "_normals", "_flow"]},
                         {"$type": "set_field_of_view",
                          "field_of_view": self.get_field_of_view()},
                         {"$type": "send_images",
                          "frequency": "always"}])

        # Skip trials that aren't on the disk, and presumably have been uploaded; jump to the highest number.
        exists_up_to = 0
        for f in output_dir.glob("*.hdf5"):
            if int(f.stem) > exists_up_to:
                exists_up_to = int(f.stem)
        pbar.update(exists_up_to)

        # Initialize the scene.
        self.communicate(commands)

        for i in range(exists_up_to, num):
            filepath = output_dir.joinpath(TDWUtils.zero_padding(i, 4) + ".hdf5")
            if not filepath.exists():
                # Do the trial.
                self.trial(filepath=filepath, temp_path=temp_path, trial_num=i)
            pbar.update(1)
        pbar.close()
        self.communicate({"$type": "terminate"})

    def trial(self, filepath: Path, temp_path: Path, trial_num: int) -> None:
        """
        Run a trial. Write static and per-frame data to disk until the trial is done.

        :param filepath: The path to this trial's hdf5 file.
        :param temp_path: The path to the temporary file.
        :param trial_num: The number of the current trial.
        """

        # Clear the object IDs.
        self.object_ids = np.empty(dtype=int, shape=0)

        # Create the .hdf5 file.
        f = h5py.File(str(temp_path.resolve()), "a")

        commands = []
        # Remove asset bundles (to prevent a memory leak).
        if trial_num % 100 == 0:
            commands.append({"$type": "unload_asset_bundles"})

        # Add commands to start the trial.
        commands.extend(self.get_trial_initialization_commands())
        # Add commands to request output data.
        commands.extend(self._get_send_data_commands())
        # Write static data to disk.
        static_group = f.create_group("static")
        self._write_static_data(static_group)

        # Send the commands and start the trial.
        resp = self.communicate(commands)
        frame = 0

        # Add the first frame.
        done = False
        frames_grp = f.create_group("frames")
        self._write_frame(frames_grp=frames_grp, resp=resp, frame_num=frame)

        # Continue the trial. Send commands, and parse output data.
        while not done:
            frame += 1
            resp = self.communicate(self.get_per_frame_commands(resp, frame))
            frame_grp, objs_grp, tr_dict, done = self._write_frame(frames_grp=frames_grp, resp=resp, frame_num=frame)
            done = done or self.is_done(resp, frame)

        # Cleanup.
        commands = []
        for o_id in self.object_ids:
            commands.append({"$type": self._get_destroy_object_command_name(o_id),
                             "id": int(o_id)})
        self.communicate(commands)
        # Close the file.
        f.close()
        # Move the file.
        temp_path.replace(filepath)

    @staticmethod
    def get_random_avatar_position(radius_min: float, radius_max: float, y_min: float, y_max: float,
                                   center: Dict[str, float], angle_min: float = 0,
                                   angle_max: float = 360) -> Dict[str, float]:
        """
        :param radius_min: The minimum distance from the center.
        :param radius_max: The maximum distance from the center.
        :param y_min: The minimum y positional coordinate.
        :param y_max: The maximum y positional coordinate.
        :param center: The centerpoint.
        :param angle_min: The minimum angle of rotation around the centerpoint.
        :param angle_max: The maximum angle of rotation around the centerpoint.

        :return: A random position for the avatar around a centerpoint.
        """

        a_r = random.uniform(radius_min, radius_max)
        a_x = center["x"] + a_r
        a_z = center["z"] + a_r
        theta = np.radians(random.uniform(angle_min, angle_max))
        a_x = np.cos(theta) * (a_x - center["x"]) - np.sin(theta) * (a_z - center["z"]) + center["x"]
        a_y = random.uniform(y_min, y_max)
        a_z = np.sin(theta) * (a_x - center["x"]) + np.cos(theta) * (a_z - center["z"]) + center["z"]

        return {"x": a_x, "y": a_y, "z": a_z}

    def is_done(self, resp: List[bytes], frame: int) -> bool:
        """
        Override this command for special logic to end the trial.

        :param resp: The output data response.
        :param frame: The frame number.

        :return: True if the trial is done.
        """

        return False

    @abstractmethod
    def get_scene_initialization_commands(self) -> List[dict]:
        """
        :return: Commands to initialize the scene ONLY for the first time (not per-trial).
        """

        raise Exception()

    @abstractmethod
    def get_trial_initialization_commands(self) -> List[dict]:
        """
        :return: Commands to initialize each trial.
        """

        raise Exception()

    @abstractmethod
    def _get_send_data_commands(self) -> List[dict]:
        """
        :return: A list of commands to request per-frame output data. Appended to the trial initialization commands.
        """

        raise Exception()

    def _write_static_data(self, static_group: h5py.Group) -> None:
        """
        Write static data to disk after assembling the trial initialization commands.

        :param static_group: The static data group.
        """

        static_group.create_dataset("object_ids", data=self.object_ids)

    @abstractmethod
    def _write_frame(self, frames_grp: h5py.Group, resp: List[bytes], frame_num: int) -> \
            Tuple[h5py.Group, h5py.Group, dict, bool]:
        """
        Write a frame to the hdf5 file.

        :param frames_grp: The frames hdf5 group.
        :param resp: The response from the build.
        :param frame_num: The frame number.

        :return: Tuple: (The frame group, the objects group, a dictionary of Transforms, True if the trial is "done")
        """

        raise Exception()

    def _get_destroy_object_command_name(self, o_id: int) -> str:
        """
        :param o_id: The object ID.

        :return: The name of the command used to destroy an object.
        """

        return "destroy_object"

    @abstractmethod
    def get_per_frame_commands(self, resp: List[bytes], frame: int) -> List[dict]:
        """
        :param resp: The output data response.
        :param frame: The frame number

        :return: Commands to send per frame.
        """

        raise Exception()

    @abstractmethod
    def get_field_of_view(self) -> float:
        """
        :return: The camera field of view.
        """

        raise Exception()

    def add_object(self, model_name: str, position={"x": 0, "y": 0, "z": 0}, rotation={"x": 0, "y": 0, "z": 0},
                   library: str = "") -> int:
        raise Exception("Don't use this function; see README for functions that supersede it.")

    def get_add_object(self, model_name: str, object_id: int, position={"x": 0, "y": 0, "z": 0},
                       rotation={"x": 0, "y": 0, "z": 0}, library: str = "") -> dict:
        raise Exception("Don't use this function; see README for functions that supersede it.")
