from lib.data import data_util
from lib.data.adaptor import CheckedAdaptor
from lib.data.adaptors import parse_util
from lib.data.adaptors.registry import adaptor_parser
from lib.data.data_with_attrs import Field, FullList


class Idx(CheckedAdaptor):
    def __init__(self, dim_names_to_isel: dict[str, int | slice]):
        self.dim_names_to_isel = dim_names_to_isel

    def apply_checked[D: Field | FullList](self, data: D) -> D:
        if isinstance(data, Field):
            return data.assign_data(data.data.isel(self.dim_names_to_isel))

        elif isinstance(data, FullList):
            coordss = data.coordss.copy()
            df = data.data
            for dim, isel in self.dim_names_to_isel.items():
                if dim not in coordss:
                    raise ValueError(f"Data has no coordinate information for dimension {dim}")

                if isinstance(isel, int):
                    pos = float(coordss[dim][isel])
                    df = df[df[dim] == pos]
                    coordss[dim] = pos
                else:
                    if isel.start not in [None, 0]:
                        pos_lower = float(coordss[dim][isel.start])
                        df = df[df[dim] >= pos_lower]

                    if isel.stop is not None:
                        pos_upper = float(coordss[dim][isel.stop])
                        df = df[df[dim] < pos_upper]

                    coordss[dim] = coordss[dim][isel]

            return data.assign(df, coordss=coordss)

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{dim_name}={data_util.sel_to_frag(isel)}" for dim_name, isel in self.dim_names_to_isel.items())
        return [f"idx_{subfrags}"]


IDX_FORMAT = "dim_name=[idx | lower?:upper?]"


@adaptor_parser(
    "--idx",
    "-i",
    metavar=IDX_FORMAT,
    help="select data at the given index, or between the lower index (inclusive) and upper index (exclusive)",
    nargs="+",
)
def parse_idx(args: list[str]) -> Idx:
    dim_names_to_isel = {}
    for arg in args:
        [dim_name, isel_arg] = parse_util.parse_assignment(arg, IDX_FORMAT)

        parse_util.check_identifier(dim_name, "dim_name")
        if ":" in isel_arg:
            dim_names_to_isel[dim_name] = parse_util.parse_slice(isel_arg, int)
        else:
            dim_names_to_isel[dim_name] = parse_util.parse_number(isel_arg, "idx", int)

    return Idx(dim_names_to_isel)
