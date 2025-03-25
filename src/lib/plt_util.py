import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colorizer import _ScalarMappable


def update_cbar(mappable: _ScalarMappable):
    data = mappable.get_array()
    data_min = data.min()
    data_max = data.max()

    if data_min >= 0:
        cmin = 0
        cmax = data_max
        cmap = "inferno"
    elif data_max <= 0:
        cmin = data_min
        cmax = 0
        cmap = "inferno_r"
    else:
        cmax = max(abs(data.max()), abs(data.min()))
        cmin = -cmax
        cmap = "RdBu_r"

    mappable.set_clim(cmin, cmax)
    mappable.set_cmap(plt.get_cmap(cmap))


def update_title(ax: Axes, var: str, time: float, time_unit: str | None = None):
    maybe_unit = " " + time_unit if time_unit else ""
    ax.set_title(f"{var} ($t={time:.2f}${maybe_unit})")
