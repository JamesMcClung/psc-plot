import math

from lib.plotting.plot_info import ImageInfo, PlotInfo, PlotInfo2D, PolarMeshInfo

DEFAULT_PLOT_SIZE = (5.0, 3.75)
"""A plot area's size when nothing in it asks for another, in inches."""
DEFAULT_POLAR_SIZE = 4.5
MIN_DOTS_PER_CELL = 2
"""So every cell of an image is visible."""
MAX_EQUAL_SCALE_RATIO = 2.5
"""Equal x and y scales may make one side at most this much longer than the other (2, with some wiggle room). Past
it, equal scale is given up entirely."""


def _get_equal_scale_aspect(infos: list[PlotInfo2D]) -> float | None:
    """The plot area's height / width that gives x and y the same scale, or `None` if they shouldn't share one: their
    units differ, or the plot area would be more than `MAX_EQUAL_SCALE_RATIO` times longer one way than the other."""
    aspects = []
    for info in infos:
        x_unit, y_unit = info.dim_units.get(info.x_dim), info.dim_units.get(info.y_dim)
        if not x_unit or x_unit != y_unit:
            return None

        (x_lo, x_hi), (y_lo, y_hi) = info.dim_bounds.get(info.x_dim, (None, None)), info.dim_bounds.get(info.y_dim, (None, None))
        if None in (x_lo, x_hi, y_lo, y_hi) or x_hi == x_lo:
            return None
        aspects.append(abs((y_hi - y_lo) / (x_hi - x_lo)))

    aspect = aspects[0]
    if not all(math.isclose(other, aspect) for other in aspects):
        return None  # a ratio, so compared relatively, not in dots like `sizes_close`
    if not 1 / MAX_EQUAL_SCALE_RATIO <= aspect <= MAX_EQUAL_SCALE_RATIO:
        return None  # too lopsided: each side is sized on its own instead
    return aspect


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


def _equal_scale_spans(infos: list[PlotInfo]) -> tuple[float, float, str] | None:
    """For a panel with equal x and y scales (not polar), how far its axes span, and their unit; else `None`."""
    if any(isinstance(info, PolarMeshInfo) for info in infos):
        return None
    infos_2d = [info for info in infos if isinstance(info, PlotInfo2D)]
    if not infos_2d or _get_equal_scale_aspect(infos_2d) is None:
        return None
    x_span = max(info.dim_bounds[info.x_dim][1] for info in infos_2d) - min(info.dim_bounds[info.x_dim][0] for info in infos_2d)
    y_span = max(info.dim_bounds[info.y_dim][1] for info in infos_2d) - min(info.dim_bounds[info.y_dim][0] for info in infos_2d)
    return abs(x_span), abs(y_span), infos_2d[0].dim_units[infos_2d[0].x_dim]


def _min_scale(infos: list[PlotInfo], x_span: float, y_span: float, dpi: float) -> float:
    """The least inches per unit giving every cell of the panel's images `MIN_DOTS_PER_CELL` dots along each side."""
    images = [info for info in infos if isinstance(info, ImageInfo)]
    return max((MIN_DOTS_PER_CELL * max(info.data.shape[1] / x_span, info.data.shape[0] / y_span) / dpi for info in images), default=0.0)


def auto_plot_sizes[L](infos_per_panel: dict[L, list[PlotInfo]], dpi: float) -> dict[L, tuple[float, float]]:
    """Every panel's auto size. Panels with equal x and y scales in the same unit also share one scale (inches per
    unit) across the figure, so ones spanning the same extent come out the same size and can share axes: the
    largest scale keeping each within the default area, raised if any image needs more for its minimum dots."""
    sizes = {loc: auto_plot_size(infos, dpi) for loc, infos in infos_per_panel.items()}

    spans = {loc: spans for loc, infos in infos_per_panel.items() if (spans := _equal_scale_spans(infos))}
    area = DEFAULT_PLOT_SIZE[0] * DEFAULT_PLOT_SIZE[1]
    for unit in {unit for _, _, unit in spans.values()}:
        group = {loc: (x_span, y_span) for loc, (x_span, y_span, u) in spans.items() if u == unit}
        default_scale = min(math.sqrt(area / (x_span * y_span)) for x_span, y_span in group.values())
        min_scale = max(_min_scale(infos_per_panel[loc], x_span, y_span, dpi) for loc, (x_span, y_span) in group.items())
        scale = max(default_scale, min_scale)
        for loc, (x_span, y_span) in group.items():
            sizes[loc] = (scale * x_span, scale * y_span)
    return sizes


def is_aspect_locked(infos: list[PlotInfo]) -> bool:
    """Whether the plot area's aspect is fixed by its data (equal x/y scale, or polar), so it scales as a whole."""
    if any(isinstance(info, PolarMeshInfo) for info in infos):
        return True
    infos_2d = [info for info in infos if isinstance(info, PlotInfo2D)]
    return bool(infos_2d) and _get_equal_scale_aspect(infos_2d) is not None
