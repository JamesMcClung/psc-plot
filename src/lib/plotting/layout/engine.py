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
from lib.plotting.layout.auto_size import auto_plot_sizes, is_aspect_locked
from lib.plotting.layout.geometry import Box, Margins, even_figure_size, sizes_close
from lib.plotting.layout.measure import ColorbarDecorations, PanelDecorations, measure_panel, measure_text_height, widest_frame_texts
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
"""Inches: a too-small `--figsize` can't shrink a plot area below this, nor below what its tick labels need."""
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
    """Inches by which a fixed side of `--figsize` left a plot area short of its minimum size, the most for any."""


def _panel_right_margin(decorations: PanelDecorations, axes_right: float) -> float:
    right = axes_right
    for cbar in decorations.colorbars:
        right += COLORBAR_PAD + COLORBAR_THICKNESS + cbar.margins.right
    return right


def _colorbar_gaps(decorations: ColorbarDecorations, plot_height: float) -> tuple[float, float]:
    """How much shorter than its panel a colorbar is at the top and bottom: room for its texts, and at least
    `COLORBAR_MIN_GAP_FRACTION` of the panel."""
    min_gap = COLORBAR_MIN_GAP_FRACTION * plot_height
    return (max(min_gap, decorations.margins.top), max(min_gap, decorations.margins.bottom))


def _min_height_for_colorbar(decorations: ColorbarDecorations) -> float:
    """The least plot height whose colorbar, less its gaps (see `_colorbar_gaps`), is `min_length` long."""
    need, top, bottom = decorations.min_length, decorations.margins.top, decorations.margins.bottom
    if need <= 0:
        return 0.0
    f = COLORBAR_MIN_GAP_FRACTION
    # Each gap is the larger of a fraction of the height and its text, so every combination must leave room.
    return max(need / (1 - 2 * f), (need + top) / (1 - f), (need + bottom) / (1 - f), need + top + bottom)


def _min_plot_sizes(decorations: dict[AxesIdx, PanelDecorations]) -> dict[AxesIdx, tuple[float, float]]:
    """Each panel's least plot-area size: `MIN_PLOT_SIDE`, and room for two tick labels on each axis and colorbar.
    Taken per column (widths) and per row (heights), so panels sharing an edge keep sharing it."""
    own = {loc: (max(MIN_PLOT_SIDE, deco.min_plot_size[0]), max(MIN_PLOT_SIDE, deco.min_plot_size[1], *(_min_height_for_colorbar(cbar) for cbar in deco.colorbars))) for loc, deco in decorations.items()}
    col_width = {col: max(w for (c, _), (w, _) in own.items() if c == col) for col, _ in own}
    row_height = {row: max(h for (_, r), (_, h) in own.items() if r == row) for _, row in own}
    return {(col, row): (col_width[col], row_height[row]) for col, row in own}


def _panel_margins(decorations: PanelDecorations, plot_height: float, axes_right: float) -> Margins:
    """Everything outside the plot area, colorbars included. Colorbars start past `axes_right`, the widest axes
    decorations in the panel's column."""
    axes = decorations.axes_margins
    # A colorbar's texts fit in its gaps, so colorbars never reach past their panel's top or bottom.
    top, bottom = axes.top, axes.bottom
    return Margins(left=axes.left, right=_panel_right_margin(decorations, axes_right), bottom=bottom, top=top)


def _plot_sizes(grid: Grid, options: LayoutOptions, cols: list[int], rows: list[int], col_margins: float, row_margins: float, min_sizes: dict[AxesIdx, tuple[float, float]]) -> tuple[dict[AxesIdx, tuple[float, float]], float]:
    """Each panel's plot-area size: the auto size, scaled to fit any fixed side of the figure, and grown to at least
    `min_sizes`. Also returns how many inches short of its minimum a fixed side left a plot area, the most for any
    (0 if none): growing past an auto side is just auto sizing."""
    dpi = options.dpi
    auto = auto_plot_sizes(grid.infos, dpi)
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

    shortfall = 0.0
    for loc, (w, h) in sizes.items():
        min_w, min_h = min_sizes[loc]
        short_w, short_h = min_w - w, min_h - h
        if max(short_w, short_h) <= 1e-9:
            continue
        # A locked plot area grows as a whole, so a fixed side on either is to blame.
        blamed = (short_w, short_h) if locked[loc] else (short_w if fixed_width is not None else 0.0, short_h if fixed_height is not None else 0.0)
        if fixed_width is not None or fixed_height is not None:
            shortfall = max(shortfall, *blamed)
        if locked[loc]:
            aw, ah = auto[loc]  # its shape, even if the scaling above shrank it to nothing
            s = max(min_w / aw, min_h / ah) if (w < min_w - 1e-9 or h < min_h - 1e-9) else 1.0
            sizes[loc] = (max(w, aw * s), max(h, ah * s)) if s == 1.0 else (aw * s, ah * s)
        else:
            sizes[loc] = (max(w, min_w), max(h, min_h))

    return sizes, shortfall


