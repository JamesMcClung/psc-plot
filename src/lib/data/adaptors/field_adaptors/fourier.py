import numpy as np
import xarray as xr
import xrft

from ....dimension import DIMENSIONS, Dimension
from ...adaptor import AtomicAdaptor
from .. import parse_util
from ..registry import adaptor_parser


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


class Fourier(AtomicAdaptor):
    allowed_types = [xr.DataArray]

    def __init__(self, dims: Dimension | list[Dimension]):
        if isinstance(dims, Dimension):
            dims = [dims]
        self.dims = dims

    def apply_atomic(self, da: xr.DataArray) -> xr.DataArray:
        for dim in self.dims:
            da = toggle_fourier(da, dim)

        return da

    def get_name_fragments(self) -> list[str]:
        dim_names = ",".join(dim.name.plain for dim in self.dims)
        return [f"fourier_{dim_names}"]

    def get_modified_var_latex(self, var_latex: str) -> str:
        dim_latexs = ",".join(dim.name.latex for dim in self.dims)
        return f"\\mathcal{{F}}_{{{dim_latexs}}}[{var_latex}]"


FOURIER_FORMAT = "dim_name"


@adaptor_parser(
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
