from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import DataWithAttrs, List
from lib.latex import Latex
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.particle_util import SPECIES, Species


_SUBJECT: dict[Species, Latex] = {
    "ion": Latex(r"\text{Ions}"),
    "electron": Latex(r"\text{Electrons}"),
}


class SpeciesFilter(MetadataAdaptor):
    def __init__(self, species: Species):
        self.species = species

    def apply_list(self, data: List) -> List:
        df = data.data
        if self.species == "electron":
            df = df[df["q"] < 0]
        elif self.species == "ion":
            df = df[df["q"] > 0]
        return data.assign_data(df)

    def apply(self, data: DataWithAttrs) -> DataWithAttrs:
        data = data.assign_metadata(subject=_SUBJECT[self.species])
        return super().apply(data)

    def get_name_fragments(self) -> list[str]:
        return [self.species]


_SPECIES_FILTER_FORMAT = "species"


@arg_parser(
    dest="adaptors",
    flags="--species",
    metavar=_SPECIES_FILTER_FORMAT,
    help="include only particles of this species",
)
def parse_slice(arg: str) -> SpeciesFilter:
    species = arg
    parse_util.check_value(species, "species", SPECIES)
    return SpeciesFilter(species)
