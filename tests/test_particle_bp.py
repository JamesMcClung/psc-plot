"""Tests for ParticleLoaderBp registration and loading."""

import numpy as np
import pytest
from synthetic_particles import write_steps_bp

from lib.config import CONFIG
from lib.data.loaders.particle_bp import ParticleLoaderBp
from lib.latex import Latex
from lib.parsing.parse import _get_parser


def test_dynamic_prefix_registration(tmp_path, monkeypatch):
    """Parser's prefix choices should include prt.<species_key> for every
    prt.*.bp species found in CONFIG.data_dir."""
    write_steps_bp(
        tmp_path,
        steps=[0, 1],
        times=[0.0, 1.0],
        species=[("e", -1.0, 1.0, 10), ("i25", 1.0, 25.0, 10)],
    )
    monkeypatch.setattr(CONFIG, "data_dir", tmp_path)

    parser = _get_parser()
    prefix_action = next(a for a in parser._actions if a.dest == "prefix")
    choices = set(prefix_action.choices)
    assert "prt.e" in choices
    assert "prt.i25" in choices


def test_particle_loader_bp_basic(tmp_path, monkeypatch):
    """Loading 3 steps of a single species yields a LazyList with correct
    shape, species dict, subject, and t coord."""
    write_steps_bp(
        tmp_path,
        steps=[0, 1, 2],
        times=[0.0, 0.5, 1.0],
        species=[("e", -1.0, 1.0, 50)],
    )
    monkeypatch.setattr(CONFIG, "data_dir", tmp_path)

    loader = ParticleLoaderBp(prefix="prt.e", active_key="y")
    data = loader.get_data()

    assert len(data.data) == 150
    assert set(data.data.columns) >= {"x", "y", "z", "px", "py", "pz", "w", "t"}
    assert list(data.metadata.species.keys()) == ["e"]
    info = data.metadata.species["e"]
    assert info.q == -1.0 and info.m == 1.0
    assert data.metadata.subject == Latex(r"\text{Electrons}")
    assert np.allclose(sorted(data.metadata.coordss["t"]), [0.0, 0.5, 1.0])
    assert data.metadata.active_key == "y"


def test_particle_loader_bp_mass_suffix_subject(tmp_path, monkeypatch):
    """A non-singleton species key (e.g. 'i25') gets the mass-bearing display."""
    write_steps_bp(
        tmp_path,
        steps=[0],
        times=[0.0],
        species=[("i25", 1.0, 25.0, 10)],
    )
    monkeypatch.setattr(CONFIG, "data_dir", tmp_path)
    loader = ParticleLoaderBp(prefix="prt.i25", active_key=None)
    data = loader.get_data()
    assert data.metadata.species["i25"].m == 25.0
