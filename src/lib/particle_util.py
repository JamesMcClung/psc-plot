import pathlib
import typing

import h5py
import pandas as pd

from . import field_util, file_util

type PrtVariable = typing.Literal["x", "y", "z", "px", "py", "pz", "q", "m", "w", "id", "tag"]
PRT_VARIABLES: list[PrtVariable] = list(PrtVariable.__value__.__args__)

type Species = typing.Literal["ion", "electron"]
SPECIES: list[Species] = list(Species.__value__.__args__)

PRT_PARTICLES_KEY = "particles/p0/1d"


def get_available_particle_steps(prefix: file_util.ParticlePrefix) -> list[int]:
    return file_util.get_available_steps(f"{prefix}.", ".h5")


def get_path_at_step(prefix: file_util.ParticlePrefix, step: int) -> pathlib.Path:
    return file_util.ROOT_DIR / f"{prefix}.{step:09}.h5"


def load_df(prefix: file_util.ParticlePrefix, step: int) -> pd.DataFrame:
    data_path = get_path_at_step(prefix, step)
    df = pd.read_hdf(data_path, key=PRT_PARTICLES_KEY)  # using h5py.File not yet supported
    df.attrs = load_attrs_at_step(step)
    return df


def load_attrs_at_step(prefix: file_util.ParticlePrefix, step: int) -> dict[str, typing.Any]:
    data_path = get_path_at_step(prefix, step)
    attrs = {}
    with h5py.File(data_path) as file:
        if "time" in file.keys():
            attrs["time"] = file["time"][()]
            attrs["corner"] = file["corner"][:]
            attrs["length"] = file["length"][:]
            attrs["gdims"] = file["gdims"][:]
    if not attrs:
        ds = field_util.load_ds("pfd", step)
        attrs["time"] = ds.time
        attrs["corner"] = ds.corner
        attrs["length"] = ds.length
        attrs["gdims"] = [len(ds.x), len(ds.y), len(ds.z)]

    return attrs
