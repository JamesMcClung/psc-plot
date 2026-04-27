"""Sanity-check that the synthetic writer produces files loadable by lib."""

import h5py
import numpy as np
import pytest
from synthetic_particles import write_step, write_steps


def test_writer_produces_loadable_files(tmp_path):
    write_steps(tmp_path, steps=[0, 1], times=[0.0, 1.0], n_particles_per_step=1000)

    for step in (0, 1):
        path = tmp_path / f"prt.{step:09d}.h5"
        assert path.exists()
        with h5py.File(path) as f:
            assert f["time"][()] == pytest.approx(float(step))
            assert f["particles/p0/1d"].shape == (1000,)
            assert set(f["particles/p0/1d"].dtype.names) >= {"x", "y", "z", "px", "py", "pz", "q", "m", "w"}


def test_writer_file_size_scales_with_n_particles(tmp_path):
    """Each particle is 56 bytes; a file with N particles should be close to N*56 plus HDF5 overhead (well under 2x)."""
    n = 100_000
    write_steps(tmp_path, steps=[0], times=[0.0], n_particles_per_step=n)
    size = (tmp_path / "prt.000000000.h5").stat().st_size
    # particle payload is n * 56 bytes ≈ 5.6 MB for n=100_000; overhead should be a fraction of that
    assert n * 56 < size < n * 56 * 2


def test_writer_emits_idx_begin_end_with_species_shape(tmp_path):
    path = tmp_path / "prt.000000000.h5"
    write_step(path, time=0.0, species=[(1.0, 100.0, 50), (-1.0, 1.0, 50)], seed=0)
    with h5py.File(path) as f:
        idx_begin = f["particles/idx_begin"][...]
        idx_end = f["particles/idx_end"][...]
    # shape is (n_species, gdims_z, gdims_y, gdims_x); gdims=(1,8,16) in the writer
    assert idx_begin.shape == (2, 16, 8, 1)
    assert idx_end.shape == (2, 16, 8, 1)
    # species 0: particles [0, 50); species 1: particles [50, 100). Both recorded at cell (0,0,0).
    assert idx_begin[0, 0, 0, 0] == 0
    assert idx_end[0, 0, 0, 0] == 50
    assert idx_begin[1, 0, 0, 0] == 50
    assert idx_end[1, 0, 0, 0] == 100


def test_writer_particles_sorted_by_species(tmp_path):
    path = tmp_path / "prt.000000000.h5"
    write_step(path, time=0.0, species=[(1.0, 100.0, 30), (-1.0, 1.0, 70)], seed=0)
    with h5py.File(path) as f:
        particles = f["particles/p0/1d"][...]
    # First 30 rows are species 0 (q=+1); remaining are species 1 (q=-1).
    assert np.all(particles["q"][:30] == 1.0)
    assert np.all(particles["m"][:30] == 100.0)
    assert np.all(particles["q"][30:] == -1.0)
    assert np.all(particles["m"][30:] == 1.0)
