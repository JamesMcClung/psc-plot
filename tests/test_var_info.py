import pytest

from lib.latex import Latex
from lib.scale import LogScale
from lib.var_info import VarInfo

Y = VarInfo(Latex("y"), Latex("d_\\text{e}"), "linear")
T = VarInfo(Latex("t"), Latex("\\omega_\\text{pe}^{-1}"), "linear")


@pytest.mark.parametrize("angle", ["rad", "rev"])
def test_to_fourier_divides_unit_by_angle(angle):
    k_y = Y.to_fourier(angle)
    assert (k_y.key, k_y.display.latex, k_y.unit.latex) == ("k_y", "k_y", f"\\text{{{angle}}}/d_\\text{{e}}")


def test_to_fourier_of_inverse_unit_multiplies_by_angle():
    assert T.to_fourier("rad").unit.latex == "\\text{rad}\\,\\omega_\\text{pe}"


def test_to_fourier_records_angle():
    assert Y.to_fourier("rev").fourier_angle == "rev"


def test_from_fourier_restores_original_exactly():
    y = VarInfo(Latex("y"), Latex("d_\\text{e}"), "linear", scale=LogScale())
    assert y.to_fourier("rad").from_fourier() == y


def test_is_fourier():
    assert Y.to_fourier("rad").is_fourier() and not Y.is_fourier()


def test_from_fourier_of_non_fourier_dim_fails():
    with pytest.raises(ValueError, match="not a Fourier"):
        Y.from_fourier()


def test_assign_keeps_fourier_origin():
    k_y = Y.to_fourier("rad").assign(display="q")
    assert k_y.from_fourier() == Y


def test_to_fourier_of_unitless_dim_is_just_the_angle():
    assert VarInfo(Latex("i"), Latex("")).to_fourier("rev").unit.latex == "\\text{rev}"
