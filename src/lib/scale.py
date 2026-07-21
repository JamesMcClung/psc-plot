from dataclasses import dataclass, field
from typing import Literal, Self

from matplotlib.colors import Normalize, SymLogNorm
from matplotlib.scale import ScaleBase, SymmetricalLogScale

from lib.parsing import parse_util

type BuiltinAxisScaleKey = Literal["linear", "log"]
SCALES: list[BuiltinAxisScaleKey] = list(BuiltinAxisScaleKey.__value__.__args__)
type AxisScaleArg = BuiltinAxisScaleKey | ScaleBase

type BuiltinColorNormKey = Literal["linear", "log"]
BUILTIN_COLOR_NORM_KEYS: tuple[BuiltinColorNormKey, ...] = BuiltinColorNormKey.__value__.__args__
type ColorNormArg = BuiltinColorNormKey | Normalize

type ScaleKey = Literal["linear", "log", "symlog"]
SCALE_KEYS: tuple[ScaleKey, ...] = ScaleKey.__value__.__args__


@dataclass(frozen=True, unsafe_hash=True)
class Scale:
    scale_key: ScaleKey

    def __init_subclass__(cls):
        SCALE_TYPES.append(cls)

    def to_axis_scale(self) -> AxisScaleArg:
        return self.scale_key

    def to_color_norm(self) -> ColorNormArg:
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


@dataclass(frozen=True, unsafe_hash=True)
class LinearScale(Scale):
    scale_key: ScaleKey = field(init=False, default="linear")


@dataclass(frozen=True, unsafe_hash=True)
class LogScale(Scale):
    scale_key: ScaleKey = field(init=False, default="log")


LINEAR_THRESHOLD_ARG_FORMAT = "linear_threshold"


@dataclass(frozen=True, unsafe_hash=True)
class SymLogScale(Scale):
    linear_threshold: float
    scale_key: ScaleKey = field(init=False, default="symlog")

    def to_axis_scale(self) -> AxisScaleArg:
        linthresh = self.linear_threshold  # or self._choose_linear_threshold(data)
        return SymmetricalLogScale(None, linthresh=linthresh)

    def to_color_norm(self) -> ColorNormArg:
        linthresh = self.linear_threshold  # or self._choose_linear_threshold(data)
        return SymLogNorm(linthresh)

    def to_name_fragment_part(self) -> str:
        if self.linear_threshold is None:
            return self.scale_key
        return f"{self.scale_key}{parse_util.SUBARG_DELIM}{self.linear_threshold}"

    @classmethod
    def to_argparse_format(cls) -> str:
        return f"{cls.scale_key}[{parse_util.SUBARG_DELIM}{LINEAR_THRESHOLD_ARG_FORMAT}]"

    @classmethod
    def try_from_argparse_format(cls, arg: str) -> Self | None:
        scale_key_arg, linear_threshold_arg = parse_util.parse_optional_assignment(arg, cls.to_argparse_format(), delim=parse_util.SUBARG_DELIM)

        if scale_key_arg != cls.scale_key:
            return None

        linear_threshold = parse_util.parse_optional_number(linear_threshold_arg, LINEAR_THRESHOLD_ARG_FORMAT, float)

        return cls(linear_threshold)

    def __eq__(self, value):
        return isinstance(value, SymLogScale) and value.scale_key == self.scale_key and self.linear_threshold == value.linear_threshold
