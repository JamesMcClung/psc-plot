from lib.data.adaptor import CheckedAdaptor
from lib.data.data_with_attrs import Field, List

from ....dimension import DIMENSIONS
from .. import parse_util
from ..registry import adaptor_parser
from .fourier import Fourier
from .reduce import Reduce


class Versus(CheckedAdaptor):
    def __init__(self, spatial_dims: list[str], time_dim: str | None, color_dim: str | None):
        self.spatial_dims = spatial_dims
        self.time_dim = time_dim
        self.color_dim = color_dim
        self.all_dims = spatial_dims + ([time_dim] if time_dim else []) + ([color_dim] if color_dim else [])

    def apply_checked[D: Field | List](self, data: D) -> D:
        # going to cut out name fragments of inner adaptors, since they can be inferred
        initial_name_fragments = data.metadata.name_fragments

        if isinstance(data, Field):
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

        elif isinstance(data, List):
            # 1. coordinate transform
            # TODO

            # 2. drop unused vars
            drop_vars = []
            for var_name in data.dims:
                if var_name not in self.all_dims + [data.metadata.dependent_var]:
                    drop_vars.append(var_name)

            data = data.assign_data(data.data.drop(columns=drop_vars))

        # do the main job of Versus: specify which dims are spatial, temporal, etc.

        spatial_dims = self.spatial_dims.copy()

        if isinstance(data, List) and not data.metadata.dependent_var:
            data = data.assign_metadata(dependent_var=spatial_dims.pop())

        return data.assign_metadata(
            spatial_dims=spatial_dims,
            time_dim=self.time_dim,
            color_dim=self.color_dim,
            name_fragments=initial_name_fragments,
        )

    def get_name_fragments(self) -> list[str]:
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
