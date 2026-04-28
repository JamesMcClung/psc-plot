"""Helper for writing synthetic particle HDF5 files in PSC's layout.

Writes the fields that lib.data.loaders.particle_h5 actually reads: the
particle table at /particles/p0/1d plus /particles/idx_begin and /idx_end
so species-discovery can locate particles by species.
"""

from __future__ import annotations

from pathlib import Path

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

# (z, y, x) to match the real-data idx layout: idx_begin.shape == (n_species, z, y, x)
_GDIMS_ZYX = (16, 8, 1)


def write_step(
    path: Path,
    time: float,
    species: list[tuple[float, float, int]],
    seed: int,
) -> None:
    """Write one synthetic particle HDF5 file at `path`.

    `species` is a list of (q, m, n_particles) tuples. Particles are written
    sorted by species: species 0 first, species 1 second, etc. For each
    species s, idx_begin[s, 0, 0, 0] and idx_end[s, 0, 0, 0] bracket its
    slice of /particles/p0/1d; all other (z, y, x) cells are zero/zero.
    """
    rng = np.random.default_rng(seed)
    total = sum(n for _, _, n in species)
    particles = np.empty(total, dtype=_PARTICLE_DTYPE)
    particles["x"] = rng.uniform(0.0, 1.0, total).astype("<f4")
    particles["y"] = rng.uniform(0.0, 1.0, total).astype("<f4")
    particles["z"] = rng.uniform(0.0, 1.0, total).astype("<f4")
    particles["px"] = rng.normal(0.0, 0.1, total).astype("<f4")
    particles["py"] = rng.normal(0.0, 0.1, total).astype("<f4")
    particles["pz"] = rng.normal(0.0, 0.1, total).astype("<f4")
    particles["w"] = np.ones(total, dtype="<f4")
    particles["id"] = np.arange(total, dtype="<u8")
    particles["tag"] = np.zeros(total, dtype="<i4")

    n_species = len(species)
    idx_begin = np.zeros((n_species, *_GDIMS_ZYX), dtype="<u8")
    idx_end = np.zeros((n_species, *_GDIMS_ZYX), dtype="<u8")

    cursor = 0
    for s, (q, m, n) in enumerate(species):
        particles["q"][cursor : cursor + n] = np.float32(q)
        particles["m"][cursor : cursor + n] = np.float32(m)
        idx_begin[s, 0, 0, 0] = cursor
        idx_end[s, 0, 0, 0] = cursor + n
        cursor += n

    with h5py.File(path, "w") as f:
        f.create_dataset("time", data=np.float64(time))
        f.create_dataset("corner", data=np.array([0.0, 0.0, 0.0], dtype="<f8"))
        f.create_dataset("length", data=np.array([1.0, 1.0, 1.0], dtype="<f8"))
        # gdims in (x, y, z) order to match the real-data convention
        f.create_dataset("gdims", data=np.array([_GDIMS_ZYX[2], _GDIMS_ZYX[1], _GDIMS_ZYX[0]], dtype="<i4"))
        f.create_dataset("particles/p0/1d", data=particles)
        f.create_dataset("particles/idx_begin", data=idx_begin)
        f.create_dataset("particles/idx_end", data=idx_end)


def write_steps(
    data_dir: Path,
    steps: list[int],
    times: list[float],
    n_particles_per_step: int,
) -> None:
    """Convenience wrapper: writes one file per (step, time) pair with the
    default two-species layout (half q=+1/m=100 ions, half q=-1/m=1 electrons)."""
    data_dir.mkdir(parents=True, exist_ok=True)
    for step, time in zip(steps, times):
        path = data_dir / f"prt.{step:09d}.h5"
        half = n_particles_per_step // 2
        write_step(path, time, species=[(1.0, 100.0, half), (-1.0, 1.0, n_particles_per_step - half)], seed=step)


from adios2 import Stream


def write_step_bp(
    path: Path,
    time: float,
    step: int,
    species_key: str,
    q: float,
    m: float,
    n_particles: int,
    seed: int,
) -> None:
    """Write one synthetic BP particle file at `path` for a single species.

    Matches PSC's BP layout: per-particle vars x,y,z,px,py,pz,w and file attrs
    name,q,m,time,step,corner,length,gdims.
    """
    rng = np.random.default_rng(seed)
    x = rng.uniform(0.0, 1.0, n_particles).astype(np.float32)
    y = rng.uniform(0.0, 1.0, n_particles).astype(np.float32)
    z = rng.uniform(0.0, 1.0, n_particles).astype(np.float32)
    px = rng.normal(0.0, 0.1, n_particles).astype(np.float32)
    py = rng.normal(0.0, 0.1, n_particles).astype(np.float32)
    pz = rng.normal(0.0, 0.1, n_particles).astype(np.float32)
    w = np.ones(n_particles, dtype=np.float32)

    with Stream(str(path), "w") as s:
        s.write_attribute("name", species_key)
        s.write_attribute("q", np.float32(q))
        s.write_attribute("m", np.float32(m))
        s.write_attribute("time", np.float64(time))
        s.write_attribute("step", np.int32(step))
        s.write_attribute("corner", np.array([0.0, 0.0, 0.0], dtype=np.float64))
        s.write_attribute("length", np.array([1.0, 1.0, 1.0], dtype=np.float64))
        s.write_attribute("gdims", np.array([_GDIMS_ZYX[2], _GDIMS_ZYX[1], _GDIMS_ZYX[0]], dtype=np.int32))
        s.write("x", x)
        s.write("y", y)
        s.write("z", z)
        s.write("px", px)
        s.write("py", py)
        s.write("pz", pz)
        s.write("w", w)


def write_steps_bp(
    data_dir: Path,
    steps: list[int],
    times: list[float],
    species: list[tuple[str, float, float, int]],
) -> None:
    """Convenience wrapper: writes one BP file per (step, species_key) pair.

    `species` is a list of (species_key, q, m, n_particles_per_step) tuples.
    Seeds are deterministic per (step, species_key) to avoid particle-position
    collisions between different species.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    for step, time in zip(steps, times):
        for species_index, (species_key, q, m, n) in enumerate(species):
            path = data_dir / f"prt.{species_key}.{step:09d}.bp"
            write_step_bp(
                path=path,
                time=time,
                step=step,
                species_key=species_key,
                q=q,
                m=m,
                n_particles=n,
                seed=step * 100 + species_index,
            )
