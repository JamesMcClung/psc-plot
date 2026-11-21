"""Which colorbars a grid gets, and which images each keys: pure, on a model of the grid."""

import itertools
import random

import pytest

from lib.plotting.layout.colorbars import CellModel, ColorbarPlan, GridModel, assign_colorbars

E, N = ("E_y", "V/m", "linear"), ("n", "n_0", "linear")


def _model(keys: dict, stacks: list[list], shareable: set[int]) -> GridModel:
    cells = {loc: CellModel(loc, key) for loc, key in keys.items()}
    stacked = {loc for stack in stacks for loc in stack}
    stacks = stacks + [[loc] for loc in keys if loc not in stacked]
    return GridModel(cells, stacks, shareable)


def _bars(plan: ColorbarPlan, orientation: str) -> set[tuple]:
    return {bar.keyed for bar in plan.colorbars if bar.orientation == orientation}


def validate(model: GridModel, plan: ColorbarPlan):
    """Every image keyed exactly once, by a bar of its own key; horizontal bars only above a stack's top; only
    shareable boundaries flush."""
    keyed = [loc for bar in plan.colorbars for loc in bar.keyed]
    images = [loc for loc, cell in model.cells.items() if cell.color_key is not None]
    assert sorted(keyed) == sorted(images), plan
    for bar in plan.colorbars:
        assert len({model.cells[loc].color_key for loc in bar.keyed}) == 1, bar
        if bar.orientation == "horizontal":
            tops = {stack[0] for stack in model.x_stacks}
            assert all(anchor in tops for anchor in bar.anchors), bar
    assert plan.flush_col_boundaries <= model.shareable_col_boundaries


def test_row_shares_one_vertical_bar():
    model = _model({(1, 1): E, (2, 1): E}, [], {1})
    plan = assign_colorbars(model)
    validate(model, plan)
    assert plan.flush_col_boundaries == {1}
    assert _bars(plan, "vertical") == {((1, 1), (2, 1))} and not _bars(plan, "horizontal")


def test_row_with_different_keys_gets_horizontal_bars():
    model = _model({(1, 1): E, (2, 1): N}, [], {1})
    plan = assign_colorbars(model)
    validate(model, plan)
    assert plan.flush_col_boundaries == {1}
    assert _bars(plan, "horizontal") == {((1, 1),), ((2, 1),)} and not _bars(plan, "vertical")


def test_unshareable_row_gets_vertical_bars():
    model = _model({(1, 1): E, (2, 1): N}, [], set())
    plan = assign_colorbars(model)
    assert plan.flush_col_boundaries == set()
    assert _bars(plan, "vertical") == {((1, 1),), ((2, 1),)}


def test_column_extends_one_vertical_bar():
    model = _model({(1, 1): E, (1, 2): E}, [[(1, 1), (1, 2)]], set())
    plan = assign_colorbars(model)
    validate(model, plan)
    assert _bars(plan, "vertical") == {((1, 1), (1, 2))}


def test_grid_of_one_key_gets_one_bar():
    model = _model({(1, 1): E, (2, 1): E, (1, 2): E, (2, 2): E}, [[(1, 1), (1, 2)], [(2, 1), (2, 2)]], {1})
    plan = assign_colorbars(model)
    validate(model, plan)
    assert plan.flush_col_boundaries == {1}
    [bar] = plan.colorbars
    assert bar.orientation == "vertical" and set(bar.keyed) == set(model.cells)


def test_users_worked_example():
    a, b, c, d = (1, 1), (2, 1), (1, 2), (2, 2)
    model = _model({a: E, b: N, c: E, d: E}, [[a, c], [b, d]], {1})
    plan = assign_colorbars(model)
    validate(model, plan)
    assert plan.flush_col_boundaries == set()
    assert _bars(plan, "vertical") == {(a, c), (b,), (d,)} and not _bars(plan, "horizontal")


def test_horizontal_never_inside_stack():
    """Row 2 would want horizontal bars, but its images sit below lines in their stacks."""
    a, b, c, d = (1, 1), (2, 1), (1, 2), (2, 2)
    model = _model({a: None, b: None, c: E, d: N}, [[a, c], [b, d]], {1})
    plan = assign_colorbars(model)
    validate(model, plan)
    assert plan.flush_col_boundaries == set()
    assert _bars(plan, "vertical") == {(c,), (d,)} and not _bars(plan, "horizontal")


def test_horizontal_bar_keys_its_stack():
    """Row 1 needs horizontal bars; C, flush below A with the same key, shares A's rather than getting its own."""
    a, b, c = (1, 1), (2, 1), (1, 2)
    model = _model({a: E, b: N, c: E}, [[a, c]], {1})
    plan = assign_colorbars(model)
    validate(model, plan)
    assert plan.flush_col_boundaries == {1}
    assert _bars(plan, "horizontal") == {(a, c), (b,)}


def test_lines_need_no_bars():
    model = _model({(1, 1): None, (2, 1): None}, [], {1})
    plan = assign_colorbars(model)
    assert plan.colorbars == [] and plan.flush_col_boundaries == {1}


@pytest.mark.parametrize("seed", range(200))
def test_every_image_keyed_once(seed: int):
    rng = random.Random(seed)
    ncols, nrows = rng.randint(1, 3), rng.randint(1, 3)
    keys = {(col, row): rng.choice([E, N, None]) for col, row in itertools.product(range(1, ncols + 1), range(1, nrows + 1)) if rng.random() < 0.85}
    flush_rows = {row for row in range(1, nrows) if rng.random() < 0.5}
    stacks = []
    for col in range(1, ncols + 1):
        for row in range(1, nrows + 1):
            if (col, row) not in keys:
                continue
            if stacks and stacks[-1][-1] == (col, row - 1) and row - 1 in flush_rows:
                stacks[-1].append((col, row))
            else:
                stacks.append([(col, row)])
    model = GridModel({loc: CellModel(loc, key) for loc, key in keys.items()}, stacks, {col for col in range(1, ncols) if rng.random() < 0.6})
    validate(model, assign_colorbars(model))
