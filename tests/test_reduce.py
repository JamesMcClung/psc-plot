"""Tests for `--reduce`'s display label (also used by `-v`'s implicit mean)."""

from __future__ import annotations

from conftest import CONFIG_2D

from lib.parsing.parse import parse_args
from lib.run.compile import compile_plot_pipeline


def _active_display(argv: str) -> str:
    world = compile_plot_pipeline(parse_args(argv.split()), CONFIG_2D).run_world()
    return world.require_active_data().metadata.active_var_info.display.latex


def test_label_uses_dim_displays():
    # theta's key is "theta", its display "\theta"
    display = _active_display("pfd hx_fc --fourier y,z=rad --transform-polar k_y k_z -v k_p")
    assert display.endswith(r"\rangle_{\theta}"), display


def test_label_skips_length_1_dims():
    # test-2d has nx = 1, so averaging over x is a no-op and shouldn't be labeled
    display = _active_display("pfd hx_fc --reduce x,z=mean -v y")
    assert display.endswith(r"\rangle_{z}"), display


def test_label_omitted_when_every_dim_has_length_1():
    display = _active_display("pfd hx_fc --reduce x=mean -v y z")
    assert r"\langle" not in display, display
