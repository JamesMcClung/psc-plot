"""Colorbars shared across, and extended down, panels; horizontal where a row shares y but not one colorbar."""

import pytest
from conftest import _DATA_DIR

from lib.config import PscPlotConfig
from lib.parsing.parse import parse_args
from lib.plotting.layout.geometry import sizes_close
from lib.run.compile import compile_plot_pipeline

DPI = 100.0
ROW_SAME = "pfd hx_fc --copy -i t=0 -v y z --copy hx_fc -i t=-1 -v y z loc=2,1"
STACK_SAME = "pfd hx_fc -i t=-1 --copy -v y z --copy hx_fc -v y z loc=1,2"
STACK_DIFFERENT_TIMES = "pfd hx_fc --copy -i t=0 -v y z --copy hx_fc -i t=-1 -v y z loc=1,2"
ROW_DIFFERENT = "pfd hx_fc -i t=-1 -v y z loc=1,1 -w hy_fc -v y z loc=2,1"
WORKED_EXAMPLE = "pfd hx_fc -i t=-1 -v y z loc=1,1 -w hy_fc -v y z loc=2,1 -w hx_fc -v y z loc=1,2 -w hx_fc -v y z loc=2,2"


def _plot(args: str):
    plot = compile_plot_pipeline(parse_args(args.split()), PscPlotConfig.create_minimal(data_root=_DATA_DIR / "test-2d")).run_plot()
    plot._initialize()
    plot.fig.draw_without_rendering()
    return plot


def _box(ax):
    """`ax`'s box in inches."""
    w, h = ax.get_figure(root=True).get_size_inches()
    pos = ax.get_position()
    return pos.x0 * w, pos.y0 * h, pos.x1 * w, pos.y1 * h


def _colorbars(plot):
    return [(cbar, assignment) for panel in plot.grid.panels.values() for cbar, assignment in zip(panel.colorbars, panel.colorbar_assignments)]


def test_shared_clim_is_union():
    plot = _plot(ROW_SAME)
    [(cbar, assignment)] = _colorbars(plot)
    assert assignment.orientation == "vertical" and set(assignment.keyed) == {(1, 1), (2, 1)}
    images = [image for ax in plot.fig.axes for image in ax.images]
    assert len(images) == 2
    [clim] = {image.get_clim() for image in images}
    for image in images:
        assert clim[0] <= image.get_array().min() and image.get_array().max() <= clim[1]


def test_extended_bar_spans_stack():
    plot = _plot(STACK_SAME)
    [(cbar, _)] = _colorbars(plot)
    upper, lower = [_box(plot.grid.panels[loc].axes[0]) for loc in [(1, 1), (1, 2)]]
    _, y0, _, y1 = _box(cbar.ax)
    assert lower[1] <= y0 and y1 <= upper[3]
    assert y1 - y0 > (upper[3] - upper[1])  # longer than one panel


def test_stack_with_differing_sublabels_keeps_separate_bars():
    """Stacked panels have no titles, so only their colorbars can say which time each shows."""
    plot = _plot(STACK_DIFFERENT_TIMES)
    bars = _colorbars(plot)
    assert {assignment.keyed for _, assignment in bars} == {((1, 1),), ((1, 2),)}
    labels = [texts.top.get_text() for panel in plot.grid.panels.values() for texts in panel.colorbar_texts]
    assert all("t =" in label for label in labels) and len(set(labels)) == 2


def test_horizontal_bar_above_panel():
    plot = _plot(ROW_DIFFERENT)
    bars = _colorbars(plot)
    assert len(bars) == 2 and all(assignment.orientation == "horizontal" for _, assignment in bars)
    renderer = plot.fig.canvas.get_renderer()
    for cbar, assignment in bars:
        [loc] = assignment.anchors
        px0, _, px1, py1 = _box(plot.grid.panels[loc].axes[0])
        x0, y0, x1, y1 = _box(cbar.ax)
        assert y0 >= py1 and px0 - 1 / DPI <= x0 and x1 <= px1 + 1 / DPI
        [texts] = [texts for texts in plot.grid.panels[loc].colorbar_texts if texts.cbar is cbar]
        assert "\n" not in texts.top.get_text()
        assert texts.top.get_window_extent(renderer).y0 >= cbar.ax.get_window_extent(renderer).y1
        label, bar = texts.top.get_window_extent(renderer), cbar.ax.get_window_extent(renderer)
        assert (label.x0 + label.x1) / 2 == pytest.approx((bar.x0 + bar.x1) / 2, abs=1)  # centered over the bar
        if texts.bottom.get_text():
            assert texts.bottom.get_window_extent(renderer).x0 >= cbar.ax.get_window_extent(renderer).x1
    # The titles sit above the bars.
    for cbar, assignment in bars:
        [loc] = assignment.anchors
        title = plot.grid.panels[loc].axes[0].title
        if title.get_text():
            assert title.get_window_extent(renderer).y0 >= cbar.ax.get_tightbbox(renderer).y1 - 1


def test_users_worked_example_figure():
    plot = _plot(WORKED_EXAMPLE)
    assert plot.grid.flush_col_boundaries == set()
    keyeds = {assignment.keyed for _, assignment in _colorbars(plot)}
    assert keyeds == {((1, 1), (1, 2)), ((2, 1),), ((2, 2),)}
    assert all(assignment.orientation == "vertical" for _, assignment in _colorbars(plot))


def test_row_sharing_one_bar_sits_flush():
    plot = _plot(ROW_SAME)
    assert plot.grid.flush_col_boundaries == {1}
    left, right = [_box(plot.grid.panels[loc].axes[0]) for loc in [(1, 1), (2, 1)]]
    assert sizes_close(left[2], right[0], DPI)


@pytest.mark.parametrize("args", [ROW_SAME, STACK_SAME, STACK_DIFFERENT_TIMES, ROW_DIFFERENT, WORKED_EXAMPLE])
def test_no_ambiguous_colorbar(args: str):
    plot = _plot(args)
    keyed = [loc for _, assignment in _colorbars(plot) for loc in assignment.keyed]
    images = [loc for loc, panel in plot.grid.panels.items() if panel.color_artists]
    assert sorted(keyed) == sorted(images)


def test_panel_with_two_color_quantities_gets_a_bar_each():
    """An image with particles colored by another quantity on top: each keeps its own bar and color limits."""
    plot = _plot("pfd ey_ec -i t=-1 -v y z -w prt.i -i t=-1 -cv y z color=pz loc=1,1")
    bars = _colorbars(plot)
    assert len(bars) == 2
    labels = {texts.top.get_text().split("\n")[0] for panel in plot.grid.panels.values() for texts in panel.colorbar_texts}
    assert any("E_y" in label for label in labels) and any("u_z" in label for label in labels)


def test_panel_with_two_color_quantities_sits_apart():
    plot = _plot("pfd ey_ec -i t=-1 -v y z loc=1,1 -w ey_ec -v y z loc=2,1 -w prt.i -i t=-1 -cv y z color=pz loc=2,1")
    assert plot.grid.flush_col_boundaries == set()
    assert all(assignment.orientation == "vertical" for _, assignment in _colorbars(plot)) and len(_colorbars(plot)) == 3
