"""Lines on a twin y axis: told apart by color, each axis labeled in its lines' color."""

from conftest import make_plot
from matplotlib.colors import same_color

TWIN = "pfd_moments px_e -i y=0 -v t -w pfd::hx_fc -i y=0 -v t"


def test_twin_lines_differ_in_color():
    fig = make_plot(TWIN.split())
    left, right = fig.axes
    [left_line], [right_line] = left.lines, right.lines
    assert not same_color(left_line.get_color(), right_line.get_color())


def test_twin_axes_labeled_in_their_lines_color():
    fig = make_plot(TWIN.split())
    fig.draw_without_rendering()
    for ax in fig.axes:
        [line] = ax.lines
        assert same_color(ax.yaxis.label.get_color(), line.get_color())
        assert all(same_color(label.get_color(), line.get_color()) for label in ax.yaxis.get_ticklabels())


def test_single_axis_labels_stay_black():
    fig = make_plot("pfd ex_ec --copy -i t=0 -v y --copy ex_ec -i t=-1 -v y".split())
    [ax] = fig.axes
    assert same_color(ax.yaxis.label.get_color(), "black")
