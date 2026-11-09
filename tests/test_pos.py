"""Tests for `--pos` on a variable key of field data, which masks instead of selecting."""

from __future__ import annotations

import numpy as np
import pytest
from conftest import CONFIG_2D

from lib.parsing.parse import parse_args
from lib.run.compile import compile_plot_pipeline


def _pull_active(argv: str):
    return compile_plot_pipeline(parse_args(argv.split()), CONFIG_2D).run_world().require_active_data()


def _bounds(values: np.ndarray) -> tuple[float, float]:
    lo, hi = np.nanquantile(values, [0.25, 0.75])
    return float(lo), float(hi)


def test_pos_masks_active_variable_outside_range():
    raw = _pull_active("pfd hx_fc -v y z").require_active_subdata().values
    lo, hi = _bounds(raw)
    masked = _pull_active(f"pfd hx_fc --pos hx_fc={lo}:{hi} -v y z").require_active_subdata().values

    assert masked.shape == raw.shape
    keep = (raw >= lo) & (raw < hi)
    np.testing.assert_array_equal(masked[keep], raw[keep])
    assert np.isnan(masked[~keep]).all()
    assert keep.any() and (~keep).any()


def test_pos_open_ended_mask():
    raw = _pull_active("pfd hx_fc -v y z").require_active_subdata().values
    lo, _ = _bounds(raw)
    masked = _pull_active(f"pfd hx_fc --pos hx_fc={lo}: -v y z").require_active_subdata().values
    np.testing.assert_array_equal(np.isnan(masked), raw < lo)


def test_pos_masks_by_other_variable():
    hx = _pull_active("pfd hx_fc -v y z").require_active_subdata()
    ey = _pull_active("pfd ey_ec -v y z").require_active_subdata()
    lo, hi = _bounds(hx.values)
    masked = _pull_active(f"pfd ey_ec --pos hx_fc={lo}:{hi} -v y z").require_active_subdata()

    hx, ey, masked = (da.transpose(*ey.dims) for da in (hx, ey, masked))
    keep = ((hx >= lo) & (hx < hi)).values
    np.testing.assert_array_equal(masked.values[keep], ey.values[keep])
    assert np.isnan(masked.values[~keep]).all()


def test_pos_mask_combines_with_dim_selection():
    raw = _pull_active("pfd hx_fc --pos y=0: -v y z").require_active_subdata().values
    lo, hi = _bounds(raw)
    masked = _pull_active(f"pfd hx_fc --pos y=0: hx_fc={lo}:{hi} -v y z").require_active_subdata().values
    assert masked.shape == raw.shape
    np.testing.assert_array_equal(np.isnan(masked), ~((raw >= lo) & (raw < hi)))


def test_pos_mask_rejects_single_value():
    with pytest.raises(ValueError, match="range"):
        _pull_active("pfd hx_fc --pos hx_fc=1 -v y z")


def test_pos_without_key_masks_active_variable():
    raw = _pull_active("pfd hx_fc -v y z").require_active_subdata().values
    lo, hi = _bounds(raw)
    explicit = _pull_active(f"pfd hx_fc --pos hx_fc={lo}:{hi} -v y z").require_active_subdata().values
    implicit = _pull_active(f"pfd hx_fc --pos {lo}:{hi} -v y z").require_active_subdata().values
    np.testing.assert_array_equal(implicit, explicit)


def test_pos_without_key_filters_active_column():
    explicit = _pull_active("prt.e py --pos py=0: -v y z")
    implicit = _pull_active("prt.e py --pos 0: -v y z")
    assert len(implicit.data) == len(explicit.data) < len(_pull_active("prt.e py -v y z").data)


def test_pos_without_key_name_fragment():
    pipeline = compile_plot_pipeline(parse_args("pfd hx_fc --pos 1:2 y=0: -v y z".split()), CONFIG_2D)
    assert "pos_1.0_2.0_y=0.0" in pipeline.get_save_file_stem()


def test_pos_without_key_accepts_negative_lower_bound():
    raw = _pull_active("pfd hx_fc -v y z").require_active_subdata().values
    masked = _pull_active("pfd hx_fc --pos -1e9:0 -v y z").require_active_subdata().values
    np.testing.assert_array_equal(np.isnan(masked), raw >= 0)
