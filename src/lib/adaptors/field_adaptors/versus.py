import xarray as xr

from ...dimension import DIMENSIONS
from .. import parse_util
from ..adaptor_base import FieldAdaptor
from ..registry import adaptor_parser
from .fourier import Fourier
from .reduce import Reduce


class Versus(FieldAdaptor):
    def __init__(self, dim_names: list[str]):
        self.dim_names = dim_names
        self.cached_inner_adaptors: list[FieldAdaptor] | None = None

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        if self.cached_inner_adaptors is None:
            self.cached_inner_adaptors = []
            # 1. apply implicit coordinate transforms, as necessary
            for dim_name in self.dim_names:
                # 1a. already have the coordinate; do nothing
                if dim_name in da.dims:
                    continue

                # 1b. need to do a Fourier transform
                dim = DIMENSIONS[dim_name]
                f_dim = dim.toggle_fourier()
                if f_dim.name.plain in da.dims:
                    fourier = Fourier(f_dim)
                    self.cached_inner_adaptors.append(fourier)
                    da = fourier.apply(da)
                    continue

                # 1c. need to do a coordinate transform
                # TODO

            # 2. reduce remaining dimensions via arithmetic mean
            for dim_name in da.dims:
                if dim_name not in self.dim_names:
                    reduce = Reduce(dim_name, "mean")
                    self.cached_inner_adaptors.append(reduce)
                    da = reduce.apply(da)
        else:
            for adaptor in self.cached_inner_adaptors:
                da = adaptor.apply(da)

        # 3. transpose to correct dimension order
        da = da.transpose(*self.dim_names)

        return da

    def get_modified_var_name(self, dep_var_name):
        assert self.cached_inner_adaptors is not None, "can't modify dep var name—don't know what inner adaptors are required yet"

        for p in self.cached_inner_adaptors:
            dep_var_name = p.get_modified_var_name(dep_var_name)

        return dep_var_name

    def get_name_fragment(self) -> str:
        # don't include inner adaptors because they can be inferred
        dims = ",".join(self.dim_names)
        return f"vs_{dims}"


_VERSUS_FORMAT = "dim_name"


@adaptor_parser(
    "--versus",
    "-v",
    metavar=_VERSUS_FORMAT,
    help="specifies the independent axes to plot against (automatically performs necessary Fourier and coordinate transforms, and reduces other dimensions via arithmetic mean)",
    nargs="+",
)
def parse_versus(args: list[str]) -> Versus:
    for arg in args:
        parse_util.check_value(arg, "dim_name", DIMENSIONS)
    return Versus(args)
