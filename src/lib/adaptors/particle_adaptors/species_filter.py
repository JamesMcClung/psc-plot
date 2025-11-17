import pandas as pd

from ...particle_util import SPECIES, Species
from .. import parse_util
from ..adaptor import Adaptor
from ..registry import adaptor_parser


class SpeciesFilter(Adaptor[pd.DataFrame]):
    def __init__(self, species: Species):
        self.species = species

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.species == "electron":
            df = df[df["q"] < 0]
        elif self.species == "ion":
            df = df[df["q"] > 0]
        return df

    def get_name_fragment(self) -> str:
        return self.species


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
