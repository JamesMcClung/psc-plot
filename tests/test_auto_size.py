import numpy as np
import pytest

from lib.latex import Latex
from lib.plotting.layout.auto_size import auto_plot_size, is_aspect_locked
from lib.plotting.plot_info import ImageInfo, LineInfo, PolarMeshInfo

DEFAULT_AREA = 5.0 * 3.75


def _image(nx: int, ny: int, x_extent: float, y_extent: float, *, same_unit: bool) -> ImageInfo:
    return ImageInfo(
        data=np.zeros((ny, nx)),
        x_dim="y",
        y_dim="z",
        color_dim="f",
        dim_bounds={"y": (0.0, x_extent), "z": (0.0, y_extent), "f": (0.0, 1.0)},
        dim_units={"y": Latex("d_e"), "z": Latex("d_e" if same_unit else "d_i"), "f": Latex("")},
    )


def test_line_panel_gets_default_size():
    line = LineInfo(x_dim="y", y_dim="f", x_data=np.zeros(3), y_data=np.zeros(3), dim_units={"y": Latex("d_e"), "f": Latex("")})
    assert auto_plot_size([line], 100) == pytest.approx((5.0, 3.75))


def test_small_image_gets_default_area():
    assert auto_plot_size([_image(16, 8, 1.0, 1.0, same_unit=False)], 100) == pytest.approx((5.0, 3.75))


def test_equal_scale_image_keeps_data_aspect():
    w, h = auto_plot_size([_image(16, 8, 2.0, 1.0, same_unit=True)], 100)
    assert w / h == pytest.approx(2.0)
    assert w * h == pytest.approx(DEFAULT_AREA)


def test_equal_scale_dropped_past_2_5():
    """Past 2.5:1, equal scale is given up entirely: each side is sized on its own, as if the units differed."""
    infos = [_image(16, 8, 10.0, 1.0, same_unit=True)]
    assert auto_plot_size(infos, 100) == pytest.approx((5.0, 3.75))
    assert not is_aspect_locked(infos)


def test_equal_scale_kept_at_2_5():
    infos = [_image(16, 8, 2.5, 1.0, same_unit=True)]
    w, h = auto_plot_size(infos, 100)
    assert w / h == pytest.approx(2.5)
    assert is_aspect_locked(infos)


def test_long_thin_image_sizes_sides_independently():
    """A 1024x1 image with equal units (e.g. a 1D run plotted vs y and z) doesn't stretch its one row tall."""
    w, h = auto_plot_size([_image(1024, 1, 12.8, 0.0125, same_unit=True)], 100)
    assert (w, h) == pytest.approx((20.48, 3.75))


def test_big_image_two_dots_per_cell():
    w, h = auto_plot_size([_image(2048, 1024, 1.0, 1.0, same_unit=False)], 100)
    assert w >= 40.96
    assert h >= 20.48


def test_big_image_minimum_depends_on_dpi():
    w, h = auto_plot_size([_image(2048, 1024, 1.0, 1.0, same_unit=False)], 200)
    assert (w, h) == pytest.approx((20.48, 10.24))


def test_big_equal_scale_image_scales_uniformly():
    w, h = auto_plot_size([_image(2048, 1024, 2.0, 1.0, same_unit=True)], 100)
    assert w / h == pytest.approx(2.0)
    assert w >= 40.96


def test_polar_panel_is_square():
    polar = PolarMeshInfo(data=np.zeros((4, 4)), r_vertices=np.arange(5.0), theta_vertices=np.arange(5.0), r_dim="r", theta_dim="theta", color_dim="f")
    assert auto_plot_size([polar], 100) == pytest.approx((4.5, 4.5))


def test_equal_scale_survives_rounding_between_panels():
    """Two images whose aspects differ only by float rounding (0.4 - 0.1 != 0.3) still share equal scale."""
    a = _image(16, 8, 0.3, 0.5, same_unit=True)
    b = _image(16, 8, 0.3, 0.5, same_unit=True)
    b.dim_bounds["y"] = (0.1, 0.4)
    assert is_aspect_locked([a, b])
