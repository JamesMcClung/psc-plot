"""Tests the species-discovery path in ParticleLoaderH5."""

from __future__ import annotations

from pathlib import Path

import pytest
from synthetic_particles import write_step

from lib.config import CONFIG
from lib.data.loaders.particle_h5 import ParticleLoaderH5


@pytest.fixture
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point CONFIG.data_dir at tmp_path for the duration of one test."""
    monkeypatch.setattr(CONFIG, "data_dir", tmp_path)
    return tmp_path


def test_h5_species_discovery_standard(isolated_data_dir: Path):
    write_step(isolated_data_dir / "prt.000000000.h5", time=0.0, species=[(-1.0, 1.0, 10), (1.0, 100.0, 10)], seed=0)
    loader = ParticleLoaderH5("prt", active_key=None)
    data = loader.get_data()
    assert set(data.metadata.species.keys()) == {"e", "i"}
    e = data.metadata.species["e"]
    i = data.metadata.species["i"]
    assert e.q == -1.0 and e.m == 1.0
    assert i.q == 1.0 and i.m == 100.0


def test_h5_species_discovery_multiple_ion_masses(isolated_data_dir: Path):
    write_step(
        isolated_data_dir / "prt.000000000.h5",
        time=0.0,
        species=[(-1.0, 1.0, 10), (1.0, 25.0, 10), (1.0, 100.0, 10)],
        seed=0,
    )
    loader = ParticleLoaderH5("prt", active_key=None)
    data = loader.get_data()
    assert set(data.metadata.species.keys()) == {"e", "i25", "i100"}
    assert data.metadata.species["i25"].m == 25.0
    assert data.metadata.species["i100"].m == 100.0


def test_h5_species_discovery_multiple_ion_charges(isolated_data_dir: Path):
    write_step(
        isolated_data_dir / "prt.000000000.h5",
        time=0.0,
        species=[(-1.0, 1.0, 10), (1.0, 100.0, 10), (2.0, 100.0, 10)],
        seed=0,
    )
    loader = ParticleLoaderH5("prt", active_key=None)
    data = loader.get_data()
    assert set(data.metadata.species.keys()) == {"e", "i+", "i++"}
    assert data.metadata.species["i+"].q == 1.0
    assert data.metadata.species["i++"].q == 2.0


def test_h5_species_discovery_multiple_ion_everything(isolated_data_dir: Path):
    write_step(
        isolated_data_dir / "prt.000000000.h5",
        time=0.0,
        species=[(-1.0, 1.0, 10), (1.0, 25.0, 10), (1.0, 100.0, 10), (2.0, 100.0, 10)],
        seed=0,
    )
    loader = ParticleLoaderH5("prt", active_key=None)
    data = loader.get_data()
    assert set(data.metadata.species.keys()) == {"e", "i+25", "i+100", "i++100"}
    assert data.metadata.species["i+25"].q == 1.0
    assert data.metadata.species["i+25"].m == 25.0
    assert data.metadata.species["i+100"].q == 1.0
    assert data.metadata.species["i+100"].m == 100.0
    assert data.metadata.species["i++100"].q == 2.0
    assert data.metadata.species["i++100"].m == 100.0


def test_h5_species_discovery_electron_merge_warns(isolated_data_dir: Path):
    write_step(
        isolated_data_dir / "prt.000000000.h5",
        time=0.0,
        species=[(-1.0, 1.0, 10), (-1.0, 1.0, 10)],
        seed=0,
    )
    loader = ParticleLoaderH5("prt", active_key=None)
    with pytest.warns(UserWarning, match="merging"):
        data = loader.get_data()
    assert set(data.metadata.species.keys()) == {"e"}


def test_h5_species_discovery_species_at_different_times(isolated_data_dir: Path):
    # step 0: only species 0 has particles; step 1: only species 1 has particles.
    write_step(isolated_data_dir / "prt.000000000.h5", time=0.0, species=[(-1.0, 1.0, 10), (1.0, 1.0, 0)], seed=0)
    write_step(isolated_data_dir / "prt.000000001.h5", time=1.0, species=[(-1.0, 1.0, 0), (1.0, 1.0, 10)], seed=1)
    loader = ParticleLoaderH5("prt", active_key=None)
    data = loader.get_data()
    assert set(data.metadata.species.keys()) == {"e", "i"}
