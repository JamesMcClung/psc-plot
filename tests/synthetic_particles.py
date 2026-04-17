"""Helper for writing synthetic particle HDF5 files in PSC's layout.

Only includes the fields that lib.particle_util actually reads, so downstream
adaptors (species filter on `q`, bin on any column) work as-is.
"""
from __future__ import annotations

import pathlib

import h5py
import numpy as np

_PARTICLE_DTYPE = np.dtype(
    {
        "names": ["x", "y", "z", "px", "py", "pz", "q", "m", "w", "id", "tag"],
        "formats": ["<f4"] * 9 + ["<u8", "<i4"],
        "offsets": [0, 4, 8, 12, 16, 20, 24, 28, 32, 40, 48],
        "itemsize": 56,
    }
)


def write_step(path: pathlib.Path, time: float, n_particles: int, seed: int) -> None:
    """Write one synthetic particle HDF5 file at `path`.

    Half the particles are ions (q=+1) and half are electrons (q=-1), so
    --species ion and --species electron both have data to work with.
    """
    rng = np.random.default_rng(seed)
    particles = np.empty(n_particles, dtype=_PARTICLE_DTYPE)
    particles["x"] = rng.uniform(0.0, 1.0, n_particles).astype("<f4")
    particles["y"] = rng.uniform(0.0, 1.0, n_particles).astype("<f4")
    particles["z"] = rng.uniform(0.0, 1.0, n_particles).astype("<f4")
    particles["px"] = rng.normal(0.0, 0.1, n_particles).astype("<f4")
    particles["py"] = rng.normal(0.0, 0.1, n_particles).astype("<f4")
    particles["pz"] = rng.normal(0.0, 0.1, n_particles).astype("<f4")
    particles["q"] = np.where(np.arange(n_particles) % 2 == 0, 1.0, -1.0).astype("<f4")
    particles["m"] = np.where(particles["q"] > 0, 100.0, 1.0).astype("<f4")
    particles["w"] = np.ones(n_particles, dtype="<f4")
    particles["id"] = np.arange(n_particles, dtype="<u8")
    particles["tag"] = np.zeros(n_particles, dtype="<i4")

    with h5py.File(path, "w") as f:
        f.create_dataset("time", data=np.float64(time))
        f.create_dataset("corner", data=np.array([0.0, 0.0, 0.0], dtype="<f8"))
        f.create_dataset("length", data=np.array([1.0, 1.0, 1.0], dtype="<f8"))
        f.create_dataset("gdims", data=np.array([1, 8, 16], dtype="<i4"))
        f.create_dataset("particles/p0/1d", data=particles)


def write_steps(data_dir: pathlib.Path, steps: list[int], times: list[float], n_particles_per_step: int) -> None:
    """Write one `prt.<step>.h5` file for each (step, time) pair into `data_dir`."""
    data_dir.mkdir(parents=True, exist_ok=True)
    for step, time in zip(steps, times):
        path = data_dir / f"prt.{step:09d}.h5"
        write_step(path, time, n_particles_per_step, seed=step)
