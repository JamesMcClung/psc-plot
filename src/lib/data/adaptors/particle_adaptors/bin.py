import numpy as np
import pandas as pd
import xarray as xr

from ....particle_util import PRT_VARIABLES
from ...adaptor import Adaptor
from .. import parse_util
from ..registry import adaptor_parser


class Bin(Adaptor):
    def __init__(self, varname_to_nbins: dict[str, int | None]):
        self.varname_to_nbins = varname_to_nbins

    def apply(self, df: pd.DataFrame) -> xr.DataArray:
        binned_data, edges = np.histogramdd(
            np.array([df[var_name] for var_name in self.varname_to_nbins]).T,
            list(self.varname_to_nbins.values()),
            density=False,
            weights=df["w"],
        )

        coords = dict(zip(self.varname_to_nbins.keys(), ((edge[1:] + edge[:-1]) / 2.0 for edge in edges)))
        coords["t"] = df.attrs["time"]

        return xr.DataArray(
            binned_data,
            coords,
            dims=self.varname_to_nbins.keys(),
        )

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{varname}={nbins}" if nbins else varname for varname, nbins in self.varname_to_nbins)
        return [f"bin_{subfrags}"]


_BIN_FORMAT = "var_name[=nbins]"


@adaptor_parser(
    "--bin",
    "-b",
    metavar=_BIN_FORMAT,
    help="Bin the data along these variables, which serve as axes. If nbins is unspecified, it is guessed.",
    nargs="+",
)
def parse_slice(args: list[str]) -> Bin:
    varname_to_nbins = {}

    for arg in args:
        arg_with_eq = arg

        if "=" not in arg_with_eq:
            arg_with_eq += "="

        split_arg = arg_with_eq.split("=")

        if len(split_arg) != 2:
            parse_util.fail_format(arg, _BIN_FORMAT)

        [var_name, nbins_arg] = split_arg

        parse_util.check_value(var_name, "var_name", PRT_VARIABLES)
        nbins = parse_util.parse_optional_number(nbins_arg, "nbins", int)

        varname_to_nbins[var_name] = nbins

    return Bin(varname_to_nbins)
