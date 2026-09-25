import math

import dask.array
import dask.dataframe as dd
import numpy as np
import xarray as xr

from lib import var_info_registry
from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field, FieldMetadata, LazyList, List
from lib.data.types import VarKey
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


def _guess_bin_edgess(data: List, keys_to_nbins: dict[VarKey, int | None]) -> list:
    keys_to_edges: dict[VarKey, np.ndarray] = {}

    compute_keys: list[VarKey] = []
    mins_to_compute = []
    maxs_to_compute = []
    nbins_so_far = 1
    keys_with_missing_nbins: list[VarKey] = []

    df = data.data

    # Calculate edges using metadata when possible

    for key, nbins in keys_to_nbins.items():
        if key in data.coordss():
            coords = data.coordss()[key]
            if nbins is None:
                nbins = len(coords)
                # note: use inf as right edge for convenience; it gets sliced out later
                keys_to_edges[key] = np.concatenate((coords, [np.inf]))
            else:
                keys_to_edges[key] = np.linspace(coords[0], coords[-1] + coords[1] - coords[0], nbins + 1, endpoint=True)
        elif key in data.metadata.var_infos and (data.metadata.var_infos[key].geometry == "polar:theta" or data.metadata.var_infos[key].geometry == "spherical:phi"):
            keys_to_edges[key] = np.linspace(-np.pi, np.pi, nbins + 1, endpoint=True)
        elif key in data.metadata.var_infos and data.metadata.var_infos[key].geometry == "spherical:theta":
            keys_to_edges[key] = np.linspace(0.0, np.pi, nbins + 1, endpoint=True)
        else:
            compute_keys.append(key)
            mins_to_compute.append(df[key].min())
            maxs_to_compute.append(df[key].max())

        if nbins:
            nbins_so_far *= nbins
        else:
            keys_with_missing_nbins.append(key)

    # If needed, batch-compute the missing edges

    if compute_keys:
        if isinstance(df, dd.DataFrame):
            computed_mins, computed_maxs = dask.array.compute(mins_to_compute, maxs_to_compute)
        else:
            computed_mins, computed_maxs = mins_to_compute, maxs_to_compute

        if keys_with_missing_nbins:
            # split bins evenly across remaining dimensions
            n_data = len(df)
            mean_n_data_per_bin_so_far = n_data / nbins_so_far
            target_mean_n_data_per_bin = 10  # arbitrary number

            guessed_nbins = math.ceil((mean_n_data_per_bin_so_far / target_mean_n_data_per_bin) ** (1 / len(compute_keys)))
            for varname_with_missing_nbins in keys_with_missing_nbins:
                keys_to_nbins[varname_with_missing_nbins] = guessed_nbins

        for key, min, max in zip(compute_keys, computed_mins, computed_maxs):
            nbins = keys_to_nbins[key]
            keys_to_edges[key] = np.linspace(min, max, nbins + 1, endpoint=True)

    # ensure edges are in same order as bin values
    edgess = [keys_to_edges[key] for key in keys_to_nbins]
    return edgess


def _step_bin_indices(step_coords: np.ndarray, step_edges: np.ndarray) -> np.ndarray:
    """Map each step's coord value onto an output bin index, or -1 if it falls outside every bin."""
    indices = np.searchsorted(step_edges, step_coords, side="right") - 1
    indices[(step_coords < step_edges[0]) | (step_coords >= step_edges[-1])] = -1
    return indices


def _histogram_per_step(data: LazyList, keys_to_nbins: dict[VarKey, int | None], bin_edgess: list) -> dask.array.Array:
    """Histogram a partition-aligned `LazyList` one step at a time.

    `dask.array.histogramdd` materializes one dense `prod(nbins)` array per dataframe
    partition and sums them. Partitions are laid out along `partition_dim` — each holds
    exactly one of its values — so including that dim in the histogram makes every
    partition allocate the whole array while only ever writing to one slice of it.
    Binning each step over the remaining dims and stacking the results shrinks the
    per-partition allocation by the length of `partition_dim`; on a long run that is the
    difference between half a MiB and a hundred MiB per partition in flight.
    """
    partition_dim = data.metadata.partition_dim
    partition_ranges = data.metadata.partition_ranges
    assert partition_dim is not None and partition_ranges is not None

    keys = list(keys_to_nbins)
    step_axis = keys.index(partition_dim)
    step_edges = bin_edgess[step_axis]
    other_keys = [key for key in keys if key != partition_dim]
    other_edgess = [edges for key, edges in zip(keys, bin_edgess) if key != partition_dim]

    weight_key = data.metadata.weight_key
    step_bins = _step_bin_indices(np.asarray(data.metadata.coordss[partition_dim]), step_edges)

    # Convert each column to a dask array once, up front: every to_dask_array() call
    # re-optimizes the whole dataframe expression, so calling it per step would cost
    # O(n_steps^2). Selecting a step's partitions afterwards is a cheap `.blocks` slice,
    # and needs no knowledge of per-partition row counts.
    columns = {key: data.data[key].to_dask_array() for key in [*other_keys, *([weight_key] if weight_key else [])]}

    hists_per_bin: list[list[dask.array.Array]] = [[] for _ in range(len(step_edges) - 1)]
    for step, (start, end) in enumerate(partition_ranges):
        bin_index = int(step_bins[step])
        if bin_index < 0 or start == end:
            continue
        hist, _ = dask.array.histogramdd(
            [columns[key].blocks[start:end] for key in other_keys],
            other_edgess,
            density=False,
            weights=columns[weight_key].blocks[start:end] if weight_key else None,
        )
        hists_per_bin[bin_index].append(hist)

    other_shape = tuple(len(edges) - 1 for edges in other_edgess)
    dtype = data.data[weight_key].dtype if weight_key else np.float64
    slices = [sum(hists[1:], hists[0]) if hists else dask.array.zeros(other_shape, dtype=dtype) for hists in hists_per_bin]
    return dask.array.stack(slices, axis=step_axis)


