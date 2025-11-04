import numpy as np
import xarray as xr
import xrft

from ...dimension import DIMENSIONS, Dimension
from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser


def toggle_fourier(da: xr.DataArray, dim: Dimension) -> xr.DataArray:
    temp_prefix = "temp_"
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


class Fourier(PluginBp):
    def __init__(self, dims: list[Dimension]):
        self.dims = dims

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        for dim in self.dims:
            da = toggle_fourier(da, dim)

        return da

    def get_name_fragment(self) -> str:
        dim_names = ",".join(dim.name.plain for dim in self.dims)
        return f"fourier_{dim_names}"

    def get_modified_dep_var_name(self, title_stem: str) -> str:
        dim_latexs = ",".join(dim.name.latex for dim in self.dims)
        return f"\\mathcal{{F}}_{{{dim_latexs}}}[{title_stem}]"


FOURIER_FORMAT = "dim_name"


@plugin_parser(
    "--fourier",
    "-f",
    metavar=FOURIER_FORMAT,
    help="perform a Fourier transform along the given dimensions",
    nargs="+",
)
def parse_fourier(args: list[str]) -> Fourier:
    for dim_name in args:
        parse_util.check_value(dim_name, "dim_name", DIMENSIONS)

    dims = [DIMENSIONS[dim_name] for dim_name in args]

    return Fourier(dims)
