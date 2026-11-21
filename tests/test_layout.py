"""The layout engine: plot-area sizes, decorations kept inside the figure, stacks, colorbars, frame stability."""

import warnings

import numpy as np
import pytest
from conftest import _DATA_DIR, make_plot
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox

from lib.config import PscPlotConfig
from lib.parsing.parse import parse_args
from lib.plotting.animated_plot import AnimatedPlot
from lib.plotting.layout.auto_size import DEFAULT_PLOT_SIZE
from lib.plotting.layout.engine import COLORBAR_THICKNESS, MIN_PLOT_SIDE
from lib.plotting.layout.geometry import sizes_close
from lib.run.compile import compile_plot_pipeline

DPI = 100.0


def _plot(args: str, data_dir: str = "test-2d"):
    plot = compile_plot_pipeline(parse_args(args.split()), PscPlotConfig.create_minimal(data_root=_DATA_DIR / data_dir)).run_plot()
    plot._initialize()
    return plot


def _box_in(ax: Axes) -> Bbox:
    """`ax`'s plot area, in inches from the figure's bottom left."""
    fig = ax.get_figure(root=True)
    w, h = fig.get_size_inches()
    pos = ax.get_position()
    return Bbox.from_extents(pos.x0 * w, pos.y0 * h, pos.x1 * w, pos.y1 * h)


def _plot_axes(fig: Figure) -> list[Axes]:
    """The figure's plot axes, top to bottom: everything but colorbars and twins."""
    cbar_axes = {ax for ax in fig.axes if hasattr(ax, "_colorbar")}
    axes = [ax for ax in fig.axes if ax not in cbar_axes and not _is_twin(ax)]
    return sorted(axes, key=lambda ax: -ax.get_position().y1)


def _cbar_axes(fig: Figure) -> list[Axes]:
    return [ax for ax in fig.axes if hasattr(ax, "_colorbar")]


def _is_twin(ax: Axes) -> bool:
    return any(other is not ax and other.bbox.bounds == ax.bbox.bounds and fig_index(other) < fig_index(ax) for other in ax._twinned_axes.get_siblings(ax))


def fig_index(ax: Axes) -> int:
    return ax.get_figure(root=True).axes.index(ax)


def _assert_inside_figure(fig: Figure):
    fig.draw_without_rendering()
    tight = fig.get_tightbbox(fig.canvas.get_renderer())  # inches
    w, h = fig.get_size_inches()
    tol = 1 / DPI
    assert tight.x0 >= -tol and tight.y0 >= -tol and tight.x1 <= w + tol and tight.y1 <= h + tol, (tight, (w, h))


def test_single_line_plot_area_is_auto_size():
    fig = make_plot("pfd hx_fc -i t=-1 -v y".split())
    [ax] = _plot_axes(fig)
    box = _box_in(ax)
    assert (box.width, box.height) == pytest.approx(DEFAULT_PLOT_SIZE, abs=1 / DPI)
    _assert_inside_figure(fig)


def test_figsize_fixes_figure():
    fig = make_plot("pfd hx_fc -i t=-1 -v y --figsize 6,4".split())
    assert tuple(fig.get_size_inches()) == pytest.approx((6.0, 4.0))
    _assert_inside_figure(fig)


def test_figsize_auto_height():
    fig = make_plot("pfd hx_fc -i t=-1 -v y --figsize 6,auto".split())
    w, h = fig.get_size_inches()
    assert w == pytest.approx(6.0)
    [ax] = _plot_axes(fig)
    assert _box_in(ax).height == pytest.approx(DEFAULT_PLOT_SIZE[1], abs=1 / DPI)
    _assert_inside_figure(fig)


def test_figsize_fixed_both_keeps_equal_scale():
    """An image with equal x/y scale keeps its aspect in a fixed figure, rather than stretching to fill it."""
    fig = make_plot("pfd hx_fc -i t=-1 -v y z --figsize 8,3".split())
    [ax] = _plot_axes(fig)
    box = _box_in(ax)
    assert box.width / box.height == pytest.approx(2.0, rel=0.01)  # test-2d: y spans twice z
    _assert_inside_figure(fig)


@pytest.mark.parametrize("args", ["pfd hx_fc -i t=-1 -v y", "pfd hx_fc -i t=-1 -v y z --figsize 5.13,auto"])
def test_figure_pixels_even(args: str):
    fig = make_plot(args.split())
    dots = fig.get_size_inches() * fig.dpi
    assert np.allclose(dots, np.round(dots)) and all(round(d) % 2 == 0 for d in dots), dots


def test_colorbar_geometry():
    fig = make_plot("pfd hx_fc -i t=-1 -v y z".split())
    [ax] = _plot_axes(fig)
    [cax] = _cbar_axes(fig)
    plot_box, cbar_box = _box_in(ax), _box_in(cax)
    assert cbar_box.width == pytest.approx(COLORBAR_THICKNESS, abs=1 / DPI)
    # at least 10% shorter than the panel at each end, leaving room for its texts
    assert cbar_box.y0 >= plot_box.y0 + 0.1 * plot_box.height - 1 / DPI
    assert cbar_box.y1 <= plot_box.y1 - 0.1 * plot_box.height + 1 / DPI
    assert cbar_box.x0 >= plot_box.x1
    _assert_inside_figure(fig)


