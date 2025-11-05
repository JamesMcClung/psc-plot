import xarray as xr

from ..adaptor_base import FieldAdaptor
from ..registry import register_const_adaptor


class Real(FieldAdaptor):
    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.real

    def get_name_fragment(self) -> str:
        return f"real"

    def get_modified_dep_var_name(self, title_stem: str) -> str:
        return f"\\text{{Re}}[{title_stem}]"


register_const_adaptor(
    "--real",
    help="take the real part",
    const=Real(),
)
