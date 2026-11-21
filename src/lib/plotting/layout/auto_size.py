import math

from lib.plotting.plot_info import ImageInfo, PlotInfo, PlotInfo2D, PolarMeshInfo

DEFAULT_PLOT_SIZE = (5.0, 3.75)
"""A plot area's size when nothing in it asks for another, in inches."""
DEFAULT_POLAR_SIZE = 4.5
MIN_DOTS_PER_CELL = 2
"""So every cell of an image is visible."""
MAX_EQUAL_SCALE_RATIO = 2.5
"""Equal x and y scales may make one side at most this much longer than the other: 2, with some wiggle room."""


def _get_equal_scale_aspect(infos: list[PlotInfo2D]) -> float | None:
    """The plot area's height / width that gives x and y the same scale, clamped, or `None` if they shouldn't share one."""
    aspects = set()
    for info in infos:
        x_unit, y_unit = info.dim_units.get(info.x_dim), info.dim_units.get(info.y_dim)
        if not x_unit or x_unit != y_unit:
            return None

        (x_lo, x_hi), (y_lo, y_hi) = info.dim_bounds.get(info.x_dim, (None, None)), info.dim_bounds.get(info.y_dim, (None, None))
        if None in (x_lo, x_hi, y_lo, y_hi) or x_hi == x_lo:
            return None
        aspects.add(abs((y_hi - y_lo) / (x_hi - x_lo)))

    if len(aspects) != 1:
        return None
    return min(max(aspects.pop(), 1 / MAX_EQUAL_SCALE_RATIO), MAX_EQUAL_SCALE_RATIO)


def auto_plot_size(infos: list[PlotInfo], dpi: float) -> tuple[float, float]:
    """The size, in inches, of the plot area that holds `infos` (all of one panel)."""
    if any(isinstance(info, PolarMeshInfo) for info in infos):
        return (DEFAULT_POLAR_SIZE, DEFAULT_POLAR_SIZE)

    infos_2d = [info for info in infos if isinstance(info, PlotInfo2D)]
    aspect = _get_equal_scale_aspect(infos_2d) if infos_2d else None

    if aspect is None:
        width, height = DEFAULT_PLOT_SIZE
    else:
        area = DEFAULT_PLOT_SIZE[0] * DEFAULT_PLOT_SIZE[1]
        width, height = math.sqrt(area / aspect), math.sqrt(area * aspect)

    # Every cell of every image gets at least MIN_DOTS_PER_CELL dots along each side.
    min_width = max((MIN_DOTS_PER_CELL * info.data.shape[1] / dpi for info in infos if isinstance(info, ImageInfo)), default=0.0)
    min_height = max((MIN_DOTS_PER_CELL * info.data.shape[0] / dpi for info in infos if isinstance(info, ImageInfo)), default=0.0)

    if aspect is None:
        return (max(width, min_width), max(height, min_height))

    growth = max(1.0, min_width / width, min_height / height)
    return (width * growth, height * growth)


def is_aspect_locked(infos: list[PlotInfo]) -> bool:
    """Whether the plot area's aspect is fixed by its data (equal x/y scale, or polar), so it scales as a whole."""
    if any(isinstance(info, PolarMeshInfo) for info in infos):
        return True
    infos_2d = [info for info in infos if isinstance(info, PlotInfo2D)]
    return bool(infos_2d) and _get_equal_scale_aspect(infos_2d) is not None
