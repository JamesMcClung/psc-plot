"""All text but tick labels is twice matplotlib's default size."""

from conftest import make_plot
from matplotlib.text import Text

TITLE = 24.0  # 2 x "large" (12pt)
LABEL = 20.0  # 2 x "medium" (10pt)
TICK = 10.0


def _tick_labels(fig) -> list[Text]:
    return [label for ax in fig.axes for axis in (ax.xaxis, ax.yaxis) for label in axis.get_ticklabels()]


def test_image_text_twice_default():
    fig = make_plot("pfd hx_fc -i t=-1 -v y z".split())
    ax, cax = fig.axes
    assert ax.title.get_fontsize() == TITLE
    assert ax.xaxis.label.get_fontsize() == LABEL
    assert ax.yaxis.label.get_fontsize() == LABEL
    assert all(text.get_fontsize() == LABEL for text in cax.texts)
    assert all(label.get_fontsize() == TICK for label in _tick_labels(fig))


def test_suptitle_twice_default():
    fig = make_plot("prt.i -i t=-1 --bin y z -v y z time= --with prt.e -i t=-1 --bin y z -v y z time= loc=1,2".split())
    assert fig._suptitle.get_fontsize() == TITLE


def test_legend_twice_default():
    fig = make_plot("pfd ex_ec --copy -i t=0 -v y --copy ex_ec -i t=-1 -v y".split())
    [legend] = [ax.get_legend() for ax in fig.axes if ax.get_legend()]
    assert all(text.get_fontsize() == LABEL for text in legend.get_texts())
