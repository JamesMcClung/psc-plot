import numpy as np
import xarray as xr
import xrft

from lib.data.adaptor import BareAdaptor
from lib.dimension import DIMENSIONS, Dimension
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


def toggle_fourier(da: xr.DataArray, dim: Dimension) -> xr.DataArray:
    temp_prefix = "temp_"
    f_dim = dim.toggle_fourier()

    # multiply/or divide coords by 2pi to go from frequency <-> angular frequency

    if dim.is_fourier():
        da = da.assign_coords({dim.key: da.coords[dim.key] / (2 * np.pi)})
        da = xrft.ifft(da, dim=dim.key, prefix=temp_prefix, lag=0.0)
        da = da.rename({temp_prefix + dim.key: f_dim.key})
    else:
        da = xrft.fft(da, dim=dim.key, prefix=temp_prefix)
        da = da.rename({temp_prefix + dim.key: f_dim.key})
        da = da.assign_coords({f_dim.key: da.coords[f_dim.key] * (2 * np.pi)})

    return da


class Fourier(BareAdaptor):
    def __init__(self, dims: Dimension | list[Dimension]):
        if isinstance(dims, Dimension):
            dims = [dims]
        self.dims = dims

    def apply_field_bare(self, da: xr.DataArray) -> xr.DataArray:
        for dim in self.dims:
            da = toggle_fourier(da, dim)

        return da

    def get_name_fragments(self) -> list[str]:
        dim_names = ",".join(dim.key for dim in self.dims)
        return [f"fourier_{dim_names}"]

    def get_modified_var_latex(self, var_latex: str) -> str:
        dim_latexs = ",".join(dim.name.latex for dim in self.dims)
        return f"\\mathcal{{F}}_{{{dim_latexs}}}[{var_latex}]"


FOURIER_FORMAT = "dim_name"


@arg_parser(
    dest="adaptors",
    flags=["--fourier", "-f"],
    metavar=FOURIER_FORMAT,
    help="perform a Fourier transform along the given dimensions",
    nargs="+",
)
def parse_fourier(args: list[str]) -> Fourier:
    for dim_name in args:
        parse_util.check_value(dim_name, "dim_name", DIMENSIONS)

    dims = [DIMENSIONS[dim_name] for dim_name in args]

    return Fourier(dims)
