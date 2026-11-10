import dask.dataframe as dd
import numpy as np
import pandas as pd
import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.data.data_with_attrs import Metadata
from lib.latex import Latex
from lib.parsing.args_registry import const_arg


@const_arg(
    dest="adaptors",
    flags="--exp",
    help="exponentiate the active variable",
)
class Exp(BareAdaptor):
    """Exponentiates; keeps the unit and scale, undoing a `--log`."""

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        return np.exp(da)

    def apply_list_bare(self, series: pd.Series | dd.Series) -> pd.Series | dd.Series:
        return np.exp(series)

    def get_name_fragments(self) -> list[str]:
        return ["exp"]

    def get_modified_display_latex(self, metadata: Metadata) -> Latex:
        return Latex(f"\\exp({metadata.active_var_info.display})")
