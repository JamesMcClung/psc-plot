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


from lib.data.data_with_attrs import Metadata, FieldMetadata, ListMetadata


def test_metadata_has_empty_species_by_default():
    for cls in (Metadata, FieldMetadata, ListMetadata):
        md = cls()
        assert md.species == {}, f"{cls.__name__}.species default should be empty dict"


def test_metadata_roundtrips_species_via_create_from():
    src = ListMetadata(species={"e": SpeciesInfo(species_key="e", display=Latex(r"\text{Electrons}"), q=-1.0, m=1.0)})
    dst = FieldMetadata.create_from(src)
    assert "e" in dst.species
    assert dst.species["e"].q == -1.0
