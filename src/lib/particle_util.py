import typing

import h5py
import pandas

from . import field_util, file_util

type PrtVariable = typing.Literal["x", "y", "z", "px", "py", "pz", "q", "m", "w", "id", "tag"]
PRT_VARIABLES: list[PrtVariable] = list(PrtVariable.__value__.__args__)

type Species = typing.Literal["ion", "electron"]
SPECIES: list[Species] = list(Species.__value__.__args__)


def get_available_particle_steps(prefix: file_util.ParticlePrefix) -> list[int]:
    return file_util.get_available_steps(f"{prefix}.", ".h5")


def load_df(prefix: file_util.ParticlePrefix, step: int) -> pandas.DataFrame:
    data_path = file_util.ROOT_DIR / f"{prefix}.{step:09}.h5"
    df = pandas.read_hdf(data_path, key="particles/p0/1d")  # using h5py.File not yet supported
    with h5py.File(data_path) as file:
        if "time" in file.keys():
            time = file["time"][()]
            corner = file["corner"][:]
            length = file["length"][:]
            gdims = file["gdims"][:]
        else:
            ds = field_util.load_ds("pfd", step)
            time = ds.time
            corner = ds.corner
            length = ds.length
            gdims = [len(ds.x), len(ds.y), len(ds.z)]

        df.attrs = {"time": time, "corner": corner, "length": length, "gdims": gdims}

    return df
