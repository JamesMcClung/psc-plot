from typing import Literal, Self

from matplotlib.colors import SymLogNorm
from matplotlib.scale import SymmetricalLogScale

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


class Scale:
    scale_key: ScaleKey

    def __init_subclass__(cls):
        SCALE_TYPES.append(cls)

    def to_axis_scale(self, data: DataWithAttrs) -> plt_util.AxisScaleArg:
        return self.scale_key

    def to_color_norm(self, data: DataWithAttrs) -> plt_util.ColorNormArg:
        return self.scale_key

    @classmethod
    def to_argparse_format(cls) -> str:
        return cls.scale_key

    @classmethod
    def try_from_argparse_format(cls, arg: str) -> Self | None:
        if arg == cls.scale_key:
            return cls()
        return None


SCALE_TYPES: list[Scale] = []  # automatically populated with subclasses


class LinearScale(Scale):
    scale_key = "linear"


class LogScale(Scale):
    scale_key = "log"


class SymLogScale(Scale):
    scale_key = "symlog"
    LINEAR_THRESHOLD_ARG_FORMAT = "linear_threshold"

    def __init__(self, linear_threshold: float | None):
        self.linear_threshold = linear_threshold

    def _choose_linear_threshold(self, data: DataWithAttrs) -> float:
        # TODO pipe it through Magnitude -> Reduce, but reduce via quantile... which requires refactoring Reduce to support subargs
        return 0.0001

    def to_axis_scale(self, data: DataWithAttrs) -> plt_util.AxisScaleArg:
        linthresh = self.linear_threshold or self._choose_linear_threshold(data)
        return SymmetricalLogScale(None, linthresh=linthresh)

    def to_color_norm(self, data: DataWithAttrs) -> plt_util.ColorNormArg:
        linthresh = self.linear_threshold or self._choose_linear_threshold(data)
        return SymLogNorm(linthresh)

    @classmethod
    def to_argparse_format(cls) -> str:
        return f"{cls.scale_key}[{parse_util.SUBARG_DELIM}{cls.LINEAR_THRESHOLD_ARG_FORMAT}]"

    @classmethod
    def try_from_argparse_format(cls, arg: str) -> Self | None:
        scale_key_arg, linear_threshold_arg = parse_util.parse_optional_assignment(arg, cls.to_argparse_format(), delim=parse_util.SUBARG_DELIM)

        if scale_key_arg != cls.scale_key:
            return None

        linear_threshold = parse_util.parse_optional_number(linear_threshold_arg, cls.LINEAR_THRESHOLD_ARG_FORMAT, float)

        return cls(linear_threshold)


class SetScale(Hook):
    def __init__(self, dim_name: str | None, scale: Scale):
        self.dim_name = dim_name
        self.scale = scale

    def pre_init_fig(self, init_data):
        init_data = assert_impl(init_data, HasData)

        data = init_data.data

        if self.dim_name is None:
            # find and set the dependent scale/norm
            if check_impl(init_data, HasSpatialScales) and init_data.last_spatial_dim_is_dependent:
                init_data.spatial_scales[-1] = self.scale.to_axis_scale(data)
            elif check_impl(init_data, HasColorNorm) and init_data.color_is_dependent:
                init_data.color_norm = self.scale.to_color_norm(data)
            else:
                message = f"dependent scale not found"
                raise Exception(message)
        else:
            spatial_dims = data.metadata.spatial_dims
            color_dim = data.metadata.color_dim

            if self.dim_name in spatial_dims:
                init_data = assert_impl(init_data, HasSpatialScales)
                init_data.spatial_scales[spatial_dims.index(self.dim_name)] = self.scale.to_axis_scale(data)
            elif self.dim_name == color_dim:
                init_data = assert_impl(init_data, HasColorNorm)
                init_data.color_norm = self.scale.to_color_norm(data)
            else:
                message = f"'{self.dim_name}' isn't a dimension"
                raise Exception(message)


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
        maybe_scale = scale_type.try_from_argparse_format(scale_arg)
        if maybe_scale:
            return SetScale(dim_name, maybe_scale)

    parse_util.fail_format(scale_arg, ANY_SCALE_ARGS_FORMAT)
