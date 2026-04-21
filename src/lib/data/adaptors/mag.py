import dask.dataframe as dd
import pandas as pd
import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.parsing.args_registry import const_arg


@const_arg(
    dest="adaptors",
    flags="--mag",
    help="take the (complex) absolute value",
)
class Magnitude(BareAdaptor):
    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        return (da.real**2 + da.imag**2) ** 0.5

    def apply_list_bare(self, series: pd.Series | dd.Series) -> pd.Series | dd.Series:
        return (series.real**2 + series.imag**2) ** 0.5

    def get_name_fragments(self) -> list[str]:
        return ["mag"]

    def get_modified_display_latex(self, metadata) -> str:
        return f"|{metadata.active_var_info.display.latex}|"
