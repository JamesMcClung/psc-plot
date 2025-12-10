import dask.dataframe as df
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

    def apply[T: xr.DataArray | pd.DataFrame | df.DataFrame](self, data: T) -> T:
        ensure_type(self.__class__.__name__, data, *get_allowed_types(T))
        attrs_before = data.attrs

        if isinstance(data, xr.DataArray):
            # 1. apply implicit coordinate transforms, as necessary
            for dim_name in self.all_dims:
                # 1a. already have the coordinate; do nothing
                if dim_name in data.dims:
                    continue

                # 1b. need to do a Fourier transform
                dim = DIMENSIONS[dim_name]
                f_dim = dim.toggle_fourier()
                if f_dim.name.plain in data.dims:
                    fourier = Fourier(f_dim)
                    data = fourier.apply(data)
                    continue

                # 1c. need to do a coordinate transform
                # TODO

            # 2. reduce remaining dimensions via arithmetic mean
            for dim_name in data.dims:
                if dim_name not in self.all_dims:
                    reduce = Reduce(dim_name, "mean")
                    data = reduce.apply(data)

        elif isinstance(data, (pd.DataFrame, df.DataFrame)):
            # 1. coordinate transform
            # TODO

            # 2. drop unused vars
            drop_vars = []
            for var_name in data.columns:
                if var_name not in self.all_dims + [DEPENDENT_VAR_KEY]:
                    drop_vars.append(var_name)
            data = data.drop(columns=drop_vars)

        # do the main job of Versus: specify which dims are spatial, temporal, etc.
        data.attrs = (
            attrs_before
            | getattr(data, "attrs", {})
            | {
                SPATIAL_DIMS_KEY: self.spatial_dims,
                TIME_DIM_KEY: self.time_dim,
                COLOR_DIM_KEY: self.color_dim,
                NAME_FRAGMENTS_KEY: attrs_before[NAME_FRAGMENTS_KEY] + self.get_name_fragments(),
            }
        )

        if isinstance(data, (pd.DataFrame, df.DataFrame)) and DEPENDENT_VAR_KEY not in data.attrs:
            data.attrs[DEPENDENT_VAR_KEY] = data.attrs[SPATIAL_DIMS_KEY].pop()

        return data

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
    help=f"Specifies the independent axes to plot against (automatically performs necessary Fourier and coordinate transforms, and reduces other dimensions via arithmetic mean). The optional `{_TIME_PREFIX}[dim_name]` specifies an additional dimension to use as the time axis. If unspecified, defaults to `{_TIME_PREFIX}t` unless t is used as a spatial axis. Alternatively, disable time by passing `{_TIME_PREFIX}` (with no dim_name).",
    nargs="+",
)
def parse_versus(args: list[str]) -> Versus:
    spatial_dims = []
    time_dim = "t"
    time_dim_is_default = True
    color_dim = None
    for arg in args:
        if arg.startswith(_TIME_PREFIX):
            time_dim = arg.removeprefix(_TIME_PREFIX) or None
            parse_util.check_optional_identifier(time_dim, "time dim_name")
            time_dim_is_default = False
        elif arg.startswith(_COLOR_PREFIX):
            color_dim = arg.removeprefix(_COLOR_PREFIX)
            parse_util.check_identifier(color_dim, "color dim_name")
        else:
            parse_util.check_identifier(arg, "dim_name")
            spatial_dims.append(arg)
            if time_dim_is_default and arg == time_dim:
                time_dim = None

    return Versus(spatial_dims, time_dim, color_dim)
