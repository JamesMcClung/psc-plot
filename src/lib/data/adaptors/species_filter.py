import dask.dataframe as dd
import pandas as pd

from lib.data.adaptor import BareAdaptor
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.particle_util import SPECIES, Species


class SpeciesFilter(BareAdaptor):
    def __init__(self, species: Species):
        self.species = species

    def apply_list_bare(self, df: dd.DataFrame | pd.DataFrame) -> dd.DataFrame | pd.DataFrame:
        if self.species == "electron":
            df = df[df["q"] < 0]
        elif self.species == "ion":
            df = df[df["q"] > 0]
        return df

    def get_modified_display_latex(self, display_latex: str, metadata) -> str:
        subscript = self.species[0]
        return f"{{{display_latex}}}_{subscript}"

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
