import xarray as xr

from ...adaptor import AtomicAdaptor
from ..registry import register_const_adaptor


class Real(AtomicAdaptor):
    allowed_types = [xr.DataArray]

    def apply_atomic(self, da: xr.DataArray) -> xr.DataArray:
        return da.real

    def get_name_fragments(self) -> list[str]:
        return ["real"]

    def get_modified_var_latex(self, var_latex: str) -> str:
        return f"\\text{{Re}}[{var_latex}]"


register_const_adaptor(
    "--real",
    help="take the real part",
    const=Real(),
)
