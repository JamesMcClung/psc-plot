from typing import Literal

from lib.data.adaptor import MetadataAdaptor
from lib.data.adaptors.fourier import Fourier
from lib.data.adaptors.reduce import Reduce
from lib.data.data_with_attrs import DataWithAttrs, Field, List
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class Versus(MetadataAdaptor):
    def __init__(
        self,
        spatial_dims: list[str],
        *,
        time_dim_rule: str | None | Literal["guess"],
        color_dim: str | None,
    ):
        self.spatial_dims = spatial_dims
        self.time_dim_rule = time_dim_rule
        self.color_dim = color_dim

    def _get_retained_dim_keys(self, data: DataWithAttrs) -> list[str]:
        retained_dims = self.spatial_dims.copy()

        if time_dim := self._get_time_dim(data):
            retained_dims.append(time_dim)

        if self.color_dim:
            retained_dims.append(self.color_dim)

        if isinstance(data, List) and data.metadata.active_key:
            retained_dims.append(data.metadata.active_key)

        return retained_dims

    def _get_time_dim(self, data: DataWithAttrs) -> str | None:
        if self.time_dim_rule != "guess":
            return self.time_dim_rule

        if "t" in data.dims and "t" not in self.spatial_dims and "t" != self.color_dim:
            return "t"

        return None

    def apply_field(self, data: Field) -> Field:
        # 1. apply implicit coordinate transforms, as necessary
        retained_dims = self._get_retained_dim_keys(data)
        for dim_name in retained_dims:
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
        reduce_dims = [dim for dim in data.dims if dim not in retained_dims]
        reduce = Reduce(reduce_dims, "mean")
        data = reduce.apply(data)

        return data.assign_metadata(
            spatial_dims=self.spatial_dims.copy(),
            time_dim=self._get_time_dim(data),
            color_dim=self.color_dim,
        )

    def apply_list(self, data: List) -> List:
        # 1. coordinate transform
        # TODO

        # 2. drop unused vars
        keep_vars = self._get_retained_dim_keys(data)
        drop_vars = [active_key for active_key in data.dims if active_key not in keep_vars]
        data = data.assign_data(data.data.drop(columns=drop_vars))

        spatial_dims = self.spatial_dims.copy()
        if len(spatial_dims) == 1 and data.metadata.active_key is not None and data.metadata.active_key not in spatial_dims:
            spatial_dims.append(data.metadata.active_key)

        return data.assign_metadata(
            spatial_dims=spatial_dims,
            time_dim=self._get_time_dim(data),
            color_dim=self.color_dim,
        )

    def get_name_fragments(self) -> list[str]:
        dims = ",".join(self.spatial_dims)
        if self.time_dim_rule != "guess":
            dims += f";{_TIME_PREFIX}{self.time_dim_rule or ''}"
        if self.color_dim:
            dims += f";{_COLOR_PREFIX}{self.color_dim}"
        return [f"v_{dims}"]


_TIME_PREFIX = "time="
_COLOR_PREFIX = "color="
_VERSUS_FORMAT = f"dim_key | {_TIME_PREFIX}[dim_key] | {_COLOR_PREFIX}dim_key"


@arg_parser(
    dest="adaptors",
    flags=["--versus", "-v"],
    metavar=_VERSUS_FORMAT,
    help=f"Specifies the independent axes of the plot. Remaining dimensions are reduced via arithmetic mean. Time has a special behavior: if {_TIME_PREFIX}[dim_key] is omitted, it is set to 't' if 't' is present in the data and isn't being used as a different axis. Disable this guessing by passing {_TIME_PREFIX} (with no dim_key).",
    nargs="+",
)
def parse_versus(args: list[str]) -> Versus:
    spatial_dims = []
    time_dim_rule = "guess"
    color_dim = None
    for arg in args:
        if arg.startswith(_TIME_PREFIX):
            time_dim_rule = arg.removeprefix(_TIME_PREFIX) or None
            parse_util.check_optional_identifier(time_dim_rule, "time dim_key")
        elif arg.startswith(_COLOR_PREFIX):
            color_dim = arg.removeprefix(_COLOR_PREFIX)
            parse_util.check_identifier(color_dim, "color dim_key")
        else:
            parse_util.check_identifier(arg, "dim_key")
            spatial_dims.append(arg)

    return Versus(spatial_dims, time_dim_rule=time_dim_rule, color_dim=color_dim)
