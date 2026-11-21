"""Which colorbars a grid gets, and which images each keys. Pure: it works on a model of the grid, so the rules can
be tested on their own.

A colorbar keys the images flush with it: a vertical bar, the run of flush panels to its left (extended over runs
flush below with the same key); a horizontal bar, the stack below it. A colorbar must never be ambiguous: every image
is keyed by exactly one bar, of its own key, and no bar sits where flush panels close up the space it would take
(even in another row or column). Sharing y axes is tried first; if the colorbars that needs would be
ambiguous, no column boundary is flush, and every image gets a vertical bar of its own (extended over same-key images
flush above and below it).
"""

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass
from typing import Literal

type AxesIdx = tuple[int, int]
type ColorKey = Hashable
"""What images must agree on to share a colorbar: the display, unit and scale of their color dim."""


@dataclass(frozen=True)
class CellModel:
    loc: AxesIdx
    color_key: ColorKey | None
    """`None` for a panel without an image (or anything else needing a colorbar)."""


@dataclass(frozen=True)
class GridModel:
    cells: dict[AxesIdx, CellModel]
    x_stacks: list[list[AxesIdx]]
    """Every panel's stack (runs sharing an x axis, flush), top to bottom; a panel on its own is a stack of one."""
    shareable_col_boundaries: set[int]
    """Columns `c` whose panels could all share y with those of column `c + 1`, colorbars aside."""


@dataclass(frozen=True)
class ColorbarAssignment:
    orientation: Literal["vertical", "horizontal"]
    keyed: tuple[AxesIdx, ...]
    """The images it keys."""
    anchors: tuple[AxesIdx, ...]
    """The panels it attaches to: a vertical bar sits right of each (the right end of each run it spans), a
    horizontal bar above its one (the top of the stack it keys)."""


@dataclass(frozen=True)
class ColorbarPlan:
    colorbars: list[ColorbarAssignment]
    flush_col_boundaries: set[int]


def _row_runs(model: GridModel, flush: set[int]) -> list[list[AxesIdx]]:
    """Each row's runs of panels sitting flush side by side, left to right; rows top to bottom."""
    runs = []
    for row in sorted({loc[1] for loc in model.cells}):
        for loc in sorted((loc for loc in model.cells if loc[1] == row), key=lambda loc: loc[0]):
            previous = runs[-1][-1] if runs and runs[-1][-1][1] == row else None
            if previous and previous[0] + 1 == loc[0] and previous[0] in flush:
                runs[-1].append(loc)
            else:
                runs.append([loc])
    return runs


def _plan(model: GridModel, flush: set[int]) -> ColorbarPlan | None:
    """The colorbars with these column boundaries flush, or `None` if they'd be ambiguous."""
    key = {loc: cell.color_key for loc, cell in model.cells.items()}
    stack_of = {loc: (stack, i) for stack in model.x_stacks for i, loc in enumerate(stack)}
    flush_rows = {stack[i][1] for stack in model.x_stacks for i in range(len(stack) - 1)}

    def flush_below(above: AxesIdx, below: AxesIdx) -> bool:
        stack, i = stack_of[above]
        return i + 1 < len(stack) and stack[i + 1] == below

    colorbars: list[ColorbarAssignment] = []
    keyed_from_above: set[AxesIdx] = set()
    vertical_groups: list[tuple[list[list[AxesIdx]], ColorKey]] = []  # runs merged into one bar, and their key

    for run in _row_runs(model, flush):
        images = [loc for loc in run if key[loc] is not None]
        if not images:
            continue
        already = [loc for loc in images if loc in keyed_from_above]
        if len(already) == len(images):
            continue  # a horizontal bar above keys them all

        if len({key[loc] for loc in images}) == 1:
            if already:
                return None  # a bar at the run's end would key these a second time
            if run[-1][0] in flush:
                return None  # the bar would sit in a junction other rows close up
            # Extend the bar of the same key over the run flush above, if it spans the same columns.
            for runs, group_key in vertical_groups:
                above = runs[-1]
                if group_key == key[images[0]] and [loc[0] for loc in above] == [loc[0] for loc in run] and all(flush_below(a, b) for a, b in zip(above, run)):
                    runs.append(run)
                    break
            else:
                vertical_groups.append(([run], key[images[0]]))
            continue

        # The run's images differ: each gets a horizontal bar above it, keying its stack, which it must top.
        for loc in images:
            if loc in already:
                continue
            stack, i = stack_of[loc]
            if i != 0 or loc[1] - 1 in flush_rows:
                return None  # a horizontal bar never sits inside a stack, nor in a junction other columns close up
            stack_images = tuple(below for below in stack if key[below] is not None)
            colorbars.append(ColorbarAssignment("horizontal", stack_images, (loc,)))
            keyed_from_above.update(stack_images)

    for runs, _ in vertical_groups:
        keyed = tuple(loc for run in runs for loc in run if key[loc] is not None)
        colorbars.append(ColorbarAssignment("vertical", keyed, tuple(run[-1] for run in runs)))

    # Unambiguous: every image keyed exactly once, by a bar of its own key.
    keyed = [loc for bar in colorbars for loc in bar.keyed]
    if sorted(keyed) != sorted(loc for loc in key if key[loc] is not None):
        return None
    if any(len({key[loc] for loc in bar.keyed}) != 1 for bar in colorbars):
        return None
    return ColorbarPlan(colorbars, flush)


def assign_colorbars(model: GridModel) -> ColorbarPlan:
    """Share y wherever it's shareable, if the colorbars that needs are unambiguous; else share none."""
    plan = _plan(model, set(model.shareable_col_boundaries))
    if plan is None:
        plan = _plan(model, set())
        assert plan is not None, "with nothing side by side, every image has a vertical bar of its own"
    return plan
