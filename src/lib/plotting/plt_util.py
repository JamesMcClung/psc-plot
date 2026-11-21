import math

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backend_bases import RendererBase
from matplotlib.colorbar import Colorbar
from matplotlib.colorizer import _ScalarMappable
from matplotlib.ticker import ScalarFormatter


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


def update_shared_cbar(mappables: list[_ScalarMappable], boundss: list[tuple[float, float]]):
    """Give every mappable the same color limits and colormap, spanning all their bounds, so one colorbar keys
    them all."""
    lower = min(lower for lower, _ in boundss)
    upper = max(upper for _, upper in boundss)
    for mappable in mappables:
        update_cbar(mappable, data_min_override=lower, data_max_override=upper)


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
    cbar.long_axis.get_offset_text().set_visible(False)

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


_CANDIDATE_LEVELS = np.linspace(0.0, 1.0, 5)
_CANDIDATES = np.stack(np.meshgrid(_CANDIDATE_LEVELS, _CANDIDATE_LEVELS, _CANDIDATE_LEVELS, indexing="ij"), axis=-1).reshape(-1, 3)
"""sRGB colors to choose among: a grid through the whole gamut, its corners (black, white, primaries,
secondaries) included."""
_CANDIDATES_OKLAB = _srgb_to_oklab(_CANDIDATES)
_NEUTRALS = (0, len(_CANDIDATES) - 1)
"""The indices of black and white among `_CANDIDATES`."""
NEUTRAL_PREFERENCE = 1.1
"""A color is picked over black or white only if it's this many times as far."""


def get_contrasting_color(rgba: np.ndarray) -> tuple[float, float, float]:
    """The color that stands out most against all the given colors (of shape `(..., 4)`): of `_CANDIDATES`, the one
    whose least distance to any of them, in OKLab, is greatest. OKLab being perceptually uniform, distance there is
    difference as a person sees it. Over a white background that's black, and over black, white; over mid-tones,
    where neither stands out much, it's a saturated color, if clearly farther (`NEUTRAL_PREFERENCE`)."""
    beneath = np.unique(_srgb_to_oklab(rgba.reshape(-1, 4)[:, :3]).round(4), axis=0)
    distances = np.linalg.norm(_CANDIDATES_OKLAB[:, None, :] - beneath[None, :, :], axis=-1).min(axis=1)
    best = int(np.argmax(distances))
    neutral = max(_NEUTRALS, key=lambda i: distances[i])
    if distances[best] < NEUTRAL_PREFERENCE * distances[neutral]:
        best = neutral  # a hue barely farther than black or white just looks odd
    r, g, b = _CANDIDATES[best]
    return (float(r), float(g), float(b))
