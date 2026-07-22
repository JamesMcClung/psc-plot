"""Tests the species-discovery path in ParticleLoaderH5."""

from __future__ import annotations

from pathlib import Path

import pytest
from synthetic_particles import write_step

from lib.config import PscPlotConfig
from lib.data.loaders.particle_h5 import ParticleLoaderH5


def test_h5_species_discovery_standard(tmp_path: Path):
    write_step(tmp_path / "prt.000000000.h5", time=0.0, species=[(-1.0, 1.0, 10), (1.0, 100.0, 10)], seed=0)
    loader = ParticleLoaderH5("prt", active_key=None)
    data = loader.get_data(PscPlotConfig(data_dir=tmp_path))
    assert set(data.metadata.species.keys()) == {"e", "i"}
    e = data.metadata.species["e"]
    i = data.metadata.species["i"]
    assert e.q == -1.0 and e.m == 1.0
    assert i.q == 1.0 and i.m == 100.0


def test_h5_species_discovery_multiple_ion_masses(tmp_path: Path):
    write_step(
        tmp_path / "prt.000000000.h5",
        time=0.0,
        species=[(-1.0, 1.0, 10), (1.0, 25.0, 10), (1.0, 100.0, 10)],
        seed=0,
    )
    loader = ParticleLoaderH5("prt", active_key=None)
    data = loader.get_data(PscPlotConfig(data_dir=tmp_path))
    assert set(data.metadata.species.keys()) == {"e", "i25", "i100"}
    assert data.metadata.species["i25"].m == 25.0
    assert data.metadata.species["i100"].m == 100.0


def test_h5_species_discovery_multiple_ion_charges(tmp_path: Path):
    write_step(
        tmp_path / "prt.000000000.h5",
        time=0.0,
        species=[(-1.0, 1.0, 10), (1.0, 100.0, 10), (2.0, 100.0, 10)],
        seed=0,
    )
    loader = ParticleLoaderH5("prt", active_key=None)
    data = loader.get_data(PscPlotConfig(data_dir=tmp_path))
    assert set(data.metadata.species.keys()) == {"e", "i+", "i++"}
    assert data.metadata.species["i+"].q == 1.0
    assert data.metadata.species["i++"].q == 2.0


def test_h5_species_discovery_multiple_ion_everything(tmp_path: Path):
    write_step(
        tmp_path / "prt.000000000.h5",
        time=0.0,
        species=[(-1.0, 1.0, 10), (1.0, 25.0, 10), (1.0, 100.0, 10), (2.0, 100.0, 10)],
        seed=0,
    )
    loader = ParticleLoaderH5("prt", active_key=None)
    data = loader.get_data(PscPlotConfig(data_dir=tmp_path))
    assert set(data.metadata.species.keys()) == {"e", "i+25", "i+100", "i++100"}
    assert data.metadata.species["i+25"].q == 1.0
    assert data.metadata.species["i+25"].m == 25.0
    assert data.metadata.species["i+100"].q == 1.0
    assert data.metadata.species["i+100"].m == 100.0
    assert data.metadata.species["i++100"].q == 2.0
    assert data.metadata.species["i++100"].m == 100.0


def test_h5_species_discovery_electron_merge_warns(tmp_path: Path):
    write_step(
        tmp_path / "prt.000000000.h5",
        time=0.0,
        species=[(-1.0, 1.0, 10), (-1.0, 1.0, 10)],
        seed=0,
    )
    loader = ParticleLoaderH5("prt", active_key=None)
    with pytest.warns(UserWarning, match="merging"):
        data = loader.get_data(PscPlotConfig(data_dir=tmp_path))
    assert set(data.metadata.species.keys()) == {"e"}


def test_h5_species_discovery_species_at_different_times(tmp_path: Path):
    # step 0: only species 0 has particles; step 1: only species 1 has particles.
    write_step(tmp_path / "prt.000000000.h5", time=0.0, species=[(-1.0, 1.0, 10), (1.0, 1.0, 0)], seed=0)
    write_step(tmp_path / "prt.000000001.h5", time=1.0, species=[(-1.0, 1.0, 0), (1.0, 1.0, 10)], seed=1)
    loader = ParticleLoaderH5("prt", active_key=None)
    data = loader.get_data(PscPlotConfig(data_dir=tmp_path))
    assert set(data.metadata.species.keys()) == {"e", "i"}
