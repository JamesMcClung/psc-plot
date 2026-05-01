import pathlib
import re

import dask.dataframe as dd
import numpy as np
import xarray as xr

from lib.config import CONFIG
from lib.data.data_with_attrs import LazyList, ListMetadata
from lib.data.loader import Loader, loader
from lib.species import SpeciesInfo, build_species_display
from lib.var_info_registry import lookup

_DISCOVER_PARTICLE_BP_PREFIX_RE = re.compile(r"^prt\.([^.]+)\.\d+\.bp$")


def _get_path(prefix: str, step: int) -> pathlib.Path:
    return CONFIG.data_dir / f"{prefix}.{step:09}.bp"


def _read_attrs(path: pathlib.Path) -> dict:
    """Open a BP file, return its attrs as a plain dict."""
    with xr.open_dataset(path) as ds:
        return {k: ds.attrs[k] for k in ds.attrs}


def _load_step_df(path: pathlib.Path, time: float) -> dd.DataFrame:
    """Open one BP step lazily and return a per-step dask DataFrame with a
    constant `t` column. Drops the BP-assigned particle-dim index column.

    Note: the `t` column is added via map_partitions rather than
    dd.DataFrame.assign — the latter creates a broadcast-scalar column whose
    `to_dask_array()` trips an IndexError in dask-expr's optimizer when the
    dataframe came from xarray's to_dask_dataframe. map_partitions produces a
    proper per-row column that survives the optimizer.
    """
    with xr.open_dataset(path) as raw:
        particle_dim = next(d for d, n in raw.sizes.items() if n > 1)
    ds = xr.open_dataset(path, chunks={particle_dim: CONFIG.dask_chunk_size}).squeeze(drop=True)
    df = ds.to_dask_dataframe().drop(columns=[particle_dim])
    df = df.map_partitions(lambda p, t: p.assign(t=t), np.float64(time))
    return df


_SPECIES_KEY_RE = re.compile(r"^([a-zA-Z]+)([+-]*)(\d*)$")


@loader
class ParticleLoaderBp(Loader):
    """ADIOS2 particle loader — one instance per prt.<species_key> prefix."""

    @classmethod
    def discover_prefixes(cls, data_dir: pathlib.Path) -> list[str]:
        prefixes = set()
        for entry in data_dir.iterdir():
            if m := _DISCOVER_PARTICLE_BP_PREFIX_RE.match(entry.name):
                prefixes.add(f"prt.{m.group(1)}")
        return sorted(prefixes)

    @classmethod
    def suffix(cls):
        return "bp"

    def __init__(self, prefix: str, active_key: str | None = None):
        super().__init__(prefix, active_key)
        self.species_key = prefix.split(".", 1)[1]

    def get_data(self) -> LazyList:
        step_attrs = [_read_attrs(_get_path(self.prefix, step)) for step in self.steps]
        times = np.array([float(a["time"]) for a in step_attrs])

        head = step_attrs[0]
        q = float(head["q"])
        m = float(head["m"])

        subject = "Electrons" if q < 0 else "Ions"
        match = _SPECIES_KEY_RE.match(self.species_key)
        show_q = None
        show_m = None
        if match:
            if match.group(2):
                show_q = q
            if match.group(3):
                show_m = m
        display = build_species_display(subject, show_q, show_m)

        info = SpeciesInfo(self.species_key, display, q, m)
        species_dict = {self.species_key: info}

        dfs = [_load_step_df(_get_path(self.prefix, step), time) for step, time in zip(self.steps, times)]
        df = dd.concat(dfs)

        corners = np.asarray(head["corner"])
        lengths = np.asarray(head["length"])
        gdims = np.asarray(head["gdims"])
        coordss = {dim: np.linspace(c, c + l, n, endpoint=False) for dim, c, l, n in zip(("x", "y", "z"), corners, lengths, gdims)}
        coordss["t"] = times

        metadata = ListMetadata(
            weight_key="w",
            coordss=coordss,
            species=species_dict,
            subject=info.display,
        )
        data = LazyList(df, metadata)

        # var_info registry is keyed by "prt" (not per-species), so strip the
        # species suffix when looking up per-column metadata.
        var_infos = {key: lookup("prt", key) for key in data.dims}
        return data.assign_metadata(
            name_fragments=self._get_name_fragments(),
            active_key=self.active_key,
            var_infos=var_infos,
        )
