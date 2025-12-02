import pandas as pd
import xarray as xr

from ....dimension import DIMENSIONS
from ...adaptor import Adaptor
from ...compatability import ensure_type, get_allowed_types
from ...keys import (
    COLOR_DIM_KEY,
    DEPENDENT_VAR_KEY,
    NAME_FRAGMENTS_KEY,
    SPATIAL_DIMS_KEY,
    TIME_DIM_KEY,
)
from .. import parse_util
from ..registry import adaptor_parser
from .fourier import Fourier
from .reduce import Reduce


class Versus(Adaptor):
    def __init__(self, spatial_dims: list[str], time_dim: str | None, color_dim: str | None):
        self.spatial_dims = spatial_dims
        self.time_dim = time_dim
        self.color_dim = color_dim
        self.all_dims = spatial_dims + ([time_dim] if time_dim else []) + ([color_dim] if color_dim else [])

    def apply[T: xr.DataArray | pd.DataFrame](self, da: T) -> T:
        ensure_type(self.__class__.__name__, da, *get_allowed_types(T))
        name_frags_before = list(da.attrs.get(NAME_FRAGMENTS_KEY, []))

        if isinstance(da, xr.DataArray):
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
                    da = fourier.apply(da)
                    continue

                # 1c. need to do a coordinate transform
                # TODO

            # 2. reduce remaining dimensions via arithmetic mean
            for dim_name in da.dims:
                if dim_name not in self.all_dims:
                    reduce = Reduce(dim_name, "mean")
                    da = reduce.apply(da)

        elif isinstance(da, pd.DataFrame):
            # 1. coordinate transform
            # TODO

            # 2. drop unused vars
            drop_vars = []
            for var_name in da.columns:
                if var_name not in self.all_dims + [DEPENDENT_VAR_KEY]:
                    drop_vars.append(var_name)
            da = da.drop(columns=drop_vars)

        # let the animator take it from here
        da.attrs[SPATIAL_DIMS_KEY] = self.spatial_dims
        da.attrs[TIME_DIM_KEY] = self.time_dim
        da.attrs[COLOR_DIM_KEY] = self.color_dim
        da.attrs[NAME_FRAGMENTS_KEY] = name_frags_before + self.get_name_fragments()

        return da

    def get_name_fragments(self) -> list[str]:
        # don't include inner adaptors because they can be inferred
        dims = ",".join(self.spatial_dims)
        if self.time_dim:
            dims += f";time={self.time_dim}"
        if self.color_dim:
            dims += f";color={self.color_dim}"
        return [f"vs_{dims}"]


_TIME_PREFIX = "time="
_COLOR_PREFIX = "color="
_VERSUS_FORMAT = f"dim_name | {_TIME_PREFIX}[dim_name] | {_COLOR_PREFIX}dim_name"


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
    color_dim = None
    for arg in args:
        if arg.startswith(_TIME_PREFIX):
            time_dim = arg.removeprefix(_TIME_PREFIX) or None
            parse_util.check_optional_identifier(time_dim, "time dim_name")
        elif arg.startswith(_COLOR_PREFIX):
            color_dim = arg.removeprefix(_COLOR_PREFIX) or None
            parse_util.check_identifier(color_dim, "color dim_name")
        else:
            parse_util.check_identifier(arg, "dim_name")
            spatial_dims.append(arg)

    return Versus(spatial_dims, time_dim, color_dim)
