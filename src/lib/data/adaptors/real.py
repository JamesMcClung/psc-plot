import dask.dataframe as dd
import pandas as pd
import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.parsing.args_registry import const_arg


@const_arg(
    dest="adaptors",
    flags="--real",
    help="take the real part",
)
class Real(BareAdaptor):

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        return da.real

    def apply_list_bare(self, series: pd.Series | dd.Series) -> pd.Series | dd.Series:
        return series.real

    def get_name_fragments(self) -> list[str]:
        return ["real"]

    def get_modified_display_latex(self, metadata) -> str:
        return f"\\text{{Re}}[{metadata.active_var_info.name.latex}]"
