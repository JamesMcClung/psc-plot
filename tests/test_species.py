from lib.latex import Latex
from lib.species import SpeciesInfo


def test_species_info_holds_fields():
    info = SpeciesInfo(species_key="e", display=Latex(r"\text{Electrons}"), q=-1.0, m=1.0)
    assert info.species_key == "e"
    assert info.display.latex == r"\text{Electrons}"
    assert info.q == -1.0
    assert info.m == 1.0


def test_species_info_is_frozen():
    import dataclasses
    info = SpeciesInfo(species_key="i", display=Latex(r"\text{Ions}"), q=1.0, m=1.0)
    try:
        info.q = 2.0
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("SpeciesInfo should be frozen")
