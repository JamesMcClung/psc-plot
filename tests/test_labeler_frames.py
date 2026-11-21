"""Where a sublabel goes (title or legend) is decided from every frame, so it never moves between frames."""

import pytest
from conftest import CONFIG_2D

from lib.parsing.parse import parse_args
from lib.plotting.animated_plot import AnimatedPlot
from lib.run.compile import compile_plot_pipeline


def _plot(args: str):
    plot = compile_plot_pipeline(parse_args(args.split()), CONFIG_2D).run_plot()
    plot._initialize()
    return plot


def _legend_texts(ax) -> list[str]:
    legend = ax.get_legend()
    return [text.get_text() for text in legend.get_texts()] if legend else []


def test_label_placement_stable():
    """One line animates over t, the other is fixed at t=0: they share t's value only on frame 0, so t stays in the
    legend throughout, rather than jumping to the title on frame 0."""
    plot = _plot("pfd hx_fc -v y -i t=0 -v y")
    assert isinstance(plot, AnimatedPlot)
    [ax] = plot.fig.axes
    for frame in range(plot.n_frames):
        plot._next_frame(frame)
        assert "t =" not in ax.title.get_text(), (frame, ax.title.get_text())
        texts = _legend_texts(ax)
        assert len(texts) == 2 and all("t =" in text for text in texts), (frame, texts)


def test_common_coord_still_lifts():
    plot = _plot("pfd hx_fc -i t=-1 -v y")
    [ax] = plot.fig.axes
    assert "t =" in ax.title.get_text()


@pytest.fixture
def reads(monkeypatch: pytest.MonkeyPatch):
    from adios2py.file import File

    reads: list[str] = []
    original_read = File._read

    def counting_read(self: File, var_name: str, index):
        reads.append(var_name)
        return original_read(self, var_name, index)

    monkeypatch.setattr(File, "_read", counting_read)
    return reads


def test_get_scalar_coord_values_is_lazy(reads):
    plot = compile_plot_pipeline(parse_args("pfd hx_fc -v y".split()), CONFIG_2D).run_plot()
    [renderer] = plot.renderers
    reads.clear()
    values = [renderer.get_scalar_coord_values(frame) for frame in range(renderer.get_n_frames())]
    assert len({float(frame_values["t"]) for frame_values in values}) == renderer.get_n_frames()
    assert "hx_fc" not in reads
