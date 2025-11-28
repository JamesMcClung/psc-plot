import math

import dask.array as da
import dask.dataframe as dd
import numpy as np
import xarray as xr

from ...adaptor import AtomicAdaptor
from .. import parse_util
from ..registry import adaptor_parser


def _guess_bin_edgess(df: dd.DataFrame, varname_to_nbins: dict[str, int | None]) -> list:
    varname_to_edges: dict[str, np.array] = {}

    compute_varnames = []
    mins_to_compute = []
    maxs_to_compute = []
    nbins_so_far = 1
    varnames_with_missing_nbins = []

    # Calculate edges using metadata when possible

    for varname, nbins in varname_to_nbins.items():
        if varname == "t":
            times = df.attrs["times"]
            nt = len(times)
            nbins = nbins or nt
            if nbins != nt:
                print("todo: proper warning for t nbins")  # TODO
            dt = times[1] - times[0] if nt >= 2 else 1
            # cheat, kinda: to avoid floating-point comparison errors, center the bins on the times
            varname_to_edges[varname] = np.linspace(times[0] - dt * 0.5, times[-1] + dt * 0.5, nbins + 1, endpoint=True)

        elif varname in ["x", "y", "z"]:
            dim_idx = ["x", "y", "z"].index(varname)
            ncells = df.attrs["gdims"][dim_idx]
            nbins = nbins or ncells
            if nbins != ncells:
                print(f"todo: proper warning for {varname} nbins")  # TODO
            mins = df.attrs["corner"]
            maxs = mins + df.attrs["length"]
            varname_to_edges[varname] = np.linspace(mins[dim_idx], maxs[dim_idx], nbins + 1, endpoint=True)

        else:
            compute_varnames.append(varname)
            mins_to_compute.append(df[varname].min())
            maxs_to_compute.append(df[varname].max())

        if nbins:
            nbins_so_far *= nbins
        else:
            varnames_with_missing_nbins.append(varname)

    # If needed, batch-compute the missing edges

    if compute_varnames:
        computed_mins, computed_maxs = da.compute(mins_to_compute, maxs_to_compute)

        if varnames_with_missing_nbins:
            # split bins evenly across remaining dimensions
            n_data = len(df)
            mean_n_data_per_bin_so_far = n_data / nbins_so_far
            target_mean_n_data_per_bin = 10  # arbitrary number

            guessed_nbins = math.ceil((mean_n_data_per_bin_so_far / target_mean_n_data_per_bin) ** (1 / len(compute_varnames)))
            for varname_with_missing_nbins in varnames_with_missing_nbins:
                varname_to_nbins[varname_with_missing_nbins] = guessed_nbins

        for varname, min, max in zip(compute_varnames, computed_mins, computed_maxs):
            nbins = varname_to_nbins[varname]
            varname_to_edges[varname] = np.linspace(min, max, nbins + 1, endpoint=True)

    # ensure edges are in same order as bin values
    edgess = [varname_to_edges[varname] for varname in varname_to_nbins]
    return edgess


class Bin(AtomicAdaptor):
    def __init__(self, varname_to_nbins: dict[str, int | None]):
        self.varname_to_nbins = varname_to_nbins

    def apply_atomic(self, df: dd.DataFrame) -> xr.DataArray:
        bin_edgess = _guess_bin_edgess(df, self.varname_to_nbins)

        binned_data, _ = da.histogramdd(
            [df[var_name].to_dask_array() for var_name in self.varname_to_nbins],
            bin_edgess,
            density=False,
            weights=df["w"].to_dask_array(),
        )

        coords = dict(zip(self.varname_to_nbins.keys(), (edges[:-1] for edges in bin_edgess)))

        if "t" in coords:
            # fulfillment of the "cheating": want actual t values, but time bins are centered on those values to avoid floating point comparison errors
            coords["t"] = df.attrs["times"]

        return xr.DataArray(
            binned_data.compute(),
            coords,
            dims=self.varname_to_nbins.keys(),
        )

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{varname}={nbins}" if nbins else varname for varname, nbins in self.varname_to_nbins.items())
        return [f"bin_{subfrags}"]


_BIN_FORMAT = "var_name[=nbins]"


@adaptor_parser(
    "--bin",
    "-b",
    metavar=_BIN_FORMAT,
    help="Bin the data along these variables, which serve as axes. If nbins is unspecified, it is guessed. Note that t is implicitly binned; disable by passing t= (with no nbins).",
    nargs="+",
)
def parse_slice(args: list[str]) -> Bin:
    varname_to_nbins = {}
    insert_bin_t = True

    for arg in args:
        split_arg = arg.split("=")

        if len(split_arg) == 2 and not split_arg[1]:
            # arg is "t=", i.e., disable implicit binning along t
            parse_util.check_value(split_arg[0], "var_name", ["t"])
            insert_bin_t = False
        elif len(split_arg) > 2:
            parse_util.fail_format(arg, _BIN_FORMAT)

        [var_name, nbins_arg, *_] = split_arg + [""]

        parse_util.check_identifier(var_name, "var_name")
        nbins = parse_util.parse_optional_number(nbins_arg, "nbins", int)

        varname_to_nbins[var_name] = nbins
        if var_name == "t":
            insert_bin_t = False

    if insert_bin_t:
        varname_to_nbins["t"] = None

    return Bin(varname_to_nbins)
