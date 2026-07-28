from dataclasses import replace
from typing import Literal

from lib.data.adaptor import MetadataAdaptor
from lib.data.adaptors.reduce import Reduce
from lib.data.data_with_attrs import DataWithAttrs, Field, List
from lib.data.plot_target import PlotTarget, SpatialDims, SpatialDimsRTheta, SpatialDimsXY
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class Versus(MetadataAdaptor):
    def __init__(
        self,
        spatial_dims: list[str],
        *,
        time_dim_rule: str | None | Literal["guess"],
        color_dim: str | None,
        axes_idx: tuple[int, int] = (1, 1),
    ):
        self.spatial_dims = spatial_dims
        self.time_dim_rule = time_dim_rule
        self.color_dim = color_dim
        self.axes_idx = axes_idx

    def _get_time_dim(self, data: DataWithAttrs) -> str | None:
        if self.time_dim_rule != "guess":
            return self.time_dim_rule

        if "t" in data.dims and "t" not in self.spatial_dims and "t" != self.color_dim:
            return "t"

        return None

    def _get_spatial_dims(self, data: DataWithAttrs) -> SpatialDims:
        spatial_dims = self.spatial_dims.copy()

        if len(spatial_dims) == 1 and data.metadata.active_key:
            spatial_dims.append(data.metadata.active_key)

        if data.metadata.var_infos[spatial_dims[0]].geometry == "polar:r" and data.metadata.var_infos[spatial_dims[1]].geometry == "polar:theta":
            return SpatialDimsRTheta(*spatial_dims)

        return SpatialDimsXY(*spatial_dims)

    def _get_color_dim(self, data: DataWithAttrs) -> str | None:
        if isinstance(data, Field):
            if self.color_dim:
                message = "Can't set color dim of field data"
                raise ValueError(message)
            if len(self.spatial_dims) == 2:
                return data.metadata.active_key
            return None

        return self.color_dim

    def apply_world(self, world):
        data = self.apply(world.active_data)
        new_plot_target = PlotTarget(
            world.active_prepath,
            spatial_dims=self._get_spatial_dims(data),
            color_dim=self._get_color_dim(data),
            time_dim=self._get_time_dim(data),
            axes_index=self.axes_idx,
        )
        return replace(
            world,
            plot_targets=world.plot_targets + [new_plot_target],
            datas=world.datas | {world.active_prepath: data},
        )

    def apply_field(self, data: Field) -> Field:
        used_dims = {*self.spatial_dims, self._get_time_dim(data), self.color_dim}
        reduce_dims = [dim for dim in data.dims if dim not in used_dims]  # preserve order
        reduce = Reduce(reduce_dims, "mean")
        return reduce.apply(data)

    def apply_list(self, data: List) -> List:
        return data

    def get_name_fragments(self) -> list[str]:
        dims = ",".join(self.spatial_dims)
        if self.time_dim_rule != "guess":
            dims += f";{_TIME_PREFIX}{self.time_dim_rule or ''}"
        if self.color_dim:
            dims += f";{_COLOR_PREFIX}{self.color_dim}"
        return [f"v_{dims}"]


_TIME_PREFIX = "time="
_COLOR_PREFIX = "color="
_AXES_IDX_PREFIX = "loc="
_AXES_IDX_FORMAT = f"{_AXES_IDX_PREFIX}i,j"
_VERSUS_FORMAT = f"dim_key | {_TIME_PREFIX}[dim_key] | {_COLOR_PREFIX}dim_key | {_AXES_IDX_FORMAT}"


@arg_parser(
    dest="adaptors",
    flags=["--versus", "-v"],
    metavar=_VERSUS_FORMAT,
    help=f"Specifies the independent axes of the plot. Remaining dimensions are reduced via arithmetic mean. Time has a special behavior: if {_TIME_PREFIX}[dim_key] is omitted, it is set to 't' if 't' is present in the data and isn't being used as a different axis. Disable this guessing by passing '{_TIME_PREFIX}' (with no dim_key). The special '{_AXES_IDX_FORMAT}' argument sets the 1-indexed location of the subplot in the figure grid, which is 1,1 by default.",
    nargs="+",
)
def parse_versus(args: list[str]) -> Versus:
    spatial_dims = []
    time_dim_rule = "guess"
    color_dim = None
    axes_idx = 1, 1
    for arg in args:
        if arg.startswith(_TIME_PREFIX):
            time_dim_rule = arg.removeprefix(_TIME_PREFIX) or None
            parse_util.parse_optional_identifier(time_dim_rule, "time dim_key")
        elif arg.startswith(_COLOR_PREFIX):
            color_dim = arg.removeprefix(_COLOR_PREFIX)
            parse_util.parse_identifier(color_dim, "color dim_key")
        elif arg.startswith(_AXES_IDX_PREFIX):
            axes_idx_arg = arg.removeprefix(_AXES_IDX_PREFIX)
            i_arg, j_arg = parse_util.parse_assignment(axes_idx_arg, "i,j", delim=",")  # bit of a hack
            i = parse_util.parse_number(i_arg, "i", int)
            j = parse_util.parse_number(j_arg, "j", int)
            axes_idx = i, j
        else:
            parse_util.parse_identifier(arg, "dim_key")
            spatial_dims.append(arg)

    return Versus(spatial_dims, time_dim_rule=time_dim_rule, color_dim=color_dim, axes_idx=axes_idx)
