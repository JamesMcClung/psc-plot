"""An empty display (e.g. a `--fit` curve's) stays empty through every display modifier except `--display`."""

import pytest
from conftest import CONFIG_2D

from lib.data.loader import load
from lib.latex import Latex
from lib.parsing.parse import parse_steps


def _blank_hx():
    pfd = load(CONFIG_2D, "pfd").with_active(key="hx_fc")
    return pfd.with_active(info=pfd.active_info.assign(display=Latex("")))


@pytest.mark.parametrize("step", ["--mag", "--real", "--imag", "--diff y=+", "--pow 2", "--log", "--exp 2"])
def test_metadata_adaptor_keeps_empty_display(step):
    [adaptor] = parse_steps([step])
    assert not adaptor.apply(_blank_hx()).active_info.display


def test_fourier_keeps_empty_display():
    [adaptor] = parse_steps(["--fourier y=rev"])
    assert not adaptor.apply(_blank_hx()).active_info.display


def test_reduce_keeps_empty_display():
    [adaptor] = parse_steps(["--reduce y=mean"])
    assert not adaptor.apply(_blank_hx()).active_info.display


def test_display_sets_and_replaces_empty_display():
    [blank] = parse_steps(["--display hx_fc="])
    assert not blank.apply(load(CONFIG_2D, "pfd").with_active(key="hx_fc")).active_info.display
    [named] = parse_steps(["--display B"])
    assert named.apply(_blank_hx()).active_info.display == Latex("B")
