"""Panels side by side share a y axis where they can, sitting flush."""

import pytest
from conftest import make_plot
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from lib.plotting.layout.geometry import sizes_close
from lib.plotting.tick_labels import visible_tick_labels

DPI = 100.0


def _main_axes(fig: Figure) -> list[Axes]:
    """Plot axes (no colorbars, no twins), left to right then top to bottom."""
    axes = [ax for i, ax in enumerate(fig.axes) if not hasattr(ax, "_colorbar") and ax.get_position().bounds not in [other.get_position().bounds for other in fig.axes[:i]]]
    return sorted(axes, key=lambda ax: (-round(ax.get_position().y1, 3), ax.get_position().x0))


def _x_in(ax: Axes) -> tuple[float, float]:
    w = ax.get_figure(root=True).get_size_inches()[0]
    pos = ax.get_position()
    return pos.x0 * w, pos.x1 * w


def _flush(left: Axes, right: Axes) -> bool:
    return sizes_close(_x_in(left)[1], _x_in(right)[0], DPI)


def _assert_shared(left: Axes, right: Axes):
    left.get_figure(root=True).draw_without_rendering()
    assert _flush(left, right)
    assert right.get_shared_y_axes().joined(left, right)
    assert not visible_tick_labels(right.yaxis)
    assert not right.yaxis.label.get_text()
    assert left.yaxis.label.get_text()


def test_two_lines_share_y():
    fig = make_plot("pfd hx_fc -v y loc=1,1 -w hx_fc -v y loc=2,1".split())
    left, right = _main_axes(fig)
    _assert_shared(left, right)


def test_different_units_dont_share():
    fig = make_plot("pfd hx_fc -i t=-1 -v y loc=1,1 -w pfd_moments::px_e -i t=-1 -v y loc=2,1".split())
    left, right = _main_axes(fig)
    assert not _flush(left, right)
    assert right.yaxis.label.get_text()


def test_twinned_doesnt_share():
    fig = make_plot("pfd_moments px_e -i y=0 -v t -w pfd::hx_fc -i y=0 -v t -w pfd_moments::px_e -v t loc=2,1".split())
    assert len(fig.axes) == 3
    left = min(fig.axes, key=lambda ax: ax.get_position().x0)
    right = max(fig.axes, key=lambda ax: ax.get_position().x0)
    assert not _flush(left, right)


def test_boundary_flush_in_all_rows_or_none():
    """Row 1 could share, row 2 can't (B_x beside u_x); plot edges line up across the grid, so neither does."""
    fig = make_plot("pfd hx_fc -v y loc=1,1 -w hx_fc -v y loc=2,1 -w hx_fc -v y loc=1,2 -w pfd_moments::px_e -v y loc=2,2".split())
    top_left, top_right, bottom_left, bottom_right = _main_axes(fig)
    assert not _flush(top_left, top_right)
    assert not _flush(bottom_left, bottom_right)
    assert top_right.yaxis.label.get_text()


def test_x_labels_dont_collide_at_the_junction():
    fig = make_plot("pfd hx_fc -v y loc=1,1 -w hx_fc -v y loc=2,1".split())
    fig.draw_without_rendering()
    renderer = fig.canvas.get_renderer()
    left, right = _main_axes(fig)
    for a in visible_tick_labels(left.xaxis):
        for b in visible_tick_labels(right.xaxis):
            assert not a.get_window_extent(renderer).overlaps(b.get_window_extent(renderer)), (a.get_text(), b.get_text())


def test_shared_y_covers_both_panels_data():
    """The right panel's B_x spans less than the left's; the shared axis must still show all of the left's."""
    fig = make_plot("pfd hx_fc --copy -i t=0 -v y --copy hx_fc -i t=-1 -v y loc=2,1".split())
    left, right = _main_axes(fig)
    assert right.get_shared_y_axes().joined(left, right)
    lower, upper = left.get_ylim()
    for ax in (left, right):
        for line in ax.lines:
            assert lower <= line.get_ydata().min() and line.get_ydata().max() <= upper


def test_shared_x_covers_both_panels_data():
    """Stacked, the lower panel's y range is half the upper's; the shared x axis must still show all of the upper's."""
    fig = make_plot("pfd hx_fc -i t=-1 --copy -v y --copy hx_fc -i y=0:8 -v y loc=1,2".split())
    upper, lower = sorted([ax for ax in fig.axes if ax.lines], key=lambda ax: -ax.get_position().y1)
    assert upper.get_shared_x_axes().joined(upper, lower)
    left, right = upper.get_xlim()
    for ax in (upper, lower):
        for line in ax.lines:
            assert left <= line.get_xdata().min() and line.get_xdata().max() <= right
