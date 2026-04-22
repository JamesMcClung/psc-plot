import pathlib
import typing

import dask.dataframe as dd
import h5py
import numpy as np

from lib.config import CONFIG
from lib.data.data_with_attrs import LazyList, ListMetadata
from lib.data.loader_registry import loader
from lib.data.source import DataSource
from lib.file_util import get_available_steps
from lib.latex import Latex
from lib.var_info_registry import lookup

PRT_PARTICLES_KEY = "particles/p0/1d"


def _get_path_at_step(prefix: str, step: int) -> pathlib.Path:
    return CONFIG.data_dir / f"{prefix}.{step:09}.h5"


def _load_attrs_at_step(prefix: str, step: int) -> dict[str, typing.Any]:
    data_path = _get_path_at_step(prefix, step)
    attrs = {}
    with h5py.File(data_path) as file:
        if "time" not in file.keys():
            raise Exception("Particle data missing 'time' is no longer supported")

        attrs["time"] = file["time"][()]
        attrs["corner"] = file["corner"][:]
        attrs["length"] = file["length"][:]
        attrs["gdims"] = file["gdims"][:]

    return attrs


@loader("prt")
class ParticleLoader(DataSource):
    def __init__(self, prefix: str, active_key: str | None):
        self.prefix = prefix
        self.active_key = active_key
        self.steps = get_available_steps(f"{prefix}.", ".h5")

    def get_data(self) -> LazyList:
        attrss = [_load_attrs_at_step(self.prefix, step) for step in self.steps]
        times = np.array([attrs["time"] for attrs in attrss])

        data_paths = [_get_path_at_step(self.prefix, step) for step in self.steps]
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

        metadata = ListMetadata(
            weight_key="w",
            coordss=coordss,
        )

        df_with_metadata = LazyList(df, metadata)

        var_infos = {key: lookup(self.prefix, key) for key in df_with_metadata.dims}
        return df_with_metadata.assign_metadata(
            name_fragments=self._get_name_fragments(),
            active_key=self.active_key,
            var_infos=var_infos,
            subject=Latex(r"\text{Particles}"),
        )

    def _get_name_fragments(self) -> list[str]:
        fragments = [self.prefix]
        if self.active_key is not None:
            fragments.append(self.active_key)
        return fragments
