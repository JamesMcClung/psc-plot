import xarray as xr

from ...dimension import DIMENSIONS
from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser


class Fourier(PluginBp):
    def __init__(self, dim_name: str, force_periodic: bool = False):
        # TODO: when force_periodic is True, extend the data along dim with a mirrored copy to make it periodic
        self.dim_name = dim_name
        self.force_periodic = force_periodic

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        # TODO implement
        new_dim = DIMENSIONS[self.dim_name].to_fourier()
        da = da.rename({self.dim_name: new_dim.name})
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
