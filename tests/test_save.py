import pytest
from conftest import make_save


def test_save_static_png(tmp_path):
    """Saving a static plot produces a .png file."""
    path = make_save("pfd hx_fc -i t=-1 -v y time=".split(), tmp_path, "png")
    assert path.exists()
    assert path.suffix == ".png"


def test_save_animated_gif(tmp_path):
    """Saving an animated plot as gif produces a file with the correct number of frames."""
    from PIL import Image

    path = make_save("pfd hx_fc -v y".split(), tmp_path, "gif")
    assert path.exists()
    assert path.suffix == ".gif"

    with Image.open(path) as img:
        assert img.n_frames == 11
