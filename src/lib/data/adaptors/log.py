import dask.dataframe as dd
import numpy as np
import pandas as pd
import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.data.adaptors.math_op import float_to_latex_str
from lib.data.data_with_attrs import Metadata
from lib.latex import Latex
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class Log(BareAdaptor):
    """Takes the logarithm; keeps the unit and scale, so a later `--exp` returns to the same axis."""

    def __init__(self, base: float | None):
        self.base = base

    def _log[T: xr.DataArray | pd.Series | dd.Series](self, x: T) -> T:
        if self.base is None:
            return np.log(x)
        return np.log(x) / np.log(self.base)

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        return self._log(da)

    def apply_list_bare(self, series: pd.Series | dd.Series) -> pd.Series | dd.Series:
        return self._log(series)

    def get_name_fragments(self) -> list[str]:
        return ["log" if self.base is None else f"log{self.base}"]

    def get_modified_display_latex(self, metadata: Metadata) -> Latex:
        func = "\\ln" if self.base is None else f"\\log_{{{float_to_latex_str(self.base)}}}"
        return Latex(f"{func}({metadata.active_var_info.display})")


@arg_parser(
    dest="adaptors",
    flags="--log",
    metavar="base",
    help="take the logarithm of the active variable (natural log unless a base is given)",
    nargs="?",
)
def parse_log(arg: str | None) -> Log:
    return Log(parse_util.parse_optional_number(arg, "base", float))
