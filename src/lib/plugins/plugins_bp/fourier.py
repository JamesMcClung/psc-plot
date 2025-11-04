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
        temp_prefix = "temp_"

        dim = DIMENSIONS[self.dim_name]
        f_dim = dim.toggle_fourier()

        # multiply/or divide coords by 2pi to go from frequency <-> angular frequency

        if dim.is_fourier():
            da = da.assign_coords({dim.name.plain: da.coords[dim.name.plain] / (2 * np.pi)})
            da = xrft.ifft(da, dim=dim.name.plain, prefix=temp_prefix, lag=0.0)
            da = da.rename({temp_prefix + dim.name.plain: f_dim.name.plain})
        else:
            da = xrft.fft(da, dim=dim.name.plain, prefix=temp_prefix)
            da = da.rename({temp_prefix + dim.name.plain: f_dim.name.plain})
            da = da.assign_coords({f_dim.name.plain: da.coords[f_dim.name.plain] * (2 * np.pi)})

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
