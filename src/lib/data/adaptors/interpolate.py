import functools

import dask.dataframe as dd
import numpy as np
import pandas as pd
import xarray as xr

# PRIVATE DASK API: dask internals with no stability guarantee. `_FieldWindows` is the only code in psc-plot allowed to
# use them, so a dask upgrade has one place to break; if another adaptor needs per-partition inputs, move `_FieldWindows`
# into a shared module rather than writing a second one.
from dask._task_spec import Task, TaskRef
from dask.base import tokenize
from dask.dataframe.dask_expr._collection import new_collection
from dask.dataframe.dask_expr._expr import Expr, PartitionsFiltered
from dask.optimization import cull
from scipy.interpolate import RegularGridInterpolator

from lib.data.adaptor import WorldAdaptor
from lib.data.data_with_attrs import Field, LazyList, List
from lib.data.data_world import DataWorld
from lib.data.ensure_derived import ensure_derived
from lib.data.loader import get_or_load
from lib.data.types import DimKey, SubdataKey
from lib.file_util import Prepath
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.parsing.parse_util import SCOPE_OP


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


_SNAP_RTOL = 1e-9
"""A position this close to a coord takes that coord's slice alone. Lists and fields are usually written at the same
steps, so their partition-dim coords match, but they needn't be bitwise equal; the lerp weight this drops is negligible."""


def _bracket(coords: np.ndarray, pos: float) -> list[int]:
    """The indices of the (ascending) `coords` to lerp `pos` between: one when `pos` is on a coord or beyond either end."""
    i = int(np.searchsorted(coords, pos))
    for j in (i - 1, i):
        if 0 <= j < len(coords) and np.isclose(coords[j], pos, rtol=_SNAP_RTOL, atol=0):
            return [j]
    if i == 0:
        return [0]
    if i == len(coords):
        return [len(coords) - 1]
    return [i - 1, i]


def _with_column(df: pd.DataFrame, key: SubdataKey, field: xr.DataArray, scalar_positions: dict[DimKey, float]) -> pd.DataFrame:
    return df.assign(**{key: _interpolate(df, field, scalar_positions)})


def _with_window_column(df: pd.DataFrame, windows: pd.DataFrame, key: SubdataKey, scalar_positions: dict[DimKey, float]) -> pd.DataFrame:
    return _with_column(df, key, windows["window"].iloc[0], scalar_positions)


def _window_frame(dims: tuple[DimKey, ...], coords: dict[DimKey, np.ndarray], dim: DimKey, indices: tuple[int, ...], *blocks: np.ndarray) -> pd.DataFrame:
    """A one-row frame holding the field window that the `blocks` (one per index along `dim`) make up."""
    data = np.concatenate(blocks, axis=dims.index(dim))
    window = xr.DataArray(data, dims=dims, coords=coords | {dim: coords[dim][list(indices)]})
    return pd.DataFrame({"window": pd.Series([window], dtype=object)})


