import xarray as xr

from ...dimension import DIMENSIONS
from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser
from .fourier import Fourier
from .reduce import Reduce


class Versus(PluginBp):
    def __init__(self, dim_names: list[str]):
        self.dim_names = dim_names

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        # 1. apply implicit coordinate transforms, as necessary
        for dim_name in self.dim_names:
            # 1a. already have the coordinate; do nothing
            if dim_name in da.dims:
                continue

            # 1b. need to do a Fourier transform
            dim = DIMENSIONS[dim_name]
            f_dim = dim.toggle_fourier()
            if f_dim.name in da.dims:
                fourier = Fourier(f_dim.name)
                da = fourier.apply(da)
                continue

            # 1c. need to do a coordinate transform
            # TODO

        # 2. reduce remaining dimensions via arithmetic mean
        for dim_name in da.dims:
            if dim_name not in self.dim_names:
                reduce = Reduce(dim_name, "mean")
                da = reduce.apply(da)

        # 3. transpose to correct dimension order
        da = da.transpose(*self.dim_names)

        return da

    def get_name_fragment(self) -> str:
        dims = ",".join(self.dim_names)
        return f"vs_{dims}"


_VERSUS_FORMAT = "dim_name"


@plugin_parser(
    "--versus",
    metavar=_VERSUS_FORMAT,
    help="specifies the independent axes to plot against (automatically performs necessary Fourier and coordinate transforms, and reduces other dimensions via arithmetic mean)",
    nargs="+",
)
def parse_versus(args: list[str]) -> Versus:
    for arg in args:
        parse_util.check_value(arg, "dim_name", DIMENSIONS)
    return Versus(args)
