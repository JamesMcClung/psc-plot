from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import List
from lib.parsing.args_registry import arg_parser


class SpeciesFilter(MetadataAdaptor):
    def __init__(self, species_key: str):
        self.species_key = species_key

    def apply_list(self, data: List) -> List:
        info = data.metadata.species.get(self.species_key)
        if info is None:
            available = sorted(data.metadata.species.keys())
            raise ValueError(f"unknown species {self.species_key!r}; available: {available}")
        df = data.data
        df = df[(df["q"] == info.q) & (df["m"] == info.m)]
        return data.assign_data(df).assign_metadata(subject=info.display)

    def get_name_fragments(self) -> list[str]:
        return [self.species_key]


@arg_parser(
    dest="adaptors",
    flags="--species",
    metavar="species_key",
    help="include only particles of this species (species_key, e.g. 'e', 'i', 'i25')",
)
def parse_species(arg: str) -> SpeciesFilter:
    return SpeciesFilter(arg)
