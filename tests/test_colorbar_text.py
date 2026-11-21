"""Colorbar text is horizontal: display and unit above the bar, multiplier/offset below it."""

from conftest import make_plot
from matplotlib.figure import Figure
from matplotlib.text import Text


def _cbar(fig: Figure):
    [cax] = [ax for ax in fig.axes if hasattr(ax, "_colorbar")]
    [plot_ax] = [ax for ax in fig.axes if ax is not cax]
    return cax, plot_ax


def _texts(cax) -> tuple[Text, Text]:
    """The colorbar's top and bottom texts, by where they sit."""
    fig = cax.get_figure(root=True)
    fig.draw_without_rendering()
    renderer = fig.canvas.get_renderer()
    bar = cax.get_window_extent(renderer)
    [top] = [t for t in cax.texts if t.get_window_extent(renderer).y0 >= bar.y1 - 1]
    [bottom] = [t for t in cax.texts if t.get_window_extent(renderer).y1 <= bar.y0 + 1]
    return top, bottom


def test_cbar_text_horizontal_above_bar():
    fig = make_plot("pfd hx_fc -i t=-1 --unit hx_fc=B_0 -v y z".split())
    cax, plot_ax = _cbar(fig)
    top, _ = _texts(cax)
    assert top.get_rotation() == 0
    assert top.get_text().split("\n") == ["$B_x$", "[$B_0$]"]

    renderer = fig.canvas.get_renderer()
    assert top.get_window_extent(renderer).y1 <= plot_ax.get_window_extent(renderer).y1 + 1


def test_cbar_text_without_unit_is_one_line():
    fig = make_plot("pfd hx_fc -i t=-1 -v y z".split())
    top, _ = _texts(_cbar(fig)[0])
    assert top.get_text() == "$B_x$"


def test_cbar_multiplier_below_bar():
    fig = make_plot("pfd hy_fc -i t=3 --mul 1e-5 -v y z".split())
    _, bottom = _texts(_cbar(fig)[0])
    assert bottom.get_rotation() == 0
    assert bottom.get_text() == "$\\times 10^{-6}$"


def test_cbar_native_label_and_offset_text_unused():
    fig = make_plot("pfd hy_fc -i t=3 --mul 1e-5 -v y z".split())
    cax, _ = _cbar(fig)
    assert cax.get_ylabel() == ""
    assert not cax.yaxis.get_offset_text().get_visible() or cax.yaxis.get_offset_text().get_text() == ""


def test_cbar_offset_moves_below_bar():
    """An additive offset (values clustered far from 0) goes below the bar too, beside any multiplier."""
    fig = make_plot("pfd hx_fc -i t=-1 --add 1000 -v y z".split())
    _, bottom = _texts(_cbar(fig)[0])
    assert "1000" in bottom.get_text() or "10^{3}" in bottom.get_text()
