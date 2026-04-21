from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import DataWithAttrs, List
from lib.dimension import VarInfo
from lib.latex import Latex
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.particle_util import SPECIES, Species

_SPECIES_VAR_KEY = "__species__"


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
        if data.metadata.active_key is None:
            data = super().apply(data)
            species_dim = VarInfo(Latex(f"\\text{{{self.species}s}}"), Latex(""), "linear", key=_SPECIES_VAR_KEY)
            new_var_info = {**data.metadata.var_info, _SPECIES_VAR_KEY: species_dim}
            return data.assign_metadata(active_key=_SPECIES_VAR_KEY, var_info=new_var_info)
        return super().apply(data)

    def get_modified_display_latex(self, metadata) -> str:
        subscript = self.species[0]
        return f"{{{metadata.active_var_info.display}}}_{subscript}"

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
