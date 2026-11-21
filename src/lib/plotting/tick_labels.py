"""Tick labels that stay within their axes' ends and never overlap. Both measure drawn labels, so the layout
engine runs them inside its passes (never per frame)."""

import weakref

from matplotlib import pyplot as plt
from matplotlib.axis import Axis, XAxis
from matplotlib.backend_bases import RendererBase
from matplotlib.text import Text
from matplotlib.ticker import Locator, LogLocator, MaxNLocator

TICK_LABEL_MIN_GAP = 2.0
"""Points between neighboring tick labels, at least."""
MAX_THINNING_STEPS = 20

_HIDDEN_LABELS: weakref.WeakKeyDictionary[Axis, list[Text]] = weakref.WeakKeyDictionary()
"""The labels `thin_crowded_ticks` hid, per axis."""
_ORIGINAL_DENSITY: weakref.WeakKeyDictionary[Axis, int | str | None] = weakref.WeakKeyDictionary()
"""Each axis' locator density before `thin_crowded_ticks` first touched it."""


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


def _locator_density(locator: Locator) -> int | str | None:
    if isinstance(locator, MaxNLocator):
        return locator._nbins
    if isinstance(locator, LogLocator):
        return locator.numticks
    return None


def _set_locator_density(locator: Locator, density: int | str):
    if isinstance(locator, MaxNLocator):
        locator.set_params(nbins=density)
    elif isinstance(locator, LogLocator):
        locator.set_params(numticks=density)


def thin_crowded_ticks(axis: Axis, renderer: RendererBase):
    """Tuck the labels, then, while any two overlap, ask the axis' locator for fewer ticks. Only `MaxNLocator`
    (linear) and `LogLocator` can be asked; other locators are left alone. Never thins below two labels in view,
    and gives up after `MAX_THINNING_STEPS`. Labels that still overlap are hidden, keeping the first of each
    overlapping pair; `two_label_length` still counts them, so the layout can grow the axis to fit them.

    Each call starts over from the locator's original density, so an axis the layout grew gets its ticks back."""
    fig = axis.get_figure(root=True)
    locator = axis.get_major_locator()
    original = _ORIGINAL_DENSITY.setdefault(axis, _locator_density(locator))
    # Labels this hid in an earlier pass get another chance (not others: e.g. a stacked panel's hidden x labels).
    restored = _HIDDEN_LABELS.pop(axis, [])
    for label in restored:
        label.set_visible(True)
    if original is not None and _locator_density(locator) != original:
        _set_locator_density(locator, original)
        restored = True
    if restored:
        fig.draw_without_rendering()
        renderer = fig.canvas.get_renderer()

    density = original
    for _ in range(MAX_THINNING_STEPS):
        tuck_tick_labels(axis, renderer)  # tucking slides end labels inward, toward their neighbors
        if not _any_overlap(axis, renderer) or density is None:
            break
        n_ticks = len(visible_tick_labels(axis))
        if n_ticks <= 2:
            break

        # Ask for fewer each step, even if the locator didn't oblige last time.
        previous = density
        density = max(1, min(n_ticks, density if isinstance(density, int) else n_ticks) - 1)
        _set_locator_density(locator, density)
        fig.draw_without_rendering()
        renderer = fig.canvas.get_renderer()

        if len(visible_tick_labels(axis)) < 2:  # too few in view: back off a step, and let hiding do the rest
            _set_locator_density(locator, previous)
            fig.draw_without_rendering()
            renderer = fig.canvas.get_renderer()
            tuck_tick_labels(axis, renderer)
            break

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


def _pair_gap(length: float, fa: float, wa: float, fb: float, wb: float) -> float:
    """The gap between two labels, `wa` and `wb` long and centered at fractions `fa < fb` of an axis `length`
    long, each tucked inside the axis' ends. It only grows with `length`."""
    a_end = max(fa * length - wa / 2, 0.0) + wa
    b_start = min(fb * length + wb / 2, length) - wb
    return b_start - a_end


def two_label_length(axis: Axis, renderer: RendererBase) -> float:
    """The length, in display units, `axis` needs for each pair of neighboring tick labels it has now to sit apart,
    with their ticks where they are along it, or 0 if it has fewer than two. Labels thinning hid count (so the
    axis can grow to show them); ones hidden for other reasons don't."""
    labels = {id(label) for label in visible_tick_labels(axis)} | {id(label) for label in _HIDDEN_LABELS.get(axis, []) if label.get_text()}
    is_x = isinstance(axis, XAxis)
    box = axis.axes.get_window_extent(renderer)
    start, extent = (box.x0, box.width) if is_x else (box.y0, box.height)
    transform = axis.axes.get_xaxis_transform() if is_x else axis.axes.get_yaxis_transform()
    if extent <= 0:
        return 0.0

    placed = []
    for loc, tick in zip(axis.get_majorticklocs(), axis.get_major_ticks(len(axis.get_majorticklocs()))):
        for label in (tick.label1, tick.label2):  # e.g. a colorbar's labels are on its right: label2
            if id(label) in labels:
                position = transform.transform((loc, 0.0) if is_x else (0.0, loc))[0 if is_x else 1]
                visible = label.get_visible()
                label.set_visible(True)  # a hidden label measures as empty
                label_extent = label.get_window_extent(renderer)
                label.set_visible(visible)
                placed.append(((position - start) / extent, label_extent.width if is_x else label_extent.height))
                break
    placed.sort()
    if len(placed) < 2:
        return 0.0

    gap = TICK_LABEL_MIN_GAP * axis.get_figure(root=True).dpi / 72
    need = 0.0
    for (fa, wa), (fb, wb) in zip(placed, placed[1:]):
        if fb - fa <= 1e-9:
            continue
        lower, upper = 0.0, (wa + wb + gap) / (fb - fa)  # long enough even untucked
        for _ in range(40):
            middle = (lower + upper) / 2
            lower, upper = (lower, middle) if _pair_gap(middle, fa, wa, fb, wb) >= gap else (middle, upper)
        need = max(need, upper)
    return need


def separate_junction_labels(first: Axis, second: Axis, renderer: RendererBase):
    """Where two axes meet edge to edge along the same direction (`first` before `second`: left of it, or above
    it), hide `second`'s label nearest the junction if it crowds `first`'s. Tucked, they can't overlap, but they can
    touch, e.g. "1.0" and "0.0" reading as "1.00.0". `thin_crowded_ticks` gives it another chance each pass."""
    first_labels, second_labels = visible_tick_labels(first), visible_tick_labels(second)
    if not first_labels or not second_labels:
        return
    gap = TICK_LABEL_MIN_GAP * first.get_figure(root=True).dpi / 72
    first_extents = [label.get_window_extent(renderer) for label in first_labels]
    second_extents = [(label, label.get_window_extent(renderer)) for label in second_labels]
    if isinstance(first, XAxis):  # side by side: first's rightmost label, second's leftmost
        edge = max(extent.x1 for extent in first_extents)
        label, extent = min(second_extents, key=lambda pair: pair[1].x0)
        crowded = extent.x0 - edge < gap
    else:  # stacked: first's bottom label, second's top one
        edge = min(extent.y0 for extent in first_extents)
        label, extent = max(second_extents, key=lambda pair: pair[1].y1)
        crowded = edge - extent.y1 < gap
    if crowded:
        label.set_visible(False)
        _HIDDEN_LABELS.setdefault(second, []).append(label)
