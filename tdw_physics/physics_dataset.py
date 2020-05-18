from typing import List, Dict
from abc import ABC, abstractmethod
from pathlib import Path
from tqdm import tqdm
import h5py
import numpy as np
import random
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw_physics.trial_writers.trial_writer import TrialWriter


class PhysicsDataset(Controller, ABC):
    """
    Abstract class for a physics dataset.

    1. Create a dataset .hdf5 file.
    2. Send commands to initialize the scene.
    3. Run a series of trials. Per trial, do the following:
        1. Create a `TrialWriter` object to write data to the .hdf5 file.
        2. Get commands to initialize the trial. Write "static" data (which doesn't change between trials).
        3. Run the trial until it is "done" (defined by output from the writer). Write per-frame data to disk,.
        4. Clean up the scene and start a new trial.
    """

    def run(self, num: int, output_dir: str, temp_path: str) -> None:
        """
        Create the dataset.

        :param num: The number of trials in the dataset.
        :param output_dir: The root output directory.
        :param temp_path: Temporary path to a file being written.
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
                     "width": 256,
                     "height": 256},
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

        commands.extend(self._get_scene_initialization_commands())
        # Add the avatar.
        commands.extend([{"$type": "create_avatar",
                          "type": "A_Img_Caps_Kinematic",
                          "id": "a"},
                         {"$type": "set_pass_masks",
                          "pass_masks": ["_img", "_id", "_depth", "_normals"]},
                         {"$type": "set_field_of_view",
                          "field_of_view": self._get_field_of_view()},
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

        for i in range(exists_up_to + 1, num):
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

        # Create the data writer.
        writer = self._get_writer(h5py.File(str(temp_path.resolve()), "a"))

        commands = []
        # Remove asset bundles (to prevent a memory leak).
        if trial_num % 100 == 0:
            commands.append({"$type": "unload_asset_bundles"})

        # Add commands to start the trial.
        commands.extend(self._get_trial_initialization_commands(writer))
        # Add commands to request output data.
        commands.extend(writer.get_send_data_commands())

        # Send the commands and start the trial.
        resp = self.communicate(commands)
        frame = 0

        # Add the first frame.
        done = False
        writer.write_frame(resp=resp, frame_num=frame)

        # Continue the trial. Send commands, and parse output data.
        while not done and frame < 1000:
            frame += 1
            resp = self.communicate(self._get_per_frame_commands(frame))
            frame_grp, objs_grp, tr_dict, done = writer.write_frame(resp=resp, frame_num=frame)

        # Cleanup.
        self.communicate(writer.get_destroy_commands())
        # Close the file.
        writer.f.close()
        # Move the file.
        temp_path.replace(filepath)

    @abstractmethod
    def _get_writer(self, f: h5py.File) -> TrialWriter:
        """
        :param f: The trial's .hdf5 file.

        :return: A TrialWriter object for the current trial.
        """

        raise Exception()

    @staticmethod
    def _get_random_avatar_position(radius_min: float, radius_max: float, y_min: float, y_max: float,
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
        a_z = np.sin(theta) * (a_x - center["x"])

        return {"x": a_x, "y": a_y, "z": a_z}

    @abstractmethod
    def _get_scene_initialization_commands(self) -> List[dict]:
        """
        :return: Commands to initialize the scene ONLY for the first time (not per-trial).
        """

        raise Exception()

    @abstractmethod
    def _get_trial_initialization_commands(self, writer: TrialWriter) -> List[dict]:
        """
        :param writer: The data writer.

        :return: Commands to initialize each trial.
        """

        raise Exception()

    @abstractmethod
    def _get_per_frame_commands(self, frame: int) -> List[dict]:
        """
        :param frame: The current frame number.

        :return: Commands to send per frame.
        """

        raise Exception()

    @abstractmethod
    def _get_field_of_view(self) -> float:
        """
        :return: The camera field of view.
        """

        raise Exception()
