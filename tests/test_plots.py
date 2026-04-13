import pytest
from conftest import make_plot

MPL_KWARGS = dict(tolerance=2, savefig_kwarg={"dpi": 100}, style="default")


# --- Static 1D field ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_static_1d_rho_i():
    return make_plot(["pfd_moments", "rho_i", "-v", "y", "time="])


# --- Animated 1D field ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_1d_hx():
    return make_plot(["pfd", "hx_fc", "-v", "y"])


# --- Animated 2D field ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_2d_hx():
    return make_plot(["pfd", "hx_fc", "-v", "y", "z"])


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_2d_hx_3d():
    return make_plot(["pfd", "hx_fc", "-v", "y", "z"], data_dir="test-3d")


# --- Animated scatter ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_scatter_ion():
    return make_plot(["prt", "--species", "ion", "-v", "y", "py"])


# --- Hooks on static 1D ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_static_1d_with_grid():
    return make_plot(["pfd_moments", "rho_i", "-v", "y", "time=", "--grid", "y"])


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_static_1d_with_vline():
    return make_plot(["pfd_moments", "rho_i", "-v", "y", "time=", "--vline", "0.5=half"])


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_static_1d_with_scale():
    return make_plot(["pfd_moments", "rho_i", "-v", "y", "time=", "--scale", "symlog"])


# --- Hooks on animated ---


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_1d_with_scale():
    return make_plot(["pfd", "hx_fc", "-v", "y", "--scale", "symlog"])


@pytest.mark.mpl_image_compare(**MPL_KWARGS)
def test_animated_2d_with_scale():
    return make_plot(["pfd", "hx_fc", "-v", "y", "z", "--scale", "symlog"])
