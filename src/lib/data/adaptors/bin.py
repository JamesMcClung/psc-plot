import math

import dask.array
import dask.dataframe as dd
import numpy as np
import xarray as xr

from lib import var_info_registry
from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field, FieldMetadata, List
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
        bin_edgess = _guess_bin_edgess(data, self.keys_to_nbins)

        df = data.data
        if isinstance(df, dd.DataFrame):
            binned_data, _ = dask.array.histogramdd(
                [df[active_key].to_dask_array() for active_key in self.keys_to_nbins],
                bin_edgess,
                density=False,
                weights=df[data.metadata.weight_key].to_dask_array() if data.metadata.weight_key else None,
            )
        else:
            binned_data, _ = np.histogramdd(
                [df[active_key] for active_key in self.keys_to_nbins],
                bin_edgess,
                density=False,
                weights=df[data.metadata.weight_key] if data.metadata.weight_key else None,
            )

        # note: the slice removes any infs
        coords = dict(zip(self.keys_to_nbins.keys(), (edges[:-1] for edges in bin_edgess)))

        da = xr.DataArray(
            binned_data,
            coords,
            dims=self.keys_to_nbins.keys(),
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
