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


def format_label(metadata: Metadata) -> str:
    """Format a label for the dependent variable: ``$display$`` or ``$display\\;[unit]$``."""
    if metadata.unit_latex:
        return f"${metadata.display_latex}\\;[{metadata.unit_latex}]$"
    return f"${metadata.display_latex}$"


def update_title(ax: Axes, metadata: Metadata, cut_labels: list[str]):
    cut_labels_str = ", ".join(cut_labels)
    if cut_labels_str:
        cut_labels_str = f" ({cut_labels_str})"
    ax.set_title(f"{format_label(metadata)}{cut_labels_str}")


def get_dim(key: str, metadata: Metadata):
    """Look up a Dimension for `key`, preferring metadata.dims and falling back to DIM_DEFAULTS."""
    return metadata.dims[key]


def get_axis_label(key: str, metadata: Metadata) -> str:
    return get_dim(key, metadata).to_axis_label()


def get_var_bounds(data: "Field") -> tuple[float, float]:
    from lib.data.data_with_attrs import Field as FieldType
    import dask
    import numpy as np
    active = data.active_data
    if hasattr(active, "data") and hasattr(active.data, "dask"):
        return dask.compute(np.min(active), np.max(active))
    bounds = np.nanquantile(active, [0, 1])
    return (float(bounds[0]), float(bounds[1]))
