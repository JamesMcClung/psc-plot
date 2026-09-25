from lib.data import data_util
from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field, List
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class Idx(MetadataAdaptor):
    def __init__(self, dim_names_to_isel: dict[str, int | slice]):
        self.dim_names_to_isel = dim_names_to_isel

    def apply_field(self, data: Field) -> Field:
        return data.with_active(data=data.require_active_subdata().isel(self.dim_names_to_isel))

    def apply_list(self, data: List) -> List:
        coordss = data.coordss().copy()
        df = data.data
        partition_dim = data.metadata.partition_dim
        partition_ranges = data.metadata.partition_ranges

        for dim, isel in self.dim_names_to_isel.items():
            if dim not in coordss:
                raise ValueError(f"Data has no coordinate information for dimension {dim}")

            if dim == partition_dim and partition_ranges is not None:
                # Dask-native partition pruning along the partition dim.
                all_steps = list(range(len(partition_ranges)))
                selected_steps = all_steps[isel]
                if isinstance(selected_steps, int):
                    selected_steps = [selected_steps]
                partition_indices = [p for step in selected_steps for p in range(*partition_ranges[step])]
                df = df.partitions[partition_indices]
                coordss[dim] = coordss[dim][isel]

                if isinstance(isel, int):
                    # The dim now holds a single value, so partitions are no longer laid out along it.
                    partition_dim = None
                    partition_ranges = None
                else:
                    # Rebase the surviving ranges onto the pruned frame's partition numbering.
                    rebased = []
                    offset = 0
                    for step in selected_steps:
                        start, end = partition_ranges[step]
                        rebased.append((offset, offset + end - start))
                        offset += end - start
                    partition_ranges = rebased
                continue

            if isinstance(isel, int):
                pos = coordss[dim][isel]
                df = df[df[dim] == pos]
                if len(df) == 0:
                    import warnings

                    message = f"--idx {dim}={isel} on list data requires exact coordinate match, and returned an empty list. Try --idx {dim}={isel}:{isel + 1} instead."
                    warnings.warn(message)
                coordss[dim] = pos
            else:
                if isel.start not in [None, 0]:
                    pos_lower = coordss[dim][isel.start]
                    df = df[df[dim] >= pos_lower]

                if isel.stop is not None:
                    pos_upper = coordss[dim][isel.stop]
                    df = df[df[dim] < pos_upper]

                coordss[dim] = coordss[dim][isel]

        return data.assign(df, coordss=coordss, partition_dim=partition_dim, partition_ranges=partition_ranges)

    def get_name_fragments(self) -> list[str]:
        subfrags = "_".join(f"{dim_name}={data_util.sel_to_frag(isel)}" for dim_name, isel in self.dim_names_to_isel.items())
        return [f"idx_{subfrags}"]


IDX_FORMAT = "dim_name=[idx | lower?:upper?]"


@arg_parser(
    dest="adaptors",
    flags=["--idx", "-i"],
    metavar=IDX_FORMAT,
    help="select data at the given index, or between the lower index (inclusive) and upper index (exclusive)",
    nargs="+",
)
def parse_idx(args: list[str]) -> Idx:
    dim_names_to_isel = {}
    for arg in args:
        [dim_name, isel_arg] = parse_util.parse_assignment(arg, IDX_FORMAT)

        parse_util.parse_identifier(dim_name, "dim_name")
        if ":" in isel_arg:
            dim_names_to_isel[dim_name] = parse_util.parse_slice(isel_arg, int)
        else:
            dim_names_to_isel[dim_name] = parse_util.parse_number(isel_arg, "idx", int)

    return Idx(dim_names_to_isel)
