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
