import xarray as xr

from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser


class Div(PluginBp):
    def __init__(self, divisor: float):
        self.divisor = divisor

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da / self.divisor

    def get_name_fragment(self) -> str:
        return f"div_{self.divisor}"

    def get_modified_dep_var_name(self, title_stem: str) -> str:
        return f"({title_stem})/{{{self.divisor}}}"


@plugin_parser(
    "--div",
    metavar="divisor",
    help="divide by the given value",
)
def parse(arg: str) -> Div:
    divisor = parse_util.parse_number(arg, "exponent", float)
    return Div(divisor)
