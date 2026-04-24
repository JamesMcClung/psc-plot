"""Smoke test for the synthetic BP particle writer."""
import xarray as xr

from synthetic_particles import write_step_bp


def test_write_step_bp_roundtrips_via_xarray(tmp_path):
    path = tmp_path / "prt.e.000000000.bp"
    write_step_bp(
        path=path,
        time=1.5,
        step=42,
        species_key="e",
        q=-1.0,
        m=1.0,
        n_particles=100,
        seed=0,
    )
    ds = xr.open_dataset(path)
    assert set(ds.data_vars) == {"x", "y", "z", "px", "py", "pz", "w"}
    for name in ("x", "y", "z", "px", "py", "pz", "w"):
        sizes = [n for n in ds[name].shape if n > 1]
        assert sizes == [100], f"{name} has shape {ds[name].shape}"
    assert ds.attrs["name"] == "e"
    assert float(ds.attrs["q"]) == -1.0
    assert float(ds.attrs["m"]) == 1.0
    assert float(ds.attrs["time"]) == 1.5
    assert int(ds.attrs["step"]) == 42
