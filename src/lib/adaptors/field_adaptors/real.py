import xarray as xr

from ..adaptor import Adaptor
from ..registry import register_const_adaptor


class Real(Adaptor):
    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.real

    def get_name_fragments(self) -> list[str]:
        return ["real"]

    def get_modified_var_name(self, title_stem: str) -> str:
        return f"\\text{{Re}}[{title_stem}]"


register_const_adaptor(
    "--real",
    help="take the real part",
    const=Real(),
)
