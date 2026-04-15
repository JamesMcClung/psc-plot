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

    def get_name_fragments(self) -> list[str]:
        return ["imag"]

    def get_modified_display_latex(self, display_latex: str, metadata) -> str:
        return f"\\text{{Im}}[{display_latex}]"
