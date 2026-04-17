"""Sanity-check that the synthetic writer produces files loadable by lib."""
import h5py
import pytest

from synthetic_particles import write_steps


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
