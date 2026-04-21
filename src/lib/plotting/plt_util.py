import typing

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colorizer import _ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.scale import ScaleBase

from lib.data.data_with_attrs import Metadata

type BuiltinAxisScaleKey = typing.Literal["linear", "log"]
SCALES: list[BuiltinAxisScaleKey] = list(BuiltinAxisScaleKey.__value__.__args__)
type AxisScaleArg = BuiltinAxisScaleKey | ScaleBase

type BuiltinColorNormKey = typing.Literal["linear", "log"]
BUILTIN_COLOR_NORM_KEYS: tuple[BuiltinColorNormKey, ...] = BuiltinColorNormKey.__value__.__args__
type ColorNormArg = BuiltinColorNormKey | Normalize


def symmetrize_bounds(lower: float, upper: float) -> tuple[float, float]:
    if lower < 0 < upper:
        max_abs = max(abs(lower), abs(upper))
        return (-max_abs, max_abs)
    elif lower == upper:
        return (0.95 * lower, 1.05 * upper)
    else:
        return (lower, upper)


def update_cbar(mappable: _ScalarMappable, *, data_min_override: float | None = None, data_max_override: float | None = None):
    data = mappable.get_array()
    data_min = data.min() if data_min_override is None else data_min_override
    data_max = data.max() if data_max_override is None else data_max_override

    cmin, cmax = symmetrize_bounds(data_min, data_max)

    if cmin >= 0:
        cmap = "inferno"
    elif cmax <= 0:
        cmap = "inferno_r"
    else:
        cmap = "RdBu_r"

    mappable.set_clim(cmin, cmax)
    mappable.set_cmap(plt.get_cmap(cmap))


def update_title(ax: Axes, metadata: Metadata, cut_labels: list[str]):
    cut_labels_str = ", ".join(cut_labels)

    if metadata.var_name is None:
        return ax.set_title(cut_labels_str)

    if cut_labels_str:
        cut_labels_str = f" ({cut_labels_str})"
    return ax.set_title(metadata.active_var_info.to_axis_label() + cut_labels_str)
