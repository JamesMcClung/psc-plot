from lib.data.adaptor import MetadataAdaptor
from lib.data.adaptors.fourier import Fourier
from lib.data.adaptors.reduce import Reduce
from lib.data.data_with_attrs import Field, List
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class Versus(MetadataAdaptor):
    def __init__(self, spatial_dims: list[str], time_dim: str | None, color_dim: str | None):
        self.spatial_dims = spatial_dims
        self.time_dim = time_dim
        self.color_dim = color_dim
        self.all_dims = spatial_dims + ([time_dim] if time_dim else []) + ([color_dim] if color_dim else [])

    def apply_field(self, data: Field) -> Field:
        # going to cut out name fragments of inner adaptors, since they can be inferred
        initial_name_fragments = data.metadata.name_fragments

        # 1. apply implicit coordinate transforms, as necessary
        for dim_name in self.all_dims:
            # 1a. already have the coordinate; do nothing
            if dim_name in data.dims:
                continue

            # 1b. need to do a Fourier transform
            dim = data.metadata.var_infos[dim_name]
            f_dim = dim.toggle_fourier()
            if f_dim.key in data.dims:
                data = data.assign_metadata(
                    var_infos={**data.metadata.var_infos, f_dim.key: f_dim},
                )
                fourier = Fourier(f_dim.key)
                data = fourier.apply(data)
                continue

            # 1c. need to do a coordinate transform
            # TODO

        # 2. reduce remaining dimensions via arithmetic mean
        reduce_dims = [dim for dim in data.dims if dim not in self.all_dims]
        reduce = Reduce(reduce_dims, "mean")
        data = reduce.apply(data)

        return data.assign_metadata(
            spatial_dims=self.spatial_dims.copy(),
            time_dim=self.time_dim,
            color_dim=self.color_dim,
            name_fragments=initial_name_fragments,
        )

    def apply_list(self, data: List) -> List:
        # going to cut out name fragments of inner adaptors, since they can be inferred
        initial_name_fragments = data.metadata.name_fragments

        # 1. coordinate transform
        # TODO

        # 2. drop unused vars
        keep_vars = self.all_dims + ([data.metadata.active_key] if data.metadata.active_key else [])
        drop_vars = [active_key for active_key in data.dims if active_key not in keep_vars]
        data = data.assign_data(data.data.drop(columns=drop_vars))

        spatial_dims = self.spatial_dims.copy()
        if len(spatial_dims) == 1 and data.metadata.active_key is not None and data.metadata.active_key not in spatial_dims:
            spatial_dims.append(data.metadata.active_key)

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


@arg_parser(
    dest="adaptors",
    flags=["--versus", "-v"],
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
