import dask.dataframe as dd
import pandas as pd
import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.parsing.args_registry import const_arg


@const_arg(
    dest="adaptors",
    flags="--image",
    help="take the imaginary part",
)
class Imaginary(BareAdaptor):
    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        return da.imag

    def apply_list_bare(self, series: pd.Series | dd.Series) -> pd.Series | dd.Series:
        return series.imag

    def get_name_fragments(self) -> list[str]:
        return ["imag"]

    def get_modified_display_latex(self, metadata) -> str:
        return f"\\text{{Im}}[{metadata.active_var_info.name.latex}]"
