"""Row-level equality test: BP and H5 loaders against the same PSC sim output
must produce identical particle dataframes (up to row ordering)."""

import numpy as np
import pytest

from lib.data.adaptors.species_filter import SpeciesFilter
from lib.data.loaders.particle_bp import ParticleLoaderBp
from lib.data.loaders.particle_h5 import ParticleLoaderH5


def _load_and_filter_h5(species_key: str):
    loader = ParticleLoaderH5(prefix="prt", active_key=None)
    data = loader.get_data()
    return SpeciesFilter(species_key).apply_list(data)


def _load_bp(species_key: str):
    loader = ParticleLoaderBp(prefix=f"prt.{species_key}", active_key=None)
    return loader.get_data()


@pytest.mark.parametrize("species_key", ["i", "e"])
def test_bp_and_h5_yield_identical_particles(species_key):
    """Both loaders, compute + sort by common columns, and compare column-by-
    column. Columns present in both: x, y, z, px, py, pz, w, t."""
    bp = _load_bp(species_key)
    h5 = _load_and_filter_h5(species_key)

    common_cols = ["t", "x", "y", "z", "px", "py", "pz", "w"]
    bp_df = bp.data.compute()[common_cols].sort_values(common_cols).reset_index(drop=True)
    h5_df = h5.data.compute()[common_cols].sort_values(common_cols).reset_index(drop=True)

    assert len(bp_df) == len(h5_df), f"row counts differ: bp={len(bp_df)}, h5={len(h5_df)}"
    for col in common_cols:
        np.testing.assert_allclose(
            bp_df[col].to_numpy(),
            h5_df[col].to_numpy(),
            rtol=0,
            atol=1e-6,
            err_msg=f"column {col!r} mismatches between BP and H5",
        )
