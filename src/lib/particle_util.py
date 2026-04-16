import pathlib
import typing

import dask.dataframe as dd
import h5py
import numpy as np

from lib.config import CONFIG
from lib.data.data_with_attrs import LazyList, ListMetadata

from . import field_units, file_util

type PrtVariable = typing.Literal["x", "y", "z", "px", "py", "pz", "q", "m", "w", "id", "tag"]
PRT_VARIABLES: list[PrtVariable] = list(PrtVariable.__value__.__args__)

type Species = typing.Literal["ion", "electron"]
SPECIES: list[Species] = list(Species.__value__.__args__)

PRT_PARTICLES_KEY = "particles/p0/1d"


def get_available_particle_steps(prefix: file_util.ParticlePrefix) -> list[int]:
    return file_util.get_available_steps(f"{prefix}.", ".h5")


def get_path_at_step(prefix: file_util.ParticlePrefix, step: int) -> pathlib.Path:
    return CONFIG.data_dir / f"{prefix}.{step:09}.h5"


def load_df(prefix: file_util.ParticlePrefix, steps: list[int]) -> LazyList:
    attrss = [load_attrs_at_step(prefix, step) for step in steps]
    times = np.array([attrs["time"] for attrs in attrss])

    data_paths = [get_path_at_step(prefix, step) for step in steps]
    dfs_of_steps = []
    for time, data_path in zip(times, data_paths):
        df_of_step: dd.DataFrame = dd.read_hdf(data_path, key=PRT_PARTICLES_KEY, chunksize=CONFIG.dask_chunk_size, lock=True)
        df_of_step = df_of_step.assign(t=time)
        dfs_of_steps.append(df_of_step)

    df: dd.DataFrame = dd.concat(dfs_of_steps)

    corners = np.array(attrss[0]["corner"])
    lengths = np.array(attrss[0]["length"])
    gdims = np.array(attrss[0]["gdims"])
    coordss = {dim: np.linspace(corner, corner + length, ncells, endpoint=False) for dim, corner, length, ncells in zip(("x", "y", "z"), corners, lengths, gdims)}
    coordss["t"] = times

    info = field_units.lookup_particle("f")
    metadata = ListMetadata(
        var_name="f",
        display_latex=info.display_latex,
        unit_latex=info.unit_latex,
        weight_var="w",
        coordss=coordss,
    )

    return LazyList(df, metadata)


def load_attrs_at_step(prefix: file_util.ParticlePrefix, step: int) -> dict[str, typing.Any]:
    data_path = get_path_at_step(prefix, step)
    attrs = {}
    with h5py.File(data_path) as file:
        if "time" not in file.keys():
            raise Exception("Particle data missing 'time' is no longer supported")

        attrs["time"] = file["time"][()]
        attrs["corner"] = file["corner"][:]
        attrs["length"] = file["length"][:]
        attrs["gdims"] = file["gdims"][:]

    return attrs
