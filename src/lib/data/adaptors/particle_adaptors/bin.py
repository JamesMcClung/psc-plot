import dask.array as da
import dask.dataframe as dd
import numpy as np
import xarray as xr

from ...adaptor import AtomicAdaptor
from .. import parse_util
from ..registry import adaptor_parser


def _guess_bin_edgess(df: dd.DataFrame, varname_to_nbins: dict[str, int | None]) -> list:
    mins = [df[var_name].min() for var_name in varname_to_nbins]
    maxs = [df[var_name].max() for var_name in varname_to_nbins]

    mins, maxs = da.compute(mins, maxs)

    bin_edgess = [np.linspace(min, max, nbins, endpoint=False) for min, max, nbins in zip(mins, maxs, varname_to_nbins.values())]
    return bin_edgess


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

        if len(split_arg) == 1:
            # arg is "t=", i.e., disable implicit binning along t
            parse_util.check_value(split_arg[0], "var_name", ["t"])
            insert_bin_t = False
        elif len(split_arg) != 2:
            parse_util.fail_format(arg, _BIN_FORMAT)

        [var_name, nbins_arg] = split_arg

        parse_util.check_identifier(var_name, "var_name")
        nbins = parse_util.parse_optional_number(nbins_arg, "nbins", int)

        varname_to_nbins[var_name] = nbins
        if var_name == "t":
            insert_bin_t = False

    if insert_bin_t:
        varname_to_nbins["t"] = None

    return Bin(varname_to_nbins)
