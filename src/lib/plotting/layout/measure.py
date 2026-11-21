from dataclasses import dataclass

from matplotlib.backend_bases import RendererBase
from matplotlib.colorbar import Colorbar
from matplotlib.text import Text
from matplotlib.transforms import Bbox

from lib.plotting.grid import Grid
from lib.plotting.layout.geometry import Margins
from lib.plotting.panel import Panel
from lib.plotting.tick_labels import two_label_length


@dataclass(frozen=True)
class ColorbarDecorations:
    """How far, in inches, a colorbar's tick labels and labels extend past the bar itself."""

    margins: Margins
    min_length: float = 0.0
    """Inches of bar its tick labels need: room for two of them."""


@dataclass(frozen=True)
class PanelDecorations:
    """How far, in inches, a panel's axes decorations (tick labels, axis labels, title, any twin's) extend past
    its plot area, not counting its colorbars."""

    axes_margins: Margins
    colorbars: list[ColorbarDecorations]
    min_plot_size: tuple[float, float] = (0.0, 0.0)
    """Inches of plot area its axes' tick labels need: room for two of them along each axis."""


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
    return ColorbarDecorations(_overhang(tight, box, dpi), two_label_length(cbar.ax.yaxis, renderer) / dpi)


def measure_panel(panel: Panel, renderer: RendererBase, dpi: float) -> PanelDecorations:
    main = panel.axes[0]
    box = main.get_window_extent(renderer)

    tights = [tight for ax in panel.axes if (tight := _tight_bbox(ax, renderer))]
    tight = Bbox.union([box, *tights])

    cartesian = [ax for ax in panel.axes if ax.name != "polar"]
    min_width = max((two_label_length(ax.xaxis, renderer) for ax in cartesian), default=0.0) / dpi
    min_height = max((two_label_length(ax.yaxis, renderer) for ax in cartesian), default=0.0) / dpi

    return PanelDecorations(_overhang(tight, box, dpi), [measure_colorbar(cbar, renderer, dpi) for cbar in panel.colorbars], (min_width, min_height))


def _layout_texts(grid: Grid) -> list[Text]:
    """The texts that take layout room and change between frames: titles, the suptitle and colorbar labels. (Legends
    sit inside their axes.)"""
    texts = [panel.axes[0].title for panel in grid.panels.values()] + [grid.suptitle]
    return texts + [colorbar_text.top for panel in grid.panels.values() for colorbar_text in panel.colorbar_texts]


def _set_frame(grid: Grid, frame: int):
    for infos in grid.infos.values():
        for info in infos:
            if info.frames_scalar_coord_values:
                info.scalar_coord_values = info.frames_scalar_coord_values[min(frame, len(info.frames_scalar_coord_values) - 1)]
    grid.update_label_texts()


def widest_frame_texts(grid: Grid, renderer: RendererBase) -> dict[Text, str]:
    """For each layout text whose string changes between frames, its widest string (then tallest), to lay out with.
    Leaves every text as on frame 0. Each distinct string is measured once."""
    n_frames = max((len(info.frames_scalar_coord_values) for infos in grid.infos.values() for info in infos), default=1)
    if n_frames <= 1:
        return {}

    texts = _layout_texts(grid)
    stringss: dict[Text, dict[str, None]] = {text: {} for text in texts}  # a dict keeps the order
    for frame in range(n_frames):
        _set_frame(grid, frame)
        for text in texts:
            stringss[text][text.get_text()] = None
    _set_frame(grid, 0)

    widest = {}
    for text, strings in stringss.items():
        if len(strings) <= 1:
            continue
        frame_0 = text.get_text()
        sizes = {}
        for string in strings:
            text.set_text(string)
            extent = text.get_window_extent(renderer)
            sizes[string] = (extent.width, extent.height)
        text.set_text(frame_0)
        widest[text] = max(strings, key=lambda string: sizes[string])
    return widest


def measure_text_height(text: Text, renderer: RendererBase, dpi: float) -> float:
    """The height of `text` in inches, or 0 if it's empty or hidden."""
    if not text.get_visible() or not text.get_text():
        return 0.0
    return text.get_window_extent(renderer).height / dpi
