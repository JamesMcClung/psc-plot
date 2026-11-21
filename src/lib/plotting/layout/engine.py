"""Places every plot area and colorbar, once per figure.

Everything is plain arithmetic in inches: measure how far each panel's decorations reach past its plot area,
take each row's and column's largest, size the plot areas (from `--figsize` or the auto rules), and stack it
all up. Tick labels depend on the plot areas' sizes, so it repeats measure -> place until nothing moves. It never
runs again after the figure is built, so plot areas never move between frames.
"""

import warnings
from dataclasses import dataclass

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.plotting.grid import AxesIdx, Grid
from lib.plotting.layout.auto_size import auto_plot_size, is_aspect_locked
from lib.plotting.layout.geometry import Box, Margins, even_figure_size, sizes_close
from lib.plotting.layout.measure import ColorbarDecorations, PanelDecorations, measure_panel, measure_text_height
from lib.plotting.layout.options import LayoutOptions

FIGURE_PAD = 0.1
"""Inches of space around everything in the figure."""
PANEL_GAP = 0.25
"""Inches between neighboring panels' decorations, unless they sit flush."""
COLORBAR_PAD = 0.1
"""Inches between a colorbar and whatever is to its left."""
COLORBAR_THICKNESS = 0.25
COLORBAR_MIN_GAP_FRACTION = 0.1
"""A colorbar is shorter than its panel by at least this fraction of the panel at each end."""
MIN_PLOT_SIDE = 0.5
"""Inches: a too-small `--figsize` can't shrink a plot area below this."""
MAX_LAYOUT_PASSES = 4


@dataclass(frozen=True)
class Layout:
    fig_width: float
    fig_height: float
    plot_boxes: dict[AxesIdx, Box]
    colorbar_boxes: dict[Axes, Box]
    suptitle_top: float
    """Inches from the figure's bottom to the suptitle's top."""
    shortfall: float = 0.0
    """Inches by which `--figsize` was too small for the smallest plot area, which was enlarged to `MIN_PLOT_SIDE`."""


def _panel_right_margin(decorations: PanelDecorations, axes_right: float) -> float:
    right = axes_right
    for cbar in decorations.colorbars:
        right += COLORBAR_PAD + COLORBAR_THICKNESS + cbar.margins.right
    return right


def _panel_margins(decorations: PanelDecorations, plot_height: float, axes_right: float) -> Margins:
    """Everything outside the plot area, colorbars included. Colorbars start past `axes_right`, the widest axes
    decorations in the panel's column."""
    axes = decorations.axes_margins
    gap = COLORBAR_MIN_GAP_FRACTION * plot_height
    top = max([axes.top, *(cbar.margins.top - gap for cbar in decorations.colorbars)])
    bottom = max([axes.bottom, *(cbar.margins.bottom - gap for cbar in decorations.colorbars)])
    return Margins(left=axes.left, right=_panel_right_margin(decorations, axes_right), bottom=bottom, top=top)


def _plot_sizes(grid: Grid, options: LayoutOptions, cols: list[int], rows: list[int], col_margins: float, row_margins: float) -> tuple[dict[AxesIdx, tuple[float, float]], float]:
    """Each panel's plot-area size: the auto size, scaled to fit any fixed side of the figure. Also returns how many
    inches short of `MIN_PLOT_SIDE` a fixed side left the smallest plot area (0 if none)."""
    dpi = options.dpi
    auto = {loc: auto_plot_size(infos, dpi) for loc, infos in grid.infos.items()}
    locked = {loc: is_aspect_locked(infos) for loc, infos in grid.infos.items()}
    sizes = dict(auto)

    fixed_width, fixed_height = options.figsize.width, options.figsize.height

    # A fixed side is split among the columns (rows) in proportion to their auto sizes: a uniform scale.
    if fixed_width is not None:
        auto_widths = sum(max(auto[loc][0] for loc in auto if loc[0] == col) for col in cols)
        sx = max(fixed_width - col_margins, 0.0) / auto_widths  # no room at all leaves plot areas to the snap below
        sizes = {loc: (w * sx, h * sx if locked[loc] else h) for loc, (w, h) in sizes.items()}

    if fixed_height is not None:
        auto_heights = sum(max(sizes[loc][1] for loc in sizes if loc[1] == row) for row in rows)
        sy = max(fixed_height - row_margins, 0.0) / max(auto_heights, 1e-9)
        scaled = {}
        for loc, (w, h) in sizes.items():
            if not locked[loc]:
                scaled[loc] = (w, h * sy)
            else:
                # Keeping its aspect, a locked plot area may only grow if no fixed width holds it back.
                s = min(1.0, sy) if fixed_width is not None else sy
                scaled[loc] = (w * s, h * s)
        sizes = scaled

    too_small = {loc: (w, h) for loc, (w, h) in sizes.items() if min(w, h) < MIN_PLOT_SIDE - 1e-9}
    shortfall = max((MIN_PLOT_SIDE - min(w, h) for w, h in too_small.values()), default=0.0)
    for loc, (w, h) in too_small.items():
        if locked[loc]:
            aw, ah = auto[loc]  # its shape, even if the scaling above shrank it to nothing
            s = MIN_PLOT_SIDE / min(aw, ah)
            sizes[loc] = (aw * s, ah * s)
        else:
            sizes[loc] = (max(w, MIN_PLOT_SIDE), max(h, MIN_PLOT_SIDE))

    return sizes, shortfall


