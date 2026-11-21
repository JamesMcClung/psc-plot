"""Ticks point inward on every side, each colored to stand out against what's beneath it."""

import numpy as np
import pytest
from conftest import _DATA_DIR

from lib.config import PscPlotConfig
from lib.parsing.parse import parse_args
from lib.run.compile import compile_plot_pipeline


def _plot(args: str):
    plot = compile_plot_pipeline(parse_args(args.split()), PscPlotConfig.create_minimal(data_root=_DATA_DIR / "test-2d")).run_plot()
    plot._initialize()
    plot.fig.draw_without_rendering()
    return plot


def _ticks(plot, ax):
    [ticks] = [ticks for panel in plot.grid.panels.values() for ticks in panel.inward_ticks if ticks.ax is ax]
    return ticks


@pytest.mark.parametrize("args", ["pfd hx_fc -i t=-1 -v y z", "pfd hx_fc -i t=-1 -v y", "pfd_moments px_e -i y=0 -v t -w pfd::hx_fc -i y=0 -v t"])
def test_no_outward_ticks(args: str):
    plot = _plot(args)
    for ax in plot.fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                assert tick.tick1line.get_markersize() == 0 and tick.tick2line.get_markersize() == 0


def test_inward_ticks_every_side():
    plot = _plot("pfd hx_fc -i t=-1 -v y z")
    ax = plot.grid.panels[(1, 1)].axes[0]
    ticks = _ticks(plot, ax)

    lower, upper = sorted(ax.get_xlim())
    x_locs = [x for x in ax.xaxis.get_majorticklocs() if lower <= x <= upper]
    lower, upper = sorted(ax.get_ylim())
    y_locs = [y for y in ax.yaxis.get_majorticklocs() if lower <= y <= upper]

    for side in ("bottom", "top"):
        assert np.allclose(ticks.artists[(side, False)].get_offsets()[:, 0], x_locs)
    for side in ("left", "right"):
        assert np.allclose(ticks.artists[(side, False)].get_offsets()[:, 1], y_locs)


def test_ticks_dark_on_white_background():
    plot = _plot("pfd hx_fc -i t=-1 -v y")
    ticks = _ticks(plot, plot.grid.panels[(1, 1)].axes[0])
    colors = ticks.artists[("bottom", False)].get_edgecolor()
    assert np.all(colors[:, :3] < 0.2)


def test_ticks_on_image_follow_the_data():
    plot = _plot("pfd hx_fc -i t=-1 -v y z")
    ticks = _ticks(plot, plot.grid.panels[(1, 1)].axes[0])
    colors = np.concatenate([ticks.artists[(side, False)].get_edgecolor() for side in ("bottom", "top", "left", "right")])
    assert len({tuple(np.round(color, 3)) for color in colors}) > 1


def test_cbar_ticks_inward_and_dark_on_white():
    """hx_fc's colormap is white at 0, so the colorbar's tick there is dark."""
    plot = _plot("pfd hx_fc -i t=-1 -v y z")
    [cbar] = plot.grid.panels[(1, 1)].colorbars
    ticks = _ticks(plot, cbar.ax)
    for side in ("left", "right"):
        artist = ticks.artists[(side, False)]
        values = artist.get_offsets()[:, 1]
        [zero] = np.flatnonzero(np.isclose(values, 0.0))
        assert np.all(artist.get_edgecolor()[zero, :3] < 0.2)


def test_polar_left_alone():
    plot = _plot("pfd hx_fc -i t=-1 --transform-polar y z -v r_p theta time=")
    polar = [ax for ax in plot.fig.axes if ax.name == "polar"]
    assert not [ticks for panel in plot.grid.panels.values() for ticks in panel.inward_ticks if ticks.ax in polar]


def test_ticks_drawn_at_the_edges():
    """Tick markers are short: above an untitled plot, nothing is drawn but background."""
    plot = _plot("pfd hx_fc -v y time=")
    fig = plot.fig
    fig.canvas.draw()
    pixels = np.asarray(fig.canvas.buffer_rgba())[..., :3]
    ax = plot.grid.panels[(1, 1)].axes[0]
    box = ax.get_window_extent()
    top = int(fig.bbox.height - box.y1) - 1  # the rows above the axes
    left = int(box.x0) + 20  # past any y tick label overhanging the top
    assert top > 0
    assert np.all(pixels[:top, left:] == 255)


def _minor_locs_within(axis) -> list[float]:
    lower, upper = sorted(axis.get_view_interval())
    return [loc for loc in axis.get_minorticklocs() if lower <= loc <= upper]


def test_log_colorbar_has_minor_ticks():
    plot = _plot("prt.i --bin px=20 pz=20 --scale log --nan0 -v px pz")
    [cbar] = plot.grid.panels[(1, 1)].colorbars
    assert _minor_locs_within(cbar.ax.yaxis)


def test_symlog_colorbar_has_minor_ticks():
    plot = _plot("pfd hx_fc -i t=-1 --scale symlog#.001 -v y z")
    [cbar] = plot.grid.panels[(1, 1)].colorbars
    assert _minor_locs_within(cbar.ax.yaxis)


def test_symlog_axis_has_minor_ticks():
    plot = _plot("pfd hx_fc -i t=-1 --scale symlog#.001 -v y")
    assert _minor_locs_within(plot.grid.panels[(1, 1)].axes[0].yaxis)


def test_minor_ticks_get_inward_markers():
    plot = _plot("pfd hx_fc -i t=-1 --scale symlog#.001 -v y")
    ticks = _ticks(plot, plot.grid.panels[(1, 1)].axes[0])
    assert len(ticks.artists[("left", True)].get_offsets()) > 0


def test_linear_axis_has_no_minor_ticks():
    plot = _plot("pfd hx_fc -i t=-1 -v y")
    assert not _minor_locs_within(plot.grid.panels[(1, 1)].axes[0].yaxis)
