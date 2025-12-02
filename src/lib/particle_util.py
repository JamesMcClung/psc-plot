import pathlib
import typing

import dask.dataframe as dd
import h5py
import numpy as np
import pandas as pd

from lib.data.keys import COORDS_KEY, WEIGHT_VAR_KEY

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


def load_df_at_step(prefix: file_util.ParticlePrefix, step: int) -> pd.DataFrame:
    data_path = get_path_at_step(prefix, step)
    df = pd.read_hdf(data_path, key=PRT_PARTICLES_KEY)  # using h5py.File not yet supported
    df.attrs = load_attrs_at_step(step)
    return df


def load_df(prefix: file_util.ParticlePrefix, steps: list[int]) -> dd.DataFrame:
    data_paths = [get_path_at_step(prefix, step) for step in steps]
    df: dd.DataFrame = dd.read_hdf(data_paths, key=PRT_PARTICLES_KEY)

    attrss = [load_attrs_at_step(prefix, step) for step in steps]
    times = np.array([attrs["time"] for attrs in attrss])

    def assign_t(partition: pd.DataFrame, partition_info: dict) -> pd.DataFrame:
        # assume each step is divided into the same number of partitions
        # TODO this is probably violated if there is significant variation in the number of particles per step
        partitions_per_step = df.npartitions / len(steps)
        assert partitions_per_step == int(partitions_per_step), "varying n partitions per step; see todo"
        time = times[partition_info["number"] // int(partitions_per_step)]
        return partition.assign(t=time)

    meta = dict(zip(df.columns, df.dtypes)) | {"t": times.dtype}
    df = df.map_partitions(assign_t, meta=meta)

    corner = np.array(attrss[0]["corner"])
    length = np.array(attrss[0]["length"])
    gdims = np.array(attrss[0]["gdims"])
    coords = {dim: np.linspace(corner, corner + length, ncells, endpoint=False) for dim, corner, length, ncells in zip(("x", "y", "z"), corner, length, gdims)}
    coords["t"] = times
    df.attrs[COORDS_KEY] = coords
    df.attrs[WEIGHT_VAR_KEY] = "w"

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
