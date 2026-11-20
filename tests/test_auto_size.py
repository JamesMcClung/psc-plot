import numpy as np
import pytest

from lib.latex import Latex
from lib.plotting.layout.auto_size import auto_plot_size
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


def test_equal_scale_clamped_at_2_5():
    w, h = auto_plot_size([_image(16, 8, 10.0, 1.0, same_unit=True)], 100)
    assert w / h == pytest.approx(2.5)


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
