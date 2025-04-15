import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colorizer import _ScalarMappable


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


def update_title(ax: Axes, var: str, time: float, time_unit: str | None = None):
    maybe_unit = " " + time_unit if time_unit else ""
    ax.set_title(f"{var} ($t={time:.2f}${maybe_unit})")
