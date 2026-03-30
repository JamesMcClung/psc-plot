import numpy as np
import xarray as xr

from lib.data.adaptor import BareAdaptor
from lib.parsing.args_registry import const_arg


@const_arg(
    dest="adaptors",
    flags="--nan0",
    help="replace 0s with nans (useful for log)",
)
class Nan0(BareAdaptor):

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        return da.where(da != 0, np.nan)

    def get_name_fragments(self) -> list[str]:
        return [f"nan0"]
