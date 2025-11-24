import xarray as xr

from ...adaptor import AtomicAdaptor
from ..registry import register_const_adaptor


class Magnitude(AtomicAdaptor):
    def apply_atomic(self, da: xr.DataArray) -> xr.DataArray:
        return (da.real**2 + da.imag**2) ** 0.5

    def get_name_fragments(self) -> list[str]:
        return ["mag"]

    def get_modified_var_latex(self, var_latex: str) -> str:
        return f"|{var_latex}|"


register_const_adaptor(
    "--mag",
    help="take the (complex) absolute value",
    const=Magnitude(),
)
