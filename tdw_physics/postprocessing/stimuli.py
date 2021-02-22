import os, sys, copy
from subprocess import PIPE, STDOUT, DEVNULL
import subprocess
from typing import List, Dict, Tuple
from pathlib import Path

default_ffmpeg_args = [
    '-vcodec', 'libx264',
    '-crf', '25',
    '-pix_fmt', 'yuv420p'
]

def pngs_to_mp4(
        filename: str,
        image_stem: str,
        png_dir: Path,
        executable: str = 'ffmpeg',
        framerate: int = 30,
        size: List[int] = [256,256],
        start_frame: int = None,
        end_frame: int = None,
        ffmpeg_args: List[str] = default_ffmpeg_args,
        overwrite: bool = False,
        use_parent_dir: bool = False,
        remove_pngs: bool = False) -> None:
    """
    Convert a directory of PNGs to an MP4.
    """
    cmd = [executable]

    # framerate
    cmd += ['-r', str(framerate)]

    # format
    cmd += ['-f', 'image2']

    # size
    cmd += ['-s', str(size[0]) + 'x' + str(size[1])]

    # filenames
    cmd += ['-i', str(Path(png_dir).joinpath(image_stem + '%04d.png'))]

    # all other args
    cmd += ffmpeg_args

    # outfile
    if filename[-4:] != '.mp4':
        filename += '.mp4'
    if use_parent_dir:
        filename = Path(png_dir).parent.joinpath(filename)
    cmd += [str(filename)]

    make_video = subprocess.Popen(' '.join(cmd), shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = make_video.communicate(input=(b'y' if overwrite else b'N'))

    if remove_pngs:
        rm = subprocess.run('rm ' + str(png_dir) + '/' + image_stem + '*.png', shell=True)

    return cmd, stdout, stderr
