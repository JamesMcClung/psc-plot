import argparse

import numpy as np
import pytest
import xarray as xr
from conftest import CONFIG_2D

from lib.data.adaptors.fourier import Fourier, parse_fourier
from lib.data.loader import load


def _pfd_hy():
    return load(CONFIG_2D, "pfd").with_active(key="hy_fc")


def test_parse_dims_with_angles():
    assert parse_fourier(["y=rad", "z=rev"]).dims == {"y": "rad", "z": "rev"}


@pytest.mark.parametrize("arg", ["y", "y=deg", "y="])
def test_parse_requires_angle(arg):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_fourier([arg])


def test_rev_coords_are_rad_coords_over_2pi():
    rad = Fourier({"y": "rad"}).apply(_pfd_hy())["hy_fc"]
    rev = Fourier({"y": "rev"}).apply(_pfd_hy())["hy_fc"]
    np.testing.assert_allclose(rev.coords["k_y"], rad.coords["k_y"] / (2 * np.pi))
    np.testing.assert_allclose(rev.values, rad.values)


@pytest.mark.parametrize("angle", ["rad", "rev"])
def test_inverse_restores_dim_info(angle):
    data = _pfd_hy()
    inverse = Fourier({"k_y": angle}).apply(Fourier({"y": angle}).apply(data))
    assert inverse.metadata.var_infos["y"] == data.metadata.var_infos["y"]


def test_inverse_angle_must_match():
    k_data = Fourier({"y": "rad"}).apply(_pfd_hy())
    with pytest.raises(ValueError, match="k_y is in rad"):
        Fourier({"k_y": "rev"}).apply(k_data)


def test_name_fragment_includes_angles():
    assert Fourier({"y": "rad", "z": "rev"}).get_name_fragments() == ["fourier_y=rad,z=rev"]


@pytest.mark.parametrize("angle", ["rad", "rev"])
def test_inverse_restores_data_and_coords(angle):
    data = _pfd_hy()
    inverse = Fourier({"k_y": angle}).apply(Fourier({"y": angle}).apply(data))
    xr.testing.assert_allclose(inverse["hy_fc"].real.transpose(*data["hy_fc"].dims), data["hy_fc"])


def _hy_with_ny(ny: int):
    data = _pfd_hy()
    return data.with_active(data=data["hy_fc"].isel(y=slice(0, ny)))


def test_parse_options():
    assert parse_fourier(["dropnyquist", "y=rad"]).drop_nyquist


@pytest.mark.parametrize("arg", ["nyquist", "dropnyquist=1"])
def test_parse_rejects_unknown_option(arg):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_fourier([arg, "y=rad"])


def test_dropnyquist_drops_lowest_mode_of_even_length_dim():
    full = Fourier({"y": "rad"}).apply(_hy_with_ny(8))["hy_fc"]
    dropped = Fourier({"y": "rad"}, drop_nyquist=True).apply(_hy_with_ny(8))["hy_fc"]
    assert full.sizes["k_y"] == 8
    xr.testing.assert_equal(dropped, full.isel(k_y=slice(1, None)))
    np.testing.assert_allclose(dropped.coords["k_y"], -dropped.coords["k_y"][::-1])


def test_dropnyquist_keeps_every_mode_of_odd_length_dim():
    full = Fourier({"y": "rad"}).apply(_hy_with_ny(7))["hy_fc"]
    dropped = Fourier({"y": "rad"}, drop_nyquist=True).apply(_hy_with_ny(7))["hy_fc"]
    xr.testing.assert_equal(dropped, full)


def test_dropnyquist_rejects_inverse():
    k_data = Fourier({"y": "rad"}).apply(_pfd_hy())
    with pytest.raises(ValueError, match="dropnyquist"):
        Fourier({"k_y": "rad"}, drop_nyquist=True).apply(k_data)


def test_name_fragment_includes_options():
    assert Fourier({"y": "rad"}, drop_nyquist=True).get_name_fragments() == ["fourier_dropnyquist_y=rad"]


def test_parse_requires_a_dim():
    with pytest.raises(argparse.ArgumentTypeError, match="at least one"):
        parse_fourier(["dropnyquist"])


@pytest.mark.parametrize("ny", [7, 8])
def test_positiveonly_keeps_strictly_positive_modes(ny):
    full = Fourier({"y": "rad"}).apply(_hy_with_ny(ny))["hy_fc"]
    positive = Fourier({"y": "rad"}, positive_only=True).apply(_hy_with_ny(ny))["hy_fc"]
    xr.testing.assert_equal(positive, full.where(full.k_y > 0, drop=True))
    assert positive.sizes["k_y"] == 3


def test_positiveonly_rejects_inverse():
    k_data = Fourier({"y": "rad"}).apply(_pfd_hy())
    with pytest.raises(ValueError, match="positiveonly"):
        Fourier({"k_y": "rad"}, positive_only=True).apply(k_data)


def test_parse_positiveonly():
    assert parse_fourier(["positiveonly", "y=rad"]).positive_only


def test_name_fragment_orders_options():
    fourier = parse_fourier(["dropnyquist", "positiveonly", "y=rad"])
    assert fourier.get_name_fragments() == ["fourier_positiveonly_dropnyquist_y=rad"]


def test_display_wraps_active_var_by_default():
    data = Fourier({"y": "rad"}).apply(_pfd_hy())
    assert data.active_info.display.latex == "\\mathcal{F}_{y}[B_y]"


def test_nodisplay_keeps_active_var_display():
    data = parse_fourier(["nodisplay", "y=rad"]).apply(_pfd_hy())
    assert data.active_info.display.latex == "B_y"
    assert data.metadata.var_infos["k_y"].display.latex == "k_y"


def test_nodisplay_allows_inverse():
    k_data = Fourier({"y": "rad"}).apply(_pfd_hy())
    assert Fourier({"k_y": "rad"}, no_display=True).apply(k_data).active_info.display.latex == "\\mathcal{F}_{y}[B_y]"


def test_name_fragment_puts_nodisplay_first():
    fourier = parse_fourier(["positiveonly", "nodisplay", "y=rad"])
    assert fourier.get_name_fragments() == ["fourier_nodisplay_positiveonly_y=rad"]
