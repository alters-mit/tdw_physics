import h5py
from pathlib import Path
from argparse import ArgumentParser
from tdw.tdw_utils import TDWUtils


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--dest", type=str, help="Root directory for the images.")
    parser.add_argument("--src", type=str, help="Root source directory of the .hdf5 files.")
    parser.add_argument("--trial", type=int, default=0, help="The number of the trial that will be extracted.")

    args = parser.parse_args()

    dest = Path(args.dest)
    if not dest.exists():
        dest.mkdir(parents=True)

    f = h5py.File(f"{str(Path(args.src).resolve())}/{TDWUtils.zero_padding(args.trial, 4)}.hdf5", "r")
    for fr in f["frames"]:
        dest.joinpath(fr + ".jpg").write_bytes(f["frames"][fr]["images"]["_img"][:])
