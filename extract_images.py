import h5py
from pathlib import Path
from argparse import ArgumentParser
from PIL import Image
import io


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--dest", type=str, help="Root directory for the images.")
    parser.add_argument("--src", type=str, help="Root source directory of the .hdf5 files.")

    args = parser.parse_args()

    dest = Path(args.dest)
    if not dest.exists():
        dest.mkdir(parents=True)

    p = Path(args.src)
    for trial in p.glob("*.hdf5"):
        f = h5py.File(str(trial.resolve()), "r")
        dest_dir = dest.joinpath(trial.stem)
        if not dest_dir.exists():
            dest_dir.mkdir()
        for fr in f["frames"]:
            dest_path = dest.joinpath(fr + ".jpg")
            img = Image.open(io.BytesIO(f["frames"][fr]["images"]["_img"][:]))
            img.save(str(dest_path.resolve()))
