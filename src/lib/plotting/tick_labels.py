"""Tick labels that stay within their axes' ends and never overlap. Both measure drawn labels, so the layout
engine runs them inside its passes (never per frame)."""

import weakref
from typing import Literal

from matplotlib import pyplot as plt
from matplotlib.axis import Axis, XAxis
from matplotlib.backend_bases import RendererBase
from matplotlib.text import Text
from matplotlib.ticker import LogLocator, MaxNLocator

TICK_LABEL_MIN_GAP = 2.0
"""Points between neighboring tick labels, at least."""
MAX_THINNING_STEPS = 20

_HIDDEN_LABELS: weakref.WeakKeyDictionary[Axis, list[Text]] = weakref.WeakKeyDictionary()
"""The labels `thin_crowded_ticks` hid, per axis."""


def visible_tick_labels(axis: Axis) -> list[Text]:
    """The labels matplotlib actually draws: those with text, of ticks within the view."""
    lower, upper = sorted(axis.get_view_interval())
    tol = 1e-9 * (upper - lower)
    locs = axis.get_majorticklocs()
    ticks = axis.get_major_ticks(len(locs))
    return [label for loc, tick in zip(locs, ticks) if lower - tol <= loc <= upper + tol for label in (tick.label1, tick.label2) if label.get_visible() and label.get_text()]


def tuck_tick_labels(axis: Axis, renderer: RendererBase):
    """Anchor any label that overhangs an end of its axes to that end, so it sits within the axes' span. Labels
    are reset to the default alignment first, so ones that moved away are let go."""
    box = axis.axes.get_window_extent(renderer)
    is_x = isinstance(axis, XAxis)
    default = "center" if is_x else plt.rcParams["ytick.alignment"]

    for label in visible_tick_labels(axis):
        if is_x:
            label.set_ha(default)
            extent = label.get_window_extent(renderer)
            if extent.x0 < box.x0:
                label.set_ha("left")
            elif extent.x1 > box.x1:
                label.set_ha("right")
        else:
            label.set_va(default)
            extent = label.get_window_extent(renderer)
            if extent.y0 < box.y0:
                label.set_va("bottom")
            elif extent.y1 > box.y1:
                label.set_va("top")


def _any_overlap(axis: Axis, renderer: RendererBase) -> bool:
    gap = TICK_LABEL_MIN_GAP * axis.get_figure(root=True).dpi / 72
    extents = [label.get_window_extent(renderer) for label in visible_tick_labels(axis)]
    if isinstance(axis, XAxis):
        spans = sorted((extent.x0, extent.x1) for extent in extents)
    else:
        spans = sorted((extent.y0, extent.y1) for extent in extents)
    return any(next_lo - lo_hi[1] < gap for lo_hi, (next_lo, _) in zip(spans, spans[1:]))


def thin_crowded_ticks(axis: Axis, renderer: RendererBase):
    """Tuck the labels, then, while any two overlap, ask the axis' locator for fewer ticks. Only `MaxNLocator`
    (linear) and `LogLocator` can be asked; other locators are left alone. Stops at one tick, or after
    `MAX_THINNING_STEPS`. Labels that still overlap after that (e.g. a locator that won't go below two ticks on a
    tiny axis) are hidden, keeping the first of each overlapping pair."""
    fig = axis.get_figure(root=True)
    locator = axis.get_major_locator()
    n_wanted = None
    # Labels this hid in an earlier pass get another chance (not others: e.g. a stacked panel's hidden x labels).
    for label in _HIDDEN_LABELS.pop(axis, []):
        label.set_visible(True)

    for _ in range(MAX_THINNING_STEPS):
        tuck_tick_labels(axis, renderer)  # tucking slides end labels inward, toward their neighbors
        if not _any_overlap(axis, renderer):
            return
        n_ticks = len(visible_tick_labels(axis))
        if n_ticks <= 1:
            break

        # Ask for fewer each step, even if the locator didn't oblige last time.
        n_wanted = max(1, min(n_ticks, n_wanted or n_ticks) - 1)
        if isinstance(locator, MaxNLocator):
            locator.set_params(nbins=n_wanted)
        elif isinstance(locator, LogLocator):
            locator.set_params(numticks=n_wanted)
        else:
            break

        fig.draw_without_rendering()
        renderer = fig.canvas.get_renderer()

    _hide_overlapping(axis, renderer)


def _hide_overlapping(axis: Axis, renderer: RendererBase):
    gap = TICK_LABEL_MIN_GAP * axis.get_figure(root=True).dpi / 72
    kept = []
    for label in visible_tick_labels(axis):
        extent = label.get_window_extent(renderer)
        if any(extent.padded(gap / 2).overlaps(other.padded(gap / 2)) for other in kept):
            label.set_visible(False)
            _HIDDEN_LABELS.setdefault(axis, []).append(label)
        else:
            kept.append(extent)


def prune_ticks(axis: Axis, end: Literal["lower", "upper"]):
    """Drop the tick (and its label) at `end`. Locators that can't prune (log, say) are left alone."""
    locator = axis.get_major_locator()
    if isinstance(locator, MaxNLocator):
        locator.set_params(prune=end)
