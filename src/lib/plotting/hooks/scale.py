from typing import Literal, Self

from lib.data.data_with_attrs import DataWithAttrs, List
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.plotting import plt_util
from lib.plotting.frame_data_traits import (
    HasColorNorm,
    HasData,
    HasSpatialScales,
    assert_impl,
    check_impl,
)
from lib.plotting.hook import Hook

type ScaleKey = Literal["linear", "log", "symlog"]
SCALE_KEYS: tuple[ScaleKey, ...] = ScaleKey.__value__.__args__


class Scale(Hook):
    scale_key: ScaleKey

    def __init_subclass__(cls):
        SCALE_TYPES.append(cls)

    def __init__(self, dim_name: str | None):
        self.dim_name = dim_name

    def to_axis_scale(self, data: DataWithAttrs) -> plt_util.AxisScaleArg:
        return self.scale_key

    def to_color_norm(self, data: DataWithAttrs) -> plt_util.ColorNormArg:
        return self.scale_key

    @classmethod
    def to_argparse_format(cls) -> str:
        return cls.scale_key

    @classmethod
    def try_from_argparse_format(cls, arg: str, dim_name: str | None) -> Self | None:
        if arg == cls.scale_key:
            return cls(dim_name)
        return None

    def pre_init_fig(self, init_data):
        init_data = assert_impl(init_data, HasData)

        data = init_data.data

        if self.dim_name is None or isinstance(data, List) and self.dim_name == data.metadata.dependent_var:
            # find and set the dependent scale/norm
            if check_impl(init_data, HasSpatialScales) and init_data.last_spatial_dim_is_dependent:
                init_data.spatial_scales[-1] = self.to_axis_scale(data)
            elif check_impl(init_data, HasColorNorm) and init_data.color_is_dependent:
                init_data.color_norm = self.to_color_norm(data)
            else:
                message = f"dependent scale not found"
                raise Exception(message)
        else:
            spatial_dims = data.metadata.spatial_dims
            color_dim = data.metadata.color_dim

            if self.dim_name in spatial_dims:
                init_data = assert_impl(init_data, HasSpatialScales)
                init_data.spatial_scales[spatial_dims.index(self.dim_name)] = self.to_axis_scale(data)
            elif self.dim_name == color_dim:
                init_data = assert_impl(init_data, HasColorNorm)
                init_data.color_norm = self.to_color_norm(data)
            else:
                message = f"'{self.dim_name}' isn't a dimension"
                raise Exception(message)


SCALE_TYPES: list[Scale] = []  # automatically populated with subclasses


class LinearScale(Scale):
    scale_key = "linear"


class LogScale(Scale):
    scale_key = "log"


ANY_SCALE_ARGS_FORMAT = "{" + ",".join(scale_type.to_argparse_format() for scale_type in SCALE_TYPES) + "}"
SCALE_FORMAT = f"[dim_name=]{ANY_SCALE_ARGS_FORMAT}"


@arg_parser(
    flags="--scale",
    metavar=SCALE_FORMAT,
    help="set the axis/color scale of the dependent variable or specified dimension (default: linear)",
    dest="hooks",
)
def parse_vline(arg: str) -> Scale:
    if "=" in arg:
        dim_name, scale_arg = parse_util.parse_assignment(arg, SCALE_FORMAT)
        parse_util.check_identifier(dim_name, "dim_name")
    else:
        dim_name = None
        scale_arg = arg

    for scale_type in SCALE_TYPES:
        maybe_scale = scale_type.try_from_argparse_format(scale_arg, dim_name)
        if maybe_scale:
            return maybe_scale

    parse_util.fail_format(scale_arg, ANY_SCALE_ARGS_FORMAT)
