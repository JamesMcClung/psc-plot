import numpy as np
import xarray as xr
import xrft

from ...dimension import DIMENSIONS
from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser


class Fourier(PluginBp):
    def __init__(self, dim_name: str):
        self.dim_name = dim_name

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        # TODO properly handle inverse FT (i.e., actually use ifft)
        temp_prefix = "temp_"
        da = xrft.fft(da, dim=self.dim_name, true_phase=False, prefix=temp_prefix)

        # multiply coords by 2pi to go from frequency -> angular frequency
        fourier_dim = DIMENSIONS[self.dim_name].toggle_fourier()
        da = da.rename({temp_prefix + self.dim_name: fourier_dim.name})
        da = da.assign_coords({fourier_dim.name: 2 * np.pi * da.coords[fourier_dim.name]})

        return da

    def get_name_fragment(self) -> str:
        return f"fourier_{self.dim_name}"

    def get_modified_dep_var_name(self, title_stem: str) -> str:
        return f"\\mathcal{{F}}_{{{self.dim_name}}}[{title_stem}]"


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