def compute_layout(grid: Grid, options: LayoutOptions, decorations: dict[AxesIdx, PanelDecorations], suptitle_height: float) -> Layout:
    cols = sorted({loc[0] for loc in grid.infos})
    rows = sorted({loc[1] for loc in grid.infos})

    def row_flush_below(row: int) -> bool:
        return row in grid.flush_row_boundaries

    # Margins, first with the auto heights; colorbar gaps depend on the plot heights only weakly, so recompute after.
    def margins_for(sizes: dict[AxesIdx, tuple[float, float]]) -> dict[AxesIdx, Margins]:
        margins = {}
        axes_right = {col: max(deco.axes_margins.right for loc, deco in decorations.items() if loc[0] == col) for col in cols}
        for loc, deco in decorations.items():
            m = _panel_margins(deco, sizes[loc][1], axes_right[loc[0]])
            # Panels in a stack sit flush, so their facing edges reserve nothing.
            col, row = loc
            if row_flush_below(row):
                m = Margins(m.left, m.right, 0.0, m.top)
            if row_flush_below(row - 1):
                m = Margins(m.left, m.right, m.bottom, 0.0)
            margins[loc] = m
        return margins

    def totals(margins: dict[AxesIdx, Margins]) -> tuple[dict[int, float], dict[int, float], dict[int, float], dict[int, float], float, float]:
        col_left = {col: max(m.left for loc, m in margins.items() if loc[0] == col) for col in cols}
        col_right = {col: max(m.right for loc, m in margins.items() if loc[0] == col) for col in cols}
        row_top = {row: max(m.top for loc, m in margins.items() if loc[1] == row) for row in rows}
        row_bottom = {row: max(m.bottom for loc, m in margins.items() if loc[1] == row) for row in rows}
        col_fixed = 2 * FIGURE_PAD + sum(col_left.values()) + sum(col_right.values()) + PANEL_GAP * (len(cols) - 1)
        row_gaps = sum(0.0 if row_flush_below(row) else PANEL_GAP for row in rows[:-1])
        suptitle_room = suptitle_height + FIGURE_PAD if suptitle_height else 0.0
        row_fixed = 2 * FIGURE_PAD + suptitle_room + sum(row_top.values()) + sum(row_bottom.values()) + row_gaps
        return col_left, col_right, row_top, row_bottom, col_fixed, row_fixed

    auto = {loc: auto_plot_size(infos, options.dpi) for loc, infos in grid.infos.items()}
    margins = margins_for(auto)
    *_, col_fixed, row_fixed = totals(margins)
    sizes, shortfall = _plot_sizes(grid, options, cols, rows, col_fixed, row_fixed)
    margins = margins_for(sizes)
    col_left, col_right, row_top, row_bottom, col_fixed, row_fixed = totals(margins)

    col_width = {col: max(sizes[loc][0] for loc in sizes if loc[0] == col) for col in cols}
    # Colorbars down a column line up, past the widest axes decorations in it.
    col_axes_right = {col: max(deco.axes_margins.right for loc, deco in decorations.items() if loc[0] == col) for col in cols}
    row_height = {row: max(sizes[loc][1] for loc in sizes if loc[1] == row) for row in rows}

    content_width = col_fixed + sum(col_width.values())
    content_height = row_fixed + sum(row_height.values())
    fig_width = max(content_width, options.figsize.width or 0.0)
    fig_height = max(content_height, options.figsize.height or 0.0)
    fig_width, fig_height = even_figure_size(fig_width, fig_height, options.dpi)

    # Any slack (a fixed side the content doesn't fill, or rounding) is split evenly around the content.
    x_offset = (fig_width - content_width) / 2
    y_offset = (fig_height - content_height) / 2
    suptitle_top = fig_height - y_offset - FIGURE_PAD

    col_x0 = {}
    x = x_offset + FIGURE_PAD
    for col in cols:
        col_x0[col] = x + col_left[col]
        x += col_left[col] + col_width[col] + col_right[col] + PANEL_GAP

    row_y1 = {}
    y = fig_height - y_offset - FIGURE_PAD - (suptitle_height + FIGURE_PAD if suptitle_height else 0.0)
    for row in rows:
        row_y1[row] = y - row_top[row]
        y -= row_top[row] + row_height[row] + row_bottom[row] + (0.0 if row_flush_below(row) else PANEL_GAP)

    plot_boxes = {}
    colorbar_boxes = {}
    for loc, (w, h) in sizes.items():
        col, row = loc
        x0 = col_x0[col] + (col_width[col] - w) / 2
        y1 = row_y1[row] - (row_height[row] - h) / 2
        box = Box(x0, y1 - h, w, h)
        plot_boxes[loc] = box

        deco = decorations[loc]
        cbar_x = col_x0[col] + col_width[col] + col_axes_right[col] + COLORBAR_PAD
        cbar_height = (1 - 2 * COLORBAR_MIN_GAP_FRACTION) * h
        for cbar, cbar_deco in zip(grid.panels[loc].colorbars, deco.colorbars):
            colorbar_boxes[cbar.ax] = Box(cbar_x, box.y0 + (h - cbar_height) / 2, COLORBAR_THICKNESS, cbar_height)
            cbar_x += COLORBAR_THICKNESS + cbar_deco.margins.right + COLORBAR_PAD

    return Layout(fig_width, fig_height, plot_boxes, colorbar_boxes, suptitle_top, shortfall)


