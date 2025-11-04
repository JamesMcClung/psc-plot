import numpy as np
import xarray as xr
import xrft

from ...dimension import DIMENSIONS, Dimension
from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser


class Fourier(PluginBp):
    def __init__(self, dim: Dimension):
        self.dim = dim

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        temp_prefix = "temp_"

        f_dim = self.dim.toggle_fourier()

        # multiply/or divide coords by 2pi to go from frequency <-> angular frequency

        if self.dim.is_fourier():
            da = da.assign_coords({self.dim.name.plain: da.coords[self.dim.name.plain] / (2 * np.pi)})
            da = xrft.ifft(da, dim=self.dim.name.plain, prefix=temp_prefix, lag=0.0)
            da = da.rename({temp_prefix + self.dim.name.plain: f_dim.name.plain})
        else:
            da = xrft.fft(da, dim=self.dim.name.plain, prefix=temp_prefix)
            da = da.rename({temp_prefix + self.dim.name.plain: f_dim.name.plain})
            da = da.assign_coords({f_dim.name.plain: da.coords[f_dim.name.plain] * (2 * np.pi)})

        return da

    def get_name_fragment(self) -> str:
        return f"fourier_{self.dim.name.plain}"

    def get_modified_dep_var_name(self, title_stem: str) -> str:
        return f"\\mathcal{{F}}_{{{self.dim.name.latex}}}[{title_stem}]"


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
    dim = DIMENSIONS[dim_name]

    return Fourier(dim)