class Bin(MetadataAdaptor):
    def __init__(self, key_to_nbins: dict[VarKey, int | None]):
        self.keys_to_nbins = key_to_nbins

    def apply_field(self, data: Field) -> Field:
        dim_names_to_bin_size = {}
        for dim_name, nbins in self.keys_to_nbins.items():
            if not nbins:
                continue

            dim_len = len(data.coordss()[dim_name])
            bin_size = dim_len // nbins

            if bin_size < 1:
                raise ValueError(f"dim {dim_name} has length {dim_len}, which is too small for {nbins} bins")

            dim_names_to_bin_size[dim_name] = bin_size

        return data.with_active(data=data.require_active_subdata().coarsen(dim_names_to_bin_size, boundary="pad").mean())

    def apply_list(self, data: List) -> Field:
        # A dim whose coord has collapsed to a single value (e.g. by --idx t=<int>) holds
        # that value for every row, so it is a scalar coord of the result, not a bin dim.
        all_coordss = data.coordss()
        scalar_coords = {key: all_coordss[key] for key in self.keys_to_nbins if key in all_coordss and np.ndim(all_coordss[key]) == 0}
        keys_to_nbins = {key: nbins for key, nbins in self.keys_to_nbins.items() if key not in scalar_coords}

        bin_edgess = _guess_bin_edgess(data, keys_to_nbins)

        if isinstance(data, LazyList):
            if data.metadata.partition_dim in keys_to_nbins and data.metadata.partition_ranges is not None:
                binned_data = _histogram_per_step(data, keys_to_nbins, bin_edgess)
            else:
                binned_data, _ = dask.array.histogramdd(
                    [data[key].to_dask_array() for key in keys_to_nbins],
                    bin_edgess,
                    density=False,
                    weights=data[data.metadata.weight_key].to_dask_array() if data.metadata.weight_key else None,
                )
        else:
            binned_data, _ = np.histogramdd(
                [data[key] for key in keys_to_nbins],
                bin_edgess,
                density=False,
                weights=data[data.metadata.weight_key] if data.metadata.weight_key else None,
            )

        # note: the slice removes any infs
        coords = dict(zip(keys_to_nbins.keys(), (edges[:-1] for edges in bin_edgess))) | scalar_coords

        da = xr.DataArray(
            binned_data,
            coords,
            dims=keys_to_nbins.keys(),
        )

        f_info = var_info_registry.lookup("prt", "f")

        subject = data.metadata.subject
        if subject is not None and subject.latex == r"\text{Ions}":
            f_info = f_info.assign(display=f_info.display.latex + r"_\text{i}")
        elif subject is not None and subject.latex == r"\text{Electrons}":
            f_info = f_info.assign(display=f_info.display.latex + r"_\text{e}")
        new_var_infos = {key: data.metadata.var_infos[key] for key in da.coords if key in data.metadata.var_infos}
        # want: psc-plot prt.i --derive K="ux^2+uy^2+uz^2" --bin K=128 -v K --scale log

        new_var_infos["f"] = f_info
        return Field({"f": da}, FieldMetadata.create_from(data.metadata, active_key="f", var_infos=new_var_infos))

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{varname}={nbins}" if nbins else varname for varname, nbins in self.keys_to_nbins.items())
        return [f"bin_{subfrags}"]


_BIN_FORMAT = "var_key[=nbins]"


@arg_parser(
    dest="adaptors",
    flags=["--bin", "-b"],
    metavar=_BIN_FORMAT,
    help="Bin the data along each of the given variables, which become coordinates. If nbins is unspecified, it is guessed. Note that t is implicitly binned; disable by passing t= (with no nbins).",
    nargs="+",
)
def parse_bin(args: list[str]) -> Bin:
    keys_to_nbins = {}
    insert_bin_t = True

    for arg in args:
        split_arg = arg.split("=")

        if len(split_arg) == 2 and not split_arg[1]:
            # arg is "t=", i.e., disable implicit binning along t
            parse_util.parse_value(split_arg[0], "var_key", ["t"])
            insert_bin_t = False
            continue
        elif len(split_arg) > 2:
            parse_util.fail_format(arg, _BIN_FORMAT)

        [key, nbins_arg, *_] = split_arg + [""]

        parse_util.parse_identifier(key, "var_key")
        nbins = parse_util.parse_optional_number(nbins_arg, "nbins", int)

        keys_to_nbins[key] = nbins
        if key == "t":
            insert_bin_t = False

    if insert_bin_t:
        keys_to_nbins["t"] = None

    return Bin(keys_to_nbins)