def apply_layout(fig: Figure, grid: Grid, layout: Layout):
    fig.set_size_inches(layout.fig_width, layout.fig_height)
    for loc, box in layout.plot_boxes.items():
        grid.panels[loc].axes[0].set_position(box.to_figure_fraction(layout.fig_width, layout.fig_height))
    for cax, box in layout.colorbar_boxes.items():
        cax.set_position(box.to_figure_fraction(layout.fig_width, layout.fig_height))
    grid.suptitle.set_y(layout.suptitle_top / layout.fig_height)
    grid.suptitle.set_va("top")


def _layouts_match(a: Layout, b: Layout, dpi: float) -> bool:
    boxes = [(a.plot_boxes, b.plot_boxes), (a.colorbar_boxes, b.colorbar_boxes)]
    return sizes_close(a.fig_width, b.fig_width, dpi) and sizes_close(a.fig_height, b.fig_height, dpi) and all(sizes_close(getattr(box, attr), getattr(other[key], attr), dpi) for mine, other in boxes for key, box in mine.items() for attr in ("x0", "y0", "width", "height"))


def run_layout(fig: Figure, grid: Grid, options: LayoutOptions):
    """Lay out the figure, once: measure -> place until nothing moves."""
    dpi = options.dpi
    no_decorations = {loc: PanelDecorations(Margins(), [ColorbarDecorations(Margins()) for _ in panel.colorbars]) for loc, panel in grid.panels.items()}
    layout = compute_layout(grid, options, no_decorations, 0.0)

    for _ in range(MAX_LAYOUT_PASSES):
        apply_layout(fig, grid, layout)
        fig.draw_without_rendering()
        grid.adjust_to_draw()
        fig.draw_without_rendering()

        renderer = fig.canvas.get_renderer()
        # Display units are dots at the figure's current dpi, which HiDPI backends scale past `options.dpi`.
        display_dpi = fig.dpi
        decorations = {loc: measure_panel(panel, renderer, display_dpi) for loc, panel in grid.panels.items()}
        new_layout = compute_layout(grid, options, decorations, measure_text_height(grid.suptitle, renderer, display_dpi))
        if _layouts_match(layout, new_layout, dpi):
            break
        layout = new_layout
    else:
        apply_layout(fig, grid, layout)
        fig.draw_without_rendering()
        grid.adjust_to_draw()

    if layout.shortfall > 0:
        warnings.warn(f"--figsize leaves too little room for the plots (short by {layout.shortfall:.2f}in); enlarging the figure so every plot area is at least {MIN_PLOT_SIDE}in a side")
