import math

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.colorbar import Colorbar
from matplotlib.colorizer import _ScalarMappable
from matplotlib.ticker import ScalarFormatter

from lib.data.data_with_attrs import ListMetadata, Metadata


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


def get_multiplier_exponent(lower: float, upper: float) -> int:
    """The power of ten that matplotlib would factor out of tick labels spanning `lower` to `upper`. 0 means none."""
    largest = max(abs(lower), abs(upper))
    if largest == 0:
        return 0

    exponent = math.floor(math.log10(largest))
    smallest_plain_exponent, largest_plain_exponent = plt.rcParams["axes.formatter.limits"]

    if exponent <= smallest_plain_exponent or exponent >= largest_plain_exponent:
        return exponent
    return 0


def move_cbar_multiplier_to_label(cbar: Colorbar) -> int:
    """Factor a fixed power of ten out of the colorbar's tick labels and return it, so the caller can name it
    in the label instead. 0 means the labels were left alone. Only makes sense for a linear color scale.

    Matplotlib would otherwise float the multiplier above the bar, where it sticks out past the top edge and
    forces constrained layout to reserve room there -- fatal when the axes above is supposed to sit flush.
    """
    exponent = get_multiplier_exponent(*cbar.mappable.get_clim())
    if exponent == 0:
        return 0

    # Equal power limits are matplotlib's way of pinning the exponent, rather than letting the formatter pick
    # one from whatever ticks it is given.
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_powerlimits((exponent, exponent))
    cbar.formatter = formatter
    cbar.ax.yaxis.get_offset_text().set_visible(False)

    return exponent


def get_default_cbar_label_left(cbar: Colorbar, renderer: RendererBase) -> float:
    """Where matplotlib puts the left edge of a vertical colorbar's label, in display coordinates: a label pad
    past its tick labels, or past the bar itself if they don't reach any further.

    Measures the tick labels where they were last drawn, so the figure must already have been laid out.
    """
    ax = cbar.ax
    rights = [ax.get_window_extent(renderer).x1]
    rights += [label.get_window_extent(renderer).x1 for label in ax.get_yticklabels() if label.get_visible()]
    return max(rights) + ax.yaxis.labelpad * ax.get_figure(root=True).dpi / 72


def update_title(ax: Axes, metadata: Metadata, cut_labels: list[str]):
    title_base = ""
    cut_labels_str = ", ".join(cut_labels)

    if isinstance(metadata, ListMetadata):
        if metadata.subject:
            title_base = f"${metadata.subject}$"
    elif metadata.active_key:
        title_base = metadata.active_var_info.to_axis_label()

    if title_base and cut_labels_str:
        cut_labels_str = f" ({cut_labels_str})"

    ax.set_title(title_base + cut_labels_str)
