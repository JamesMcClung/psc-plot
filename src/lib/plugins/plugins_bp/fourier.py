import xarray as xr
import xrft

from ...dimension import DIMENSIONS, FOURIER_NAME_PREFIX
from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser


class Fourier(PluginBp):
    def __init__(self, dim_name: str):
        self.dim_name = dim_name

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        da = xrft.fft(da, dim=self.dim_name, true_phase=False, prefix=FOURIER_NAME_PREFIX)
        return da

    def get_name_fragment(self) -> str:
        return f"fourier_{self.dim_name}"


FOURIER_FORMAT = "dim_name"


@plugin_parser(
    "--fourier",
    "-f",
    metavar=FOURIER_FORMAT,
    help="perform a Fourier transform along the given dimension",
)
def parse_fourier(arg: str) -> Fourier:
    dim_name = arg

    parse_util.check_value(dim_name, "dim_name", DIMENSIONS)

    return Fourier(dim_name)
