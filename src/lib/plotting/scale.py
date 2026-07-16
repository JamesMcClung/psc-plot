from typing import Literal, Self

from matplotlib.colors import SymLogNorm
from matplotlib.scale import SymmetricalLogScale

from lib.data.data_with_attrs import DataWithAttrs
from lib.parsing import parse_util
from lib.plotting import plt_util

type ScaleKey = Literal["linear", "log", "symlog"]
SCALE_KEYS: tuple[ScaleKey, ...] = ScaleKey.__value__.__args__


class Scale:
    scale_key: ScaleKey

    def __init_subclass__(cls):
        SCALE_TYPES.append(cls)

    def to_axis_scale(self) -> plt_util.AxisScaleArg:
        return self.scale_key

    def to_color_norm(self) -> plt_util.ColorNormArg:
        return self.scale_key

    def to_name_fragment_part(self) -> str:
        return str(self.scale_key)

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

    def to_axis_scale(self) -> plt_util.AxisScaleArg:
        linthresh = self.linear_threshold  # or self._choose_linear_threshold(data)
        return SymmetricalLogScale(None, linthresh=linthresh)

    def to_color_norm(self) -> plt_util.ColorNormArg:
        linthresh = self.linear_threshold  # or self._choose_linear_threshold(data)
        return SymLogNorm(linthresh)

    def to_name_fragment_part(self) -> str:
        if self.linear_threshold is None:
            return self.scale_key
        return f"{self.scale_key}{parse_util.SUBARG_DELIM}{self.linear_threshold}"

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