class _FieldWindows(PartitionsFiltered, Expr):
    """A dask-expr frame whose partition `i` is a one-row frame holding the `field` window that list partition `i` needs:
    its slices at `partition_indices[i]` along `dim`.

    `field` must have one chunk per index along `dim` and a single chunk along every other dim, so that an index is a
    block and a window references the field's own blocks. Being `PartitionsFiltered`, it's culled by the same
    `.partitions[...]` selection as the list it's mapped alongside, so a selected step loads only its own window.
    `tests/test_interpolate.py`'s structural tests pin that culling, and the column projection passing through.

    The public-API routes that look simpler were measured not to work: a dask `Array` argument to `map_partitions` gives
    every partition the whole array, and a `from_delayed` frame or an `assign` of a second-rooted series stops
    `.partitions[...]` from culling (the `assign` also misaligns rows)."""

    _parameters = ["field", "dim", "partition_indices", "_partitions"]
    _defaults = {"_partitions": None}

    @functools.cached_property
    def _name(self):
        return f"field-windows-{tokenize(self.field.data.name, self.dim, self.partition_indices, list(self._partitions))}"

    def __dask_tokenize__(self):
        # Expr's default tokenizes the operands, which a dask-backed DataArray can't be deterministically.
        return self._name

    @functools.cached_property
    def _meta(self):
        return pd.DataFrame({"window": pd.Series(dtype=object)})

    def _divisions(self):
        return (None,) * (len(self.partition_indices) + 1)

    def _block_key(self, index: int) -> tuple:
        axis = self.field.get_axis_num(self.dim)
        return (self.field.data.name, *(index if a == axis else 0 for a in range(self.field.ndim)))

    def _layer(self) -> dict:
        indicess = [self.partition_indices[p] for p in self._partitions]
        wanted = list({self._block_key(i) for indices in indicess for i in indices})
        layer, _ = cull(dict(self.field.data.__dask_graph__()), wanted)

        coords = {dim: self.field.coords[dim].to_numpy() for dim in self.field.dims}
        for out_i, indices in enumerate(indicess):
            key = (self._name, out_i)
            layer[key] = Task(key, _window_frame, self.field.dims, coords, self.dim, indices, *(TaskRef(self._block_key(i)) for i in indices))
        return layer


class Interpolate(WorldAdaptor):
    def __init__(self, new_key: SubdataKey, prepath: Prepath, key: SubdataKey):
        self.new_key = new_key
        self.prepath = prepath
        self.key = key

    def apply_world(self, world: DataWorld) -> DataWorld:
        data = world.require_active_data()
        if not isinstance(data, List):
            raise ValueError("--interpolate adds a column to list data; the active data is a field")

        field_data = get_or_load(world, self.prepath)
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
        if not isinstance(data, LazyList):
            return _with_column(df, self.new_key, field.compute(), scalar_positions)

        meta = df._meta.assign(**{self.new_key: np.float64(0)})
        # `required_columns` lets downstream column projection pass through to the list's loader.
        required_columns = [dim for dim in field.dims if field.sizes[dim] > 1 and dim in df.columns]
        partition_dim = data.metadata.partition_dim
        partition_ranges = data.metadata.partition_ranges
        if partition_ranges is None or partition_dim not in field.dims:
            # OPT: this computes the whole field, even along dims where the list has a single position (e.g. `t` after
            # `--idx t=<int>`, which clears the partition ranges). Slicing the field to `_bracket` of each scalar
            # position first would load at most two slices per such dim; the eager path above could do the same.
            return df.map_partitions(_with_column, self.new_key, field.compute(), scalar_positions, meta=meta, required_columns=required_columns)

        # Each partition gets only the field's slices around its own step, so a selected step culls to its own
        # partitions and field slices, and no task holds more than two slices.
        field_coords = field.coords[partition_dim].to_numpy()
        step_indices = [tuple(_bracket(field_coords, pos)) for pos in data.coordss()[partition_dim]]
        partition_indices = tuple(indices for indices, (start, end) in zip(step_indices, partition_ranges) for _ in range(start, end))
        if all(len(indices) == 1 for indices in step_indices):
            # No window spans two slices, so the partition dim is squeezed away before it's ever read.
            required_columns = [dim for dim in required_columns if dim != partition_dim]

        field = field.chunk({dim: 1 if dim == partition_dim else -1 for dim in field.dims})
        windows = new_collection(_FieldWindows(field, partition_dim, partition_indices))
        return df.map_partitions(_with_window_column, windows, self.new_key, scalar_positions, meta=meta, align_dataframes=False, required_columns=required_columns)

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

    prepath, key = parse_util.parse_scoped(source, INTERPOLATE_FORMAT)
    if not prepath:
        parse_util.fail_format(arg, INTERPOLATE_FORMAT)
    parse_util.parse_identifier(key, "var_key")
    new_key = parse_util.parse_identifier(new_key_arg, "new_key") if new_key_arg is not None else key

    return Interpolate(new_key, prepath, key)
