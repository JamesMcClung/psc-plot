import math

import matplotlib.pyplot as plt
import numpy as np
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


def _get_multiplier_exponent(lower: float, upper: float) -> int:
    """The power of ten that matplotlib would factor out of tick labels spanning `lower` to `upper`. 0 means none."""
    largest = max(abs(lower), abs(upper))
    if largest == 0:
        return 0

    exponent = math.floor(math.log10(largest))
    lower_limit, upper_limit = plt.rcParams["axes.formatter.limits"]
    return 0 if lower_limit < exponent < upper_limit else exponent


def move_cbar_multiplier_to_label(cbar: Colorbar) -> int:
    """Factor a fixed power of ten out of the colorbar's tick labels and return it (0 if none), so the caller can
    put it in the label instead of matplotlib floating it above the bar, past the axes' top edge."""
    exponent = _get_multiplier_exponent(*cbar.mappable.get_clim())
    if exponent == 0:
        return 0

    # Equal power limits pin the exponent.
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_powerlimits((exponent, exponent))
    cbar.formatter = formatter
    cbar.ax.yaxis.get_offset_text().set_visible(False)

    return exponent


# From linear sRGB to the cone responses OKLab is built on, and from their cube roots to OKLab itself.
# See https://bottosson.github.io/posts/oklab/.
_LINEAR_SRGB_TO_LMS = np.array(
    [
        [0.4122214708, 0.5363325363, 0.0514459929],
        [0.2119034982, 0.6806995451, 0.1073969566],
        [0.0883024619, 0.2817188376, 0.6299787005],
    ]
)
_LMS_ROOT_TO_OKLAB = np.array(
    [
        [0.2104542553, 0.7936177850, -0.0040720468],
        [1.9779984951, -2.4285922050, 0.4505937099],
        [0.0259040371, 0.7827717662, -0.8086757660],
    ]
)


def _srgb_to_oklab(rgb: np.ndarray) -> np.ndarray:
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return np.cbrt(linear @ _LINEAR_SRGB_TO_LMS.T) @ _LMS_ROOT_TO_OKLAB.T


def _oklab_to_srgb(lab: np.ndarray) -> np.ndarray:
    linear = (lab @ np.linalg.inv(_LMS_ROOT_TO_OKLAB).T) ** 3 @ np.linalg.inv(_LINEAR_SRGB_TO_LMS).T
    linear = np.clip(linear, 0.0, 1.0)  # the opposite of an in-gamut color needn't be in gamut
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)


def get_opposite_color(rgba: np.ndarray) -> tuple[float, float, float]:
    """The opposite of the average of the given colors (of shape `(..., 4)`), in OKLab: lightness mirrored
    about the middle and hue turned half way round. OKLab being perceptually uniform, the average is one a
    person would agree with, and the opposite is about as far from it as it looks."""
    lightness, a, b = _srgb_to_oklab(rgba.reshape(-1, 4)[:, :3]).mean(axis=0)
    r, g, b = _oklab_to_srgb(np.array([1.0 - lightness, -a, -b]))
    return (float(r), float(g), float(b))


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
