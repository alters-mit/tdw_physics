import sys, os, copy, subprocess, glob
from typing import List, Dict, Tuple
from abc import ABC, abstractmethod
from pathlib import Path
from tqdm import tqdm
import h5py, json
from collections import OrderedDict
import numpy as np
import random
from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.output_data import OutputData, SegmentationColors
from tdw_physics.postprocessing.stimuli import pngs_to_mp4
from tdw_physics.postprocessing.labels import (get_labels_from,
                                               get_all_label_funcs,
                                               get_across_trial_stats_from)
import shutil

PASSES = ["_img", "_depth", "_normals", "_flow", "_id"]

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
    def __init__(self,
                 port: int = 1071,
                 check_version: bool=False,
                 launch_build: bool=True,
                 randomize: int=0,
                 seed: int=0,
                 save_args=True
    ):
        super().__init__(port=port,
                         check_version=check_version,
                         launch_build=launch_build)

        # set random state
        self.randomize = randomize
        self.seed = seed
        if not bool(self.randomize):
            random.seed(self.seed)

        # save the command-line args
        self.save_args = save_args

    def clear_static_data(self) -> None:
        self.object_ids = np.empty(dtype=int, shape=0)
        self._initialize_object_counter()

    def get_controller_label_funcs(self):
        """
        A list of funcs with signature func(f: h5py.File) -> JSON-serializeable data
        """
        def stimulus_name(f):
            return str(np.array(f['static']['stimulus_name']))
        def controller_name(f):
            return type(self).__name__

        return [stimulus_name, controller_name]

    def save_command_line_args(self, output_dir: str) -> None:
        if not self.save_args:
            return

        # save all the args, including defaults
        self._save_all_args(output_dir)

        # save just the commandline args
        output_dir = Path(output_dir)
        filepath = output_dir.joinpath("commandline_args.txt")
        if not filepath.exists():
            with open(filepath, 'w') as f:
                f.write('\n'.join(sys.argv[1:]))

        return

    def _save_all_args(self, output_dir: str) -> None:
        writelist = []
        for k,v in self.args_dict.items():
            writelist.extend(["--"+str(k),str(v)])
        output_dir = Path(output_dir)
        filepath = output_dir.joinpath("args.txt")
        if not filepath.exists():
            with open(filepath, 'w') as f:
                f.write('\n'.join(writelist))
        return

    def get_initialization_commands(self,
                                    width: int,
                                    height: int) -> None:
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
                     "sleep_threshold": 0.05}]

        commands.extend(self.get_scene_initialization_commands())
        # Add the avatar.
        commands.extend([{"$type": "create_avatar",
                          "type": "A_Img_Caps_Kinematic",
                          "id": "a"},
                         {"$type": "set_target_framerate",
                          "framerate": 30},
                         {"$type": "set_pass_masks",
                          "pass_masks": ["_img", "_id", "_depth", "_normals", "_flow"]},
                         {"$type": "set_field_of_view",
                          "field_of_view": self.get_field_of_view()},
                         {"$type": "send_images",
                          "frequency": "always"}])
        return commands

    def run(self,
            num: int,
            output_dir: str,
            temp_path: str,
            width: int,
            height: int,
            save_passes: List[str] = [],
            save_movies: bool = False,
            save_labels: bool = False,
            args_dict: dict={}) -> None:
        """
        Create the dataset.

        :param num: The number of trials in the dataset.
        :param output_dir: The root output directory.
        :param temp_path: Temporary path to a file being written.
        :param width: Screen width in pixels.
        :param height: Screen height in pixels.
        :param save_passes: a list of which passes to save out as PNGs (or convert to MP4)
        :param save_movies: whether to save out a movie of each trial
        :param save_labels: whether to save out JSON labels for the full trial set.
        """

        self._height, self._width = height, width

        # which passes to save as an MP4
        self.save_passes = save_passes
        self.save_movies = save_movies

        # whether to save a JSON of trial-level labels
        self.save_labels = save_labels
        if self.save_labels:
            meta_file = Path(output_dir).joinpath('metadata.json')
            if meta_file.exists():
                self.trial_metadata = json.loads(meta_file.read_text())
            else:
                self.trial_metadata = []

        initialization_commands = self.get_initialization_commands(width=width, height=height)

        # Initialize the scene.
        self.communicate(initialization_commands)
        self.trial_loop(num, output_dir, temp_path)

        # Save the command line args
        if self.save_args:
            self.args_dict = copy.deepcopy(args_dict)
        self.save_command_line_args(output_dir)

        if self.save_labels:
            # Save the trial-level metadata
            json_str =json.dumps(self.trial_metadata, indent=4)
            meta_file = Path(output_dir).joinpath('metadata.json')
            meta_file.write_text(json_str, encoding='utf-8')
            print("TRIAL LABELS")
            print(json_str)

            # Save the across-trial stats
            hdf5_paths = glob.glob(str(output_dir) + '/*.hdf5')
            stats = get_across_trial_stats_from(
                hdf5_paths, funcs=self.get_controller_label_funcs())
            stats["num_trials"] = int(len(hdf5_paths))
            stats_str = json.dumps(stats, indent=4)
            stats_file = Path(output_dir).joinpath('trial_stats.json')
            stats_file.write_text(stats_str, encoding='utf-8')
            print("ACROSS TRIAL STATS")
            print(stats_str)

        # Finish
        self.communicate({"$type": "terminate"})

    def trial_loop(self,
                   num: int,
                   output_dir: str,
                   temp_path: str) -> None:

        output_dir = Path(output_dir)
        if not output_dir.exists():
            output_dir.mkdir(parents=True)
        temp_path = Path(temp_path)
        if not temp_path.parent.exists():
            temp_path.parent.mkdir(parents=True)
        # Remove an incomplete temp path.
        if temp_path.exists():
            temp_path.unlink()

        pbar = tqdm(total=num)
        # Skip trials that aren't on the disk, and presumably have been uploaded; jump to the highest number.
        exists_up_to = 0
        for f in output_dir.glob("*.hdf5"):
            if int(f.stem) > exists_up_to:
                exists_up_to = int(f.stem)

        if exists_up_to > 0:
            print('Trials up to %d already exist, skipping those' % exists_up_to)

        pbar.update(exists_up_to)
        for i in range(exists_up_to, num):
            filepath = output_dir.joinpath(TDWUtils.zero_padding(i, 4) + ".hdf5")
            self.stimulus_name = '/'.join([filepath.parent.name, str(Path(filepath.name).with_suffix(''))])

            if not filepath.exists():

                # Save out images
                if any([pa in PASSES for pa in self.save_passes]):
                    self.png_dir = output_dir.joinpath("pngs_" + TDWUtils.zero_padding(i, 4))
                    if not self.png_dir.exists():
                        self.png_dir.mkdir(parents=True)

                # Do the trial.
                self.trial(filepath=filepath,
                           temp_path=temp_path,
                           trial_num=i)

                # Save an MP4 of the stimulus
                if self.save_movies:
                    for pass_mask in self.save_passes:
                        mp4_filename = str(filepath).split('.hdf5')[0] + pass_mask
                        cmd, stdout, stderr = pngs_to_mp4(
                            filename=mp4_filename,
                            image_stem=pass_mask[1:]+'_',
                            png_dir=self.png_dir,
                            size=[self._height, self._width],
                            overwrite=True,
                            remove_pngs=True,
                            use_parent_dir=False)
                    rm = subprocess.run('rm -rf ' + str(self.png_dir), shell=True)

            pbar.update(1)
        pbar.close()

    def trial(self,
              filepath: Path,
              temp_path: Path,
              trial_num: int) -> None:
        """
        Run a trial. Write static and per-frame data to disk until the trial is done.

        :param filepath: The path to this trial's hdf5 file.
        :param temp_path: The path to the temporary file.
        :param trial_num: The number of the current trial.
        """

        # Clear the object IDs and other static data
        self.clear_static_data()
        self._trial_num = trial_num

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

        # Send the commands and start the trial.
        resp = self.communicate(commands)
        self._set_segmentation_colors(resp)
        frame = 0

        # Write static data to disk.
        static_group = f.create_group("static")
        self._write_static_data(static_group)

        # Add the first frame.
        done = False
        frames_grp = f.create_group("frames")
        frame_grp, _, _, _ = self._write_frame(frames_grp=frames_grp, resp=resp, frame_num=frame)
        self._write_frame_labels(frame_grp, resp, -1, False)

        # Continue the trial. Send commands, and parse output data.
        while not done:
            frame += 1
            # print('frame %d' % frame)
            resp = self.communicate(self.get_per_frame_commands(resp, frame))
            r_ids = [OutputData.get_data_type_id(r) for r in resp[:-1]]

            # Sometimes the build freezes and has to reopen the socket.
            # This prevents such errors from throwing off the frame numbering
            if ('imag' not in r_ids) or ('tran' not in r_ids):
                print("retrying frame %d, response only had %s" % (frame, r_ids))
                frame -= 1
                continue

            frame_grp, objs_grp, tr_dict, done = self._write_frame(frames_grp=frames_grp, resp=resp, frame_num=frame)

            # Write whether this frame completed the trial and any other trial-level data
            labels_grp, _, _, done = self._write_frame_labels(frame_grp, resp, frame, done)

        # Cleanup.
        commands = []
        for o_id in self.object_ids:
            commands.append({"$type": self._get_destroy_object_command_name(o_id),
                             "id": int(o_id)})
        self.communicate(commands)

        # Compute the trial-level metadata.
        if self.save_labels:
            meta = OrderedDict()
            meta = get_labels_from(f, label_funcs=self.get_controller_label_funcs(), res=meta)
            self.trial_metadata.append(meta)

        # Close the file.
        f.close()
        # Move the file.
        try:
            temp_path.replace(filepath)
        except OSError:
            shutil.move(temp_path, filepath)

    @staticmethod
    def get_random_avatar_position(radius_min: float,
                                   radius_max: float,
                                   y_min: float,
                                   y_max: float,
                                   center: Dict[str, float],
                                   angle_min: float = 0,
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
        a_y = random.uniform(y_min, y_max)
        a_x_new = np.cos(theta) * (a_x - center["x"]) - np.sin(theta) * (a_z - center["z"]) + center["x"]
        a_z_new = np.sin(theta) * (a_x - center["x"]) + np.cos(theta) * (a_z - center["z"]) + center["z"]
        a_x = a_x_new
        a_z = a_z_new

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
        static_group.create_dataset("stimulus_name", data=self.stimulus_name)
        static_group.create_dataset("object_ids", data=self.object_ids)
        if self.object_segmentation_colors is not None:
            static_group.create_dataset("object_segmentation_colors", data=self.object_segmentation_colors)

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

    def _write_frame_labels(self,
                            frame_grp: h5py.Group,
                            resp: List[bytes],
                            frame_num: int,
                            sleeping: bool) -> Tuple[h5py.Group, bool]:
        """
        Writes the trial-level data for this frame.

        :param frame_grp: The hdf5 group for a single frame.
        :param resp: The response from the build.
        :param frame_num: The frame number.
        :param sleeping: Whether this trial timed out due to objects falling asleep.

        :return: Tuple(h5py.Group labels, bool done): the labels data and whether this is the last frame of the trial.
        """
        labels = frame_grp.create_group("labels")
        if frame_num > 0:
            complete = self.is_done(resp, frame_num)
        else:
            complete = False

        # If the trial is over, one way or another
        done = sleeping or complete

        # Write labels indicate whether and why the trial is over
        labels.create_dataset("trial_end", data=done)
        labels.create_dataset("trial_timeout", data=(sleeping and not complete))
        labels.create_dataset("trial_complete", data=(complete and not sleeping))

        # if done:
        #     print("Trial Ended: timeout? %s, completed? %s" % \
        #           ("YES" if sleeping and not complete else "NO",\
        #            "YES" if complete and not sleeping else "NO"))

        return labels, resp, frame_num, done

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

    def _initialize_object_counter(self) -> None:
        self._object_id_counter = int(0)
        self._object_id_increment = int(1)

    def _increment_object_id(self) -> None:
        self._object_id_counter = int(self._object_id_counter + self._object_id_increment)

    def _get_next_object_id(self) -> int:
        self._increment_object_id()
        return int(self._object_id_counter)

    def _set_segmentation_colors(self, resp: List[bytes]) -> None:

        self.object_segmentation_colors = None
        for r in resp:
            if OutputData.get_data_type_id(r) == 'segm':
                seg = SegmentationColors(r)
                colors = {}
                for i in range(seg.get_num()):
                    colors[seg.get_object_id(i)] = seg.get_object_color(i)

                self.object_segmentation_colors = []
                for o_id in self.object_ids:
                    if o_id in colors.keys():
                        self.object_segmentation_colors.append(
                            np.array(colors[o_id], dtype=np.uint8).reshape(1,3))

                self.object_segmentation_colors = np.concatenate(self.object_segmentation_colors, 0)
