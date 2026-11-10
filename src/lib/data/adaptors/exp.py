import dask.dataframe as dd
import numpy as np
import pandas as pd
import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.data.data_with_attrs import Metadata
from lib.latex import Latex, float_to_latex_str
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class Exp(BareAdaptor):
    """Exponentiates; keeps the unit and scale, undoing a `--log` of the same base."""

    def __init__(self, base: float | None):
        self.base = base

    def _exp[T: xr.DataArray | pd.Series | dd.Series](self, x: T) -> T:
        if self.base is None:
            return np.exp(x)
        return self.base**x

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        return self._exp(da)

    def apply_list_bare(self, series: pd.Series | dd.Series) -> pd.Series | dd.Series:
        return self._exp(series)

    def get_name_fragments(self) -> list[str]:
        return ["exp" if self.base is None else f"exp{self.base}"]

    def get_modified_display_latex(self, metadata: Metadata) -> Latex:
        if self.base is None:
            return Latex(f"\\exp({metadata.active_var_info.display})")
        return Latex(f"{float_to_latex_str(self.base)}^{{{metadata.active_var_info.display}}}")


@arg_parser(
    dest="adaptors",
    flags="--exp",
    metavar="base",
    help="exponentiate the active variable (base e unless a base is given)",
    nargs="?",
)
def parse_exp(arg: str | None) -> Exp:
    return Exp(parse_util.parse_optional_number(arg, "base", float))
