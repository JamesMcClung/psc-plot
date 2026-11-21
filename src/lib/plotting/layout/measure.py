from dataclasses import dataclass

from matplotlib.backend_bases import RendererBase
from matplotlib.colorbar import Colorbar
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from lib.plotting.layout.geometry import Margins
from lib.plotting.panel import Panel


@dataclass(frozen=True)
class ColorbarDecorations:
    """How far, in inches, a colorbar's tick labels and labels extend past the bar itself."""

    margins: Margins


@dataclass(frozen=True)
class PanelDecorations:
    """How far, in inches, a panel's axes decorations (tick labels, axis labels, title, any twin's) extend past
    its plot area, not counting its colorbars."""

    axes_margins: Margins
    colorbars: list[ColorbarDecorations]


def _overhang(outer: Bbox, inner: Bbox, dpi: float) -> Margins:
    """How far `outer` extends past `inner` on each side, in inches; both in display units."""
    return Margins(
        left=max(0.0, inner.x0 - outer.x0) / dpi,
        right=max(0.0, outer.x1 - inner.x1) / dpi,
        bottom=max(0.0, inner.y0 - outer.y0) / dpi,
        top=max(0.0, outer.y1 - inner.y1) / dpi,
    )


def _tight_bbox(artist, renderer: RendererBase) -> Bbox | None:
    bbox = artist.get_tightbbox(renderer)
    return bbox if bbox is not None and bbox.width > 0 and bbox.height > 0 else None


def measure_colorbar(cbar: Colorbar, renderer: RendererBase, dpi: float) -> ColorbarDecorations:
    box = cbar.ax.get_window_extent(renderer)
    tight = _tight_bbox(cbar.ax, renderer) or box
    return ColorbarDecorations(_overhang(tight, box, dpi))


def measure_panel(panel: Panel, renderer: RendererBase, dpi: float) -> PanelDecorations:
    main = panel.axes[0]
    box = main.get_window_extent(renderer)

    tights = [tight for ax in panel.axes if (tight := _tight_bbox(ax, renderer))]
    tight = Bbox.union([box, *tights])

    return PanelDecorations(_overhang(tight, box, dpi), [measure_colorbar(cbar, renderer, dpi) for cbar in panel.colorbars])


def measure_text_height(text: Text, renderer: RendererBase, dpi: float) -> float:
    """The height of `text` in inches, or 0 if it's empty or hidden."""
    if not text.get_visible() or not text.get_text():
        return 0.0
    return text.get_window_extent(renderer).height / dpi
