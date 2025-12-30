import xarray as xr

from lib.data.adaptor import BareAdaptor

from ..registry import register_const_adaptor


class Imaginary(BareAdaptor):
    def apply_bare(self, da: xr.DataArray) -> xr.DataArray:
        return da.imag

    def get_name_fragments(self) -> list[str]:
        return ["imag"]

    def get_modified_var_latex(self, var_latex: str) -> str:
        return f"\\text{{Im}}[{var_latex}]"


register_const_adaptor(
    "--imag",
    help="take the imaginary part",
    const=Imaginary(),
)
