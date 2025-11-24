import xarray as xr

from ....dimension import DIMENSIONS
from ...adaptor import Adaptor
from ...compatability import ensure_type
from ...keys import SPATIAL_DIMS_KEY, TIME_DIM_KEY
from .. import parse_util
from ..registry import adaptor_parser
from .fourier import Fourier
from .reduce import Reduce


class Versus(Adaptor):

    def __init__(self, spatial_dims: list[str], time_dim: str | None):
        self.spatial_dims = spatial_dims
        self.time_dim = time_dim
        self.all_dims = spatial_dims + ([time_dim] if time_dim else [])
        self.cached_inner_adaptors: list[Adaptor] | None = None

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        ensure_type(self.__class__.__name__, da, xr.DataArray)

        if self.cached_inner_adaptors is None:
            self.cached_inner_adaptors = []
            # 1. apply implicit coordinate transforms, as necessary
            for dim_name in self.all_dims:
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
                if dim_name not in self.all_dims:
                    reduce = Reduce(dim_name, "mean")
                    self.cached_inner_adaptors.append(reduce)
                    da = reduce.apply(da)
        else:
            for adaptor in self.cached_inner_adaptors:
                da = adaptor.apply(da)

        # let the animator take it from here
        da.attrs[SPATIAL_DIMS_KEY] = self.spatial_dims
        da.attrs[TIME_DIM_KEY] = self.time_dim

        return da

    def get_modified_var_latex(self, dep_var_name):
        assert self.cached_inner_adaptors is not None, "can't modify dep var name—don't know what inner adaptors are required yet"

        for p in self.cached_inner_adaptors:
            dep_var_name = p.get_modified_var_latex(dep_var_name)

        return dep_var_name

    def get_name_fragments(self) -> list[str]:
        # don't include inner adaptors because they can be inferred
        dims = ",".join(self.spatial_dims)
        if self.time_dim:
            dims = f"{self.time_dim};{dims}"
        return [f"vs_{dims}"]


_TIME_PREFIX = "time="
_VERSUS_FORMAT = f"dim_name | {_TIME_PREFIX}[dim_name]"


@adaptor_parser(
    "--versus",
    "-v",
    metavar=_VERSUS_FORMAT,
    help=f"Specifies the independent axes to plot against (automatically performs necessary Fourier and coordinate transforms, and reduces other dimensions via arithmetic mean). The optional `{_TIME_PREFIX}[dim_name]` specifies an additional dimension to use as the time axis. If unspecified, defaults to `{_TIME_PREFIX}t`. Disable time by passing `{_TIME_PREFIX}`",
    nargs="+",
)
def parse_versus(args: list[str]) -> Versus:
    spatial_dims = []
    time_dim = "t"
    for arg in args:
        if arg.startswith(_TIME_PREFIX):
            time_dim = arg.removeprefix(_TIME_PREFIX)
            parse_util.check_value(time_dim, "time dim_name", list(DIMENSIONS) + [""])
            if time_dim == "":
                time_dim = None
        else:
            parse_util.check_value(arg, "dim_name", DIMENSIONS)
            spatial_dims.append(arg)

    return Versus(spatial_dims, time_dim)
