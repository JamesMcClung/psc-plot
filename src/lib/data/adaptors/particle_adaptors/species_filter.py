import dask.dataframe as dd

from lib.data.adaptor import BareAdaptor

from ....particle_util import SPECIES, Species
from .. import parse_util
from ..registry import adaptor_parser


class SpeciesFilter(BareAdaptor):
    def __init__(self, species: Species):
        self.species = species

    def apply_bare(self, df: dd.DataFrame) -> dd.DataFrame:
        if self.species == "electron":
            df = df[df["q"] < 0]
        elif self.species == "ion":
            df = df[df["q"] > 0]
        return df

    def get_modified_var_latex(self, var_latex: str) -> str:
        subscript = self.species[0]
        return f"{{{var_latex}}}_{subscript}"

    def get_name_fragments(self) -> list[str]:
        return [self.species]


_SPECIES_FILTER_FORMAT = "species"


@adaptor_parser(
    "--species",
    metavar=_SPECIES_FILTER_FORMAT,
    help="include only particles of this species",
)
def parse_slice(arg: str) -> SpeciesFilter:
    species = arg
    parse_util.check_value(species, "species", SPECIES)
    return SpeciesFilter(species)
