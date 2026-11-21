"""`get_contrasting_color`: the color perceptually farthest (in OKLab) from everything beneath."""

import numpy as np
import pytest

from lib.plotting.plt_util import _srgb_to_oklab, get_contrasting_color


def _distance(rgb, beneath: np.ndarray) -> float:
    """The least OKLab distance from `rgb` to any of `beneath`."""
    return float(np.min(np.linalg.norm(_srgb_to_oklab(beneath[:, :3]) - _srgb_to_oklab(np.array(rgb)[None, :]), axis=1)))


def _rgba(*rgbs) -> np.ndarray:
    return np.array([[*rgb, 1.0] for rgb in rgbs])


@pytest.mark.parametrize("rgb, expected", [((1, 1, 1), (0, 0, 0)), ((0, 0, 0), (1, 1, 1))])
def test_extremes_get_the_other_extreme(rgb, expected):
    assert get_contrasting_color(_rgba(rgb)) == pytest.approx(expected)


@pytest.mark.parametrize("rgb", [(0.5, 0.5, 0.5), (0.4, 0.45, 0.5), (0.8, 0.2, 0.2), (0.2, 0.3, 0.8), (0.1, 0.6, 0.3)])
def test_at_least_as_far_as_black_or_white(rgb):
    beneath = _rgba(rgb)
    assert _distance(get_contrasting_color(beneath), beneath) >= max(_distance((0, 0, 0), beneath), _distance((1, 1, 1), beneath)) - 1e-9


def test_saturated_blue_gets_a_color():
    """Pure blue is of middling lightness, so neither black nor white stands out much; yellow does better."""
    beneath = _rgba((0.0, 0.0, 1.0))
    assert _distance(get_contrasting_color(beneath), beneath) > max(_distance((0, 0, 0), beneath), _distance((1, 1, 1), beneath)) + 0.02


def test_far_from_every_color_beneath():
    """A tick over two colors stands out from both, not from their average."""
    beneath = _rgba((1, 1, 1), (0, 0, 0))
    result = get_contrasting_color(beneath)
    assert _distance(result, beneath) > 0.3


@pytest.mark.parametrize("rgb", [(0.47, 0.02, 0.13), (0.05, 0.24, 0.45)])
def test_near_tie_stays_neutral(rgb):
    """RdBu's dark ends: yellow is only a few percent farther than white, not enough to be worth a hue."""
    assert get_contrasting_color(_rgba(rgb)) == pytest.approx((1.0, 1.0, 1.0))
