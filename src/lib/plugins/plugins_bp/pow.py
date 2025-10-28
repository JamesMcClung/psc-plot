import xarray as xr

from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser


class Pow(PluginBp):
    def __init__(self, exponent: float):
        self.exponent = exponent

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da**self.exponent

    def get_name_fragment(self) -> str:
        return f"pow_{self.exponent}"

    def get_modified_dep_var_name(self, title_stem: str) -> str:
        return f"({title_stem})^{{{self.exponent}}}"


POW_FORMAT = "exponent"


@plugin_parser(
    "--pow",
    metavar=POW_FORMAT,
    help="raise to the given power",
)
def parse_pow(arg: str) -> Pow:
    exponent = parse_util.parse_number(arg, "exponent", float)
    return Pow(exponent)
