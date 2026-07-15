import pathlib
import re

import dask.dataframe as dd
import numpy as np
import pandas as pd
import xarray as xr

from lib import file_util
from lib.config import PscPlotConfig
from lib.data.data_with_attrs import LazyList, ListMetadata
from lib.data.loader import Loader, loader
from lib.species import SpeciesInfo, build_species_display
from lib.var_info_registry import lookup

_DISCOVER_PARTICLE_BP_PREFIX_RE = re.compile(r"^prt\.([^.]+)\.\d+\.bp$")


def _get_path(data_dir: pathlib.Path, prefix: str, step: int) -> pathlib.Path:
    return data_dir / f"{prefix}.{step:09}.bp"


def _read_attrs(path: pathlib.Path) -> dict:
    """Open a BP file, return its attrs as a plain dict."""
    with xr.open_dataset(path) as ds:
        return {k: ds.attrs[k] for k in ds.attrs}


def _peek_size(path: pathlib.Path) -> tuple[str, int]:
    """Return the file's particle-dim name and length without reading data."""
    with xr.open_dataset(path) as ds:
        return next((d, n) for d, n in ds.sizes.items() if n > 1)


def _build_meta(path: pathlib.Path) -> pd.DataFrame:
    """Build an empty pandas DataFrame whose columns/dtypes match a per-partition read."""
    with xr.open_dataset(path) as ds:
        particle_dim = next(d for d, n in ds.sizes.items() if n > 1)
        dtypes = {var: ds[var].dtype for var in ds.data_vars if var != particle_dim}
    meta = pd.DataFrame({var: pd.Series(dtype=dt) for var, dt in dtypes.items()})
    meta["t"] = pd.Series(dtype=np.float64)
    return meta


def _read_chunk(
    path: pathlib.Path,
    time: float,
    particle_dim: str,
    slice_obj: slice,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Read one chunk-slice of one BP file as a pandas DataFrame with a `t`
    column. The `columns` keyword is populated by dask-expr's column-projection
    optimizer; when supplied, only those variables are read from disk."""
    ds = xr.open_dataset(path)
    wanted_vars = [c for c in columns if c != "t" and c in ds.data_vars] if columns is not None else [v for v in ds.data_vars if v != particle_dim]
    if wanted_vars:
        sliced = ds[wanted_vars].isel({particle_dim: slice_obj}).squeeze(drop=True)
        pdf = pd.DataFrame({var: np.asarray(sliced[var].values) for var in sliced.data_vars})
    else:
        start, stop, step = slice_obj.indices(ds.sizes[particle_dim])
        n_rows = max(0, (stop - start + step - 1) // step)
        pdf = pd.DataFrame(index=pd.RangeIndex(n_rows))
    if columns is None or "t" in columns:
        pdf["t"] = np.float64(time)
    if columns is not None:
        pdf = pdf[[c for c in columns if c in pdf.columns]]
    return pdf


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

    def get_data(self, config: PscPlotConfig) -> LazyList:
        steps = file_util.get_available_steps(config.data_dir, self.prefix + ".", ".bp")
        step_attrs = [_read_attrs(_get_path(config.data_dir, self.prefix, step)) for step in steps]
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

        # Build per-partition iterables for dd.from_map, chunking each file
        # along its particle dim. dd.from_map propagates downstream column
        # projection into `_read_chunk` via its `columns` kwarg, so unused
        # variables are never read from disk.
        chunk_size = config.dask_chunk_size
        paths: list[pathlib.Path] = []
        step_times: list[float] = []
        particle_dims: list[str] = []
        slices: list[slice] = []
        partition_ranges = []
        offset = 0
        for step, time in zip(steps, times):
            path = _get_path(config.data_dir, self.prefix, step)
            particle_dim, n = _peek_size(path)
            n_chunks = max(1, (n + chunk_size - 1) // chunk_size)
            partition_ranges.append((offset, offset + n_chunks))
            offset += n_chunks
            for i in range(n_chunks):
                paths.append(path)
                step_times.append(float(time))
                particle_dims.append(particle_dim)
                slices.append(slice(i * chunk_size, (i + 1) * chunk_size))

        meta = _build_meta(paths[0])
        df = dd.from_map(_read_chunk, paths, step_times, particle_dims, slices, meta=meta)

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
            partition_dim="t",
            partition_ranges=partition_ranges,
        )
        data = LazyList(df, metadata)

        # var_info registry is keyed by "prt" (not per-species), so strip the
        # species suffix when looking up per-column metadata.
        var_infos = {key: lookup("prt", key) for key in data.dims}
        return data.assign_metadata(
            active_key=self.active_key,
            var_infos=var_infos,
        )