def compute_layout(grid: Grid, options: LayoutOptions, decorations: dict[AxesIdx, PanelDecorations], suptitle_height: float) -> Layout:
    cols = sorted({loc[0] for loc in grid.infos})
    rows = sorted({loc[1] for loc in grid.infos})

    def row_flush_below(row: int) -> bool:
        return row in grid.flush_row_boundaries

    def col_flush_right(col: int) -> bool:
        return col in grid.flush_col_boundaries

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
            # Likewise panels sharing a y axis.
            if col_flush_right(col):
                m = Margins(m.left, 0.0, m.bottom, m.top)
            if col_flush_right(col - 1):
                m = Margins(0.0, m.right, m.bottom, m.top)
            margins[loc] = m
        return margins

    def totals(margins: dict[AxesIdx, Margins]) -> tuple[dict[int, float], dict[int, float], dict[int, float], dict[int, float], float, float]:
        col_left = {col: max(m.left for loc, m in margins.items() if loc[0] == col) for col in cols}
        col_right = {col: max(m.right for loc, m in margins.items() if loc[0] == col) for col in cols}
        row_top = {row: max(m.top for loc, m in margins.items() if loc[1] == row) for row in rows}
        row_bottom = {row: max(m.bottom for loc, m in margins.items() if loc[1] == row) for row in rows}
        col_gaps = sum(0.0 if col_flush_right(col) else PANEL_GAP for col in cols[:-1])
        col_fixed = 2 * FIGURE_PAD + sum(col_left.values()) + sum(col_right.values()) + col_gaps
        row_gaps = sum(0.0 if row_flush_below(row) else PANEL_GAP for row in rows[:-1])
        suptitle_room = suptitle_height + FIGURE_PAD if suptitle_height else 0.0
        row_fixed = 2 * FIGURE_PAD + suptitle_room + sum(row_top.values()) + sum(row_bottom.values()) + row_gaps
        return col_left, col_right, row_top, row_bottom, col_fixed, row_fixed

    auto = auto_plot_sizes(grid.infos, options.dpi)
    margins = margins_for(auto)
    *_, col_fixed, row_fixed = totals(margins)
    sizes, shortfall = _plot_sizes(grid, options, cols, rows, col_fixed, row_fixed, _min_plot_sizes(decorations))
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
        x += col_left[col] + col_width[col] + col_right[col] + (0.0 if col_flush_right(col) else PANEL_GAP)

    row_y1 = {}
    y = fig_height - y_offset - FIGURE_PAD - (suptitle_height + FIGURE_PAD if suptitle_height else 0.0)
    for row in rows:
        row_y1[row] = y - row_top[row]
        y -= row_top[row] + row_height[row] + row_bottom[row] + (0.0 if row_flush_below(row) else PANEL_GAP)

    plot_boxes = {}
    colorbar_boxes = {}
    for loc, (w, h) in sizes.items():
        col, row = loc
        # Centered in its column and row, unless it sits flush against a neighbor: then it hugs that edge.
        x_slack, y_slack = col_width[col] - w, row_height[row] - h
        x0 = col_x0[col] + (x_slack if col_flush_right(col) else 0.0 if col_flush_right(col - 1) else x_slack / 2)
        y1 = row_y1[row] - (y_slack if row_flush_below(row) else 0.0 if row_flush_below(row - 1) else y_slack / 2)
        box = Box(x0, y1 - h, w, h)
        plot_boxes[loc] = box

        deco = decorations[loc]
        cbar_x = col_x0[col] + col_width[col] + col_axes_right[col] + COLORBAR_PAD
        for cbar, cbar_deco in zip(grid.panels[loc].colorbars, deco.colorbars):
            gap_top, gap_bottom = _colorbar_gaps(cbar_deco, h)
            colorbar_boxes[cbar.ax] = Box(cbar_x, box.y0 + gap_bottom, COLORBAR_THICKNESS, h - gap_top - gap_bottom)
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

    # Lay out with every text at its widest on any frame, so no frame's text needs more room than it has.
    widest = widest_frame_texts(grid, fig.canvas.get_renderer())
    frame_0 = {text: text.get_text() for text in widest}
    for text, string in widest.items():
        text.set_text(string)

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

    for text, string in frame_0.items():
        text.set_text(string)

    if layout.shortfall > 0:
        warnings.warn(f"--figsize leaves too little room for the plots (short by {layout.shortfall:.2f}in); enlarging the figure so every plot area is at least {MIN_PLOT_SIDE}in a side and fits two tick labels on each axis")
