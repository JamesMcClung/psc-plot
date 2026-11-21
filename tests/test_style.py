"""All text but tick labels is 1.5x matplotlib's default size; legend text 1.25x; colorbar multipliers tick-sized."""

from conftest import make_plot
from matplotlib.text import Text

TITLE = 18.0  # 1.5 x "large" (12pt)
LABEL = 15.0  # 1.5 x "medium" (10pt)
LEGEND = 12.5  # 1.25 x "medium" (10pt)
TICK = 10.0


def _tick_labels(fig) -> list[Text]:
    return [label for ax in fig.axes for axis in (ax.xaxis, ax.yaxis) for label in axis.get_ticklabels()]


def test_image_text_scaled():
    fig = make_plot("pfd hx_fc -i t=-1 -v y z".split())
    ax, cax = fig.axes
    assert ax.title.get_fontsize() == TITLE
    assert ax.xaxis.label.get_fontsize() == LABEL
    assert ax.yaxis.label.get_fontsize() == LABEL
    top, bottom = sorted(cax.texts, key=lambda text: -text.get_position()[1])  # the label above, the multiplier below
    assert top.get_fontsize() == LABEL
    assert bottom.get_fontsize() == TICK
    assert all(label.get_fontsize() == TICK for label in _tick_labels(fig))


def test_suptitle_scaled():
    fig = make_plot("prt.i -i t=-1 --bin y z -v y z time= --with prt.e -i t=-1 --bin y z -v y z time= loc=1,2".split())
    assert fig._suptitle.get_fontsize() == TITLE


def test_legend_scaled():
    fig = make_plot("pfd ex_ec --copy -i t=0 -v y --copy ex_ec -i t=-1 -v y".split())
    [legend] = [ax.get_legend() for ax in fig.axes if ax.get_legend()]
    assert all(text.get_fontsize() == LEGEND for text in legend.get_texts())
