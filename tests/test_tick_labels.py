"""Tick labels never stick out past their axes' ends, and never overlap."""

import itertools

import matplotlib.pyplot as plt
import pytest
from conftest import make_plot
from matplotlib.axis import XAxis
from matplotlib.figure import Figure

from lib.plotting.tick_labels import thin_crowded_ticks, tuck_tick_labels, visible_tick_labels

PLOTS = [
    "pfd hx_fc -i t=-1 -v y",
    "pfd hx_fc -i t=-1 -v y z",
    "-w pfd::hx_fc -i t=3 -cv y z loc=1,1 -w pfd::hy_fc -i t=3 --mul 1e-5 -cv y z loc=1,2 -w pfd::hz_fc -i t=3 -cv y z loc=1,3",
    "pfd ex_ec --copy -i t=0 -v y --copy ex_ec -i t=-1 -v y loc=1,2 -w ex_ec -v t loc=1,3",
    "pfd_moments px_e -i y=0 -v t -w pfd::hx_fc -i y=0 -v t",
    "prt.i --bin px=20 pz=20 --scale log --nan0 -v px pz",
]


def _cartesian_axes(fig: Figure):
    return [ax for ax in fig.axes if ax.name != "polar"]


@pytest.mark.parametrize("args", PLOTS)
def test_no_tick_label_overhangs(args: str):
    fig = make_plot(args.split())
    fig.draw_without_rendering()
    renderer = fig.canvas.get_renderer()
    for ax in _cartesian_axes(fig):
        box = ax.get_window_extent(renderer)
        for label in visible_tick_labels(ax.xaxis):
            extent = label.get_window_extent(renderer)
            assert box.x0 - 1 <= extent.x0 and extent.x1 <= box.x1 + 1, (args, label.get_text())
        for label in visible_tick_labels(ax.yaxis):
            extent = label.get_window_extent(renderer)
            assert box.y0 - 1 <= extent.y0 and extent.y1 <= box.y1 + 1, (args, label.get_text())


def _assert_no_overlaps(fig: Figure, args: str):
    fig.draw_without_rendering()
    renderer = fig.canvas.get_renderer()
    for ax in _cartesian_axes(fig):
        for axis in (ax.xaxis, ax.yaxis):
            extents = [label.get_window_extent(renderer) for label in visible_tick_labels(axis)]
            for a, b in itertools.combinations(extents, 2):
                assert not a.overlaps(b), (args, a, b)


@pytest.mark.parametrize("args", PLOTS)
def test_no_tick_labels_overlap(args: str):
    _assert_no_overlaps(make_plot(args.split()), args)


def test_crowded_axis_thinned():
    args = "pfd hx_fc -i t=-1 -v y --figsize 1.6,auto"
    _assert_no_overlaps(make_plot(args.split()), args)


def test_stack_junction_labels_dont_overlap():
    """The lower panel's top y label and the upper panel's bottom one, at the edge they share."""
    fig = make_plot(PLOTS[2].split())
    fig.draw_without_rendering()
    renderer = fig.canvas.get_renderer()
    plot_axes = sorted([ax for ax in fig.axes if not hasattr(ax, "_colorbar")], key=lambda ax: -ax.get_position().y1)
    for upper, lower in zip(plot_axes[:-1], plot_axes[1:]):
        for a in visible_tick_labels(upper.yaxis):
            for b in visible_tick_labels(lower.yaxis):
                assert not a.get_window_extent(renderer).overlaps(b.get_window_extent(renderer))


def test_thinning_terminates():
    """A log axis spanning less than a decade can't thin further; thinning still returns."""
    fig, ax = plt.subplots(figsize=(0.5, 0.5))
    ax.set_yscale("log")
    ax.set_ylim(2, 5)
    fig.draw_without_rendering()
    thin_crowded_ticks(ax.yaxis, fig.canvas.get_renderer())
    tuck_tick_labels(ax.yaxis, fig.canvas.get_renderer())


def test_tuck_leaves_interior_labels_alone():
    fig, ax = plt.subplots()
    ax.set_xlim(0, 1)
    fig.draw_without_rendering()
    tuck_tick_labels(ax.xaxis, fig.canvas.get_renderer())
    middle = [label for label in ax.xaxis.get_ticklabels() if label.get_text() == "0.4"]
    assert middle and middle[0].get_ha() == "center"
    assert isinstance(ax.xaxis, XAxis)


def test_stacked_upper_panels_keep_x_labels_hidden():
    fig = make_plot(PLOTS[2].split())
    fig.draw_without_rendering()
    plot_axes = sorted([ax for ax in fig.axes if not hasattr(ax, "_colorbar")], key=lambda ax: -ax.get_position().y1)
    for upper in plot_axes[:-1]:
        assert not visible_tick_labels(upper.xaxis)
    assert visible_tick_labels(plot_axes[-1].xaxis)
