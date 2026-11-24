import dask
import dask.dataframe as dd
import numpy as np
import pandas as pd
import xarray as xr
from scipy.interpolate import RegularGridInterpolator

from lib.data.adaptor import WorldAdaptor
from lib.data.adaptors.with_ import SCOPE_OP
from lib.data.data_with_attrs import Field, LazyList, List
from lib.data.data_world import DataWorld
from lib.data.ensure_derived import ensure_derived
from lib.data.loader import load
from lib.data.types import DimKey, SubdataKey
from lib.file_util import Prepath
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


def _interpolate(df: pd.DataFrame, field: xr.DataArray, scalar_positions: dict[DimKey, float]) -> np.ndarray:
    """`field` lerped at each row's position, read from the row's columns or, failing that, `scalar_positions`.

    Positions outside the field's coords are clamped to them, and the field is constant along any dim of length 1."""
    field = field.squeeze(drop=True)
    if not field.dims:
        return np.full(len(df), field.item())

    grid: list[np.ndarray] = []
    positions: list[np.ndarray] = []
    for dim in field.dims:
        coords = field.coords[dim].to_numpy()
        pos = df[dim].to_numpy() if dim in df else np.full(len(df), scalar_positions[dim])
        grid.append(coords)
        positions.append(np.clip(pos, coords.min(), coords.max()))

    interpolator = RegularGridInterpolator(grid, field.to_numpy(), method="linear")
    return interpolator(np.stack(positions, axis=-1))


def _window(field: xr.DataArray, dim: DimKey, pos: float) -> xr.DataArray:
    """The (at most two) slices of `field` along `dim` that bracket `pos`."""
    coords = field.coords[dim].to_numpy()
    i = int(np.searchsorted(coords, pos))
    return field.isel({dim: slice(max(i - 1, 0), i + 1)})


def _with_column(df: pd.DataFrame, key: SubdataKey, field: xr.DataArray, scalar_positions: dict[DimKey, float]) -> pd.DataFrame:
    return df.assign(**{key: _interpolate(df, field, scalar_positions)})


class Interpolate(WorldAdaptor):
    def __init__(self, new_key: SubdataKey, prepath: Prepath, key: SubdataKey):
        self.new_key = new_key
        self.prepath = prepath
        self.key = key

    def apply_world(self, world: DataWorld) -> DataWorld:
        data = world.require_active_data()
        if not isinstance(data, List):
            raise ValueError("--interpolate adds a column to list data; the active data is a field")

        field_data = world.datas[self.prepath] if self.prepath in world.datas else load(world.config, self.prepath)
        if not isinstance(field_data, Field):
            raise ValueError(f"--interpolate reads from a field; {self.prepath} is not one")
        field_data = ensure_derived(field_data, self.key, world.config)
        world = world.with_data(self.prepath, field_data)

        field = field_data[self.key]
        scalar_positions = {dim: float(coords) for dim, coords in data.coordss().items() if np.ndim(coords) == 0}
        missing = [dim for dim in field.dims if field.sizes[dim] > 1 and dim not in data.data.columns and dim not in scalar_positions]
        if missing:
            raise ValueError(f"--interpolate needs a position for each of {self.prepath}{SCOPE_OP}{self.key}'s dims, but the list has none for {missing}")

        data = data.assign(self._interpolated_df(data, field, scalar_positions))
        data = data.with_active(key=self.new_key, info=field_data.metadata.var_infos[self.key])
        return world.with_active(data=data)

    def _interpolated_df(self, data: List, field: xr.DataArray, scalar_positions: dict[DimKey, float]) -> pd.DataFrame | dd.DataFrame:
        df = data.data
        partition_dim = data.metadata.partition_dim
        partition_ranges = data.metadata.partition_ranges
        if isinstance(data, LazyList):
            meta = df._meta.assign(**{self.new_key: np.float64(0)})

        if isinstance(data, LazyList) and partition_ranges is not None and partition_dim in field.dims:
            # Each partition only needs the field's slices around its own step, so frames still cull to their step's
            # partitions, and no task holds more of the field than two steps of it.
            df_parts = df.to_delayed()
            parts = []
            for step, (start, end) in enumerate(partition_ranges):
                window = _window(field, partition_dim, data.coordss()[partition_dim][step])
                parts.extend(dask.delayed(_with_column)(df_parts[p], self.new_key, window, scalar_positions) for p in range(start, end))
            return dd.from_delayed(parts, meta=meta, verify_meta=False)

        field = field.compute()
        if isinstance(data, LazyList):
            return df.map_partitions(_with_column, self.new_key, field, scalar_positions, meta=meta)
        return _with_column(df, self.new_key, field, scalar_positions)

    def get_name_fragments(self) -> list[str]:
        return [f"interpolate_{self.new_key}={self.prepath}{SCOPE_OP}{self.key}"]


INTERPOLATE_FORMAT = f"[new_key=]prepath{SCOPE_OP}var_key"


@arg_parser(
    dest="adaptors",
    flags="--interpolate",
    metavar=INTERPOLATE_FORMAT,
    help=f"Add a column to list data by linearly interpolating a field (e.g. `pfd_moments{SCOPE_OP}py_i`) at each row's position. The list needs a column (or, e.g. after `--idx t=<int>`, a single coord value) for each of the field's dims longer than 1. Positions beyond the field's coords take the value at the nearest edge. The column is named new_key (default: var_key) and becomes the active variable.",
    nargs="just one",
)
def parse_interpolate(arg: str) -> Interpolate:
    new_key_arg, source = parse_util.parse_optional_assignment(arg, INTERPOLATE_FORMAT)
    if source is None:
        new_key_arg, source = None, new_key_arg

    split_source = source.split(SCOPE_OP)
    if len(split_source) != 2:
        parse_util.fail_format(arg, INTERPOLATE_FORMAT)
    [prepath, key] = split_source

    if not prepath:
        parse_util.fail_format(arg, INTERPOLATE_FORMAT)
    parse_util.parse_identifier(key, "var_key")
    new_key = parse_util.parse_identifier(new_key_arg, "new_key") if new_key_arg is not None else key

    return Interpolate(new_key, prepath, key)
