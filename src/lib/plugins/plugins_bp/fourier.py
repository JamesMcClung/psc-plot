import xarray as xr
import xrft

from ...dimension import DIMENSIONS, FOURIER_NAME_PREFIX
from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser


class Fourier(PluginBp):
    def __init__(self, dim_name: str, force_periodic: bool = False):
        self.dim_name = dim_name
        self.force_periodic = force_periodic

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        if self.force_periodic:
            # not sure if this is good or bad
            # sometimes it sharpens signals, sometimes it adds noise
            da_mirror = da.isel({self.dim_name: slice(None, 0, -1)})
            da_mirror = da_mirror.assign_coords({self.dim_name: da_mirror.coords[self.dim_name] * -1})
            da = xr.concat([da_mirror, da], dim=self.dim_name)

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
