"""Text sizes. Set on each artist where it's made, never through rcParams: tests (and users) may run under a
style context that resets rcParams."""

from matplotlib import pyplot as plt
from matplotlib.font_manager import FontProperties

TEXT_SCALE = 2.0
"""All text but tick labels is this many times matplotlib's default size."""


def scaled_font_size(rc_key: str) -> float:
    """`TEXT_SCALE` times the size, in points, that `rc_key` (e.g. `"axes.titlesize"`) gives text by default."""
    return FontProperties(size=plt.rcParams[rc_key]).get_size_in_points() * TEXT_SCALE