def test_stacked_panels_flush():
    fig = make_plot("-w pfd::hx_fc -i t=3 -cv y z loc=1,1 -w pfd::hy_fc -i t=3 --mul 1e-5 -cv y z loc=1,2 -w pfd::hz_fc -i t=3 -cv y z loc=1,3".split())
    boxes = [_box_in(ax) for ax in _plot_axes(fig)]
    assert len(boxes) == 3
    for upper, lower in zip(boxes[:-1], boxes[1:]):
        assert sizes_close(upper.y0, lower.y1, DPI)
        assert sizes_close(upper.x0, lower.x0, DPI) and sizes_close(upper.x1, lower.x1, DPI)
    _assert_inside_figure(fig)


def test_stacks_separated_where_x_isnt_shared():
    fig = make_plot("pfd ex_ec --copy -i t=0 -v y --copy ex_ec -i t=-1 -v y loc=1,2 -w ex_ec -v t loc=1,3".split())
    upper, middle, lower = [_box_in(ax) for ax in _plot_axes(fig)]
    assert sizes_close(upper.y0, middle.y1, DPI)
    assert middle.y0 - lower.y1 > 0.1  # room for the middle panel's x axis
    _assert_inside_figure(fig)


def test_twin_axis_labels_fit():
    """u_x has a unit and B_x hasn't, so B_x gets its own y axis on the right."""
    fig = make_plot("pfd_moments px_e -i y=0 -v t -w pfd::hx_fc -i y=0 -v t".split())
    assert len(fig.axes) == 2
    fig.draw_without_rendering()
    for ax in fig.axes:
        assert ax.yaxis.label.get_text()
        assert [label for label in ax.yaxis.get_ticklabels() if label.get_visible() and label.get_text()]
    _assert_inside_figure(fig)


def test_suptitle_fits():
    fig = make_plot("prt.i -i t=1: --bin y z -v y z --with prt.e -i t=1: --bin y z -v y z loc=1,2".split())
    _assert_inside_figure(fig)


def test_layout_never_moves():
    plot = _plot("pfd hx_fc -v y z")
    assert isinstance(plot, AnimatedPlot)
    size = tuple(plot.fig.get_size_inches())
    positions = [tuple(ax.get_position().bounds) for ax in plot.fig.axes]
    for frame in range(plot.n_frames):
        plot._next_frame(frame)
        plot.fig.canvas.draw()
        assert tuple(plot.fig.get_size_inches()) == size
        assert [tuple(ax.get_position().bounds) for ax in plot.fig.axes] == positions


def test_too_small_figsize_warns_and_snaps():
    with pytest.warns(UserWarning, match="--figsize"):
        fig = make_plot("pfd hx_fc -i t=-1 -v y z --figsize 1,1".split())
    [ax] = _plot_axes(fig)
    box = _box_in(ax)
    assert min(box.width, box.height) == pytest.approx(MIN_PLOT_SIDE, abs=1 / DPI)
    w, h = fig.get_size_inches()
    assert w > 1 and h > 1
    _assert_inside_figure(fig)


def test_enough_figsize_doesnt_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        make_plot("pfd hx_fc -i t=-1 -v y --figsize 6,4".split())


def test_empty_title_reserves_nothing():
    """With no sublabels (no scalar coords), the title is empty and takes no room."""
    fig = make_plot("pfd hx_fc -v y time=".split())  # averaged over t, so no scalar coords
    [ax] = _plot_axes(fig)
    assert ax.title.get_text() == ""
    _, h = fig.get_size_inches()
    assert h - _box_in(ax).y1 < 0.3


def test_noncontiguous_locs():
    fig = make_plot("pfd hx_fc -i t=-1 -v y loc=1,1 -w hy_fc -i t=-1 -v y loc=1,3".split())
    assert len(_plot_axes(fig)) == 2
    _assert_inside_figure(fig)


def test_polar_beside_cartesian():
    fig = make_plot("pfd hx_fc -i t=-1 --transform-polar y z -v r_p theta time= -w pfd_moments::jx_e -i t=-1 -v y loc=2,1".split())
    polar = [ax for ax in fig.axes if ax.name == "polar"]
    assert len(polar) == 1
    box = _box_in(polar[0])
    assert box.width == pytest.approx(box.height, abs=1 / DPI)
    _assert_inside_figure(fig)


def test_layout_independent_of_device_pixel_ratio():
    """HiDPI backends (macosx on a Retina screen) draw at a multiple of the figure's dpi; the layout is in inches."""
    from lib.plotting.layout.engine import run_layout

    plot = _plot("pfd hx_fc -i t=-1 -v y z")
    size = tuple(plot.fig.get_size_inches())
    positions = [tuple(ax.get_position().bounds) for ax in plot.fig.axes]

    plot.fig.canvas._set_device_pixel_ratio(2)
    run_layout(plot.fig, plot.grid, plot.layout_options)
    # text renders a hair differently at 2x, which can flip the even-dot rounding
    assert tuple(plot.fig.get_size_inches()) == pytest.approx(size, abs=2.01 / DPI)
    # text renders a hair differently at 2x, so within a few dots rather than exactly; doubled margins are ~0.1
    assert np.allclose([ax.get_position().bounds for ax in plot.fig.axes], positions, atol=5e-3)


def test_colorbars_line_up_down_a_column():
    fig = make_plot("-w pfd::hx_fc -i t=3 -cv y z loc=1,1 -w pfd::hy_fc -i t=3 --mul 1e-5 -cv y z loc=1,2 -w pfd::hz_fc -i t=3 -cv y z loc=1,3".split())
    lefts = [_box_in(cax).x0 for cax in _cbar_axes(fig)]
    assert len(lefts) == 3
    assert all(sizes_close(left, lefts[0], DPI) for left in lefts), lefts


def test_polar_has_no_legend():
    fig = make_plot("pfd hx_fc -i t=-1 --transform-polar y z -v r_p theta time=".split())
    assert not [ax for ax in fig.axes if ax.get_legend()]
