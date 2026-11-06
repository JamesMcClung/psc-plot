import dask.dataframe as dd
import numpy as np
import pandas as pd

from lib.config import PscPlotConfig
from lib.data.adaptor import WorldAdaptor
from lib.data.data_with_attrs import FullList, LazyList, List
from lib.data.ensure_derived import ensure_derived
from lib.data.loader import load
from lib.file_util import Prepath
from lib.latex import Latex
from lib.parsing.args_registry import arg_parser


def _concat_subjects(first: Latex | None, second: Latex | None) -> Latex | None:
    if first == second or second is None:
        return first
    if first is None:
        return second
    return Latex(rf"{first.latex}\text{{ and }}{second.latex}")


def _check_same_coordss(first: List, second: List):
    first_coordss, second_coordss = first.coordss(), second.coordss()
    mismatched = sorted(dim for dim in first_coordss.keys() | second_coordss.keys() if dim not in first_coordss or dim not in second_coordss or not np.array_equal(first_coordss[dim], second_coordss[dim]))
    if mismatched:
        message = f"can't concat {second.metadata.prepath} to {first.metadata.prepath}: their coordinates differ along {mismatched}. Note that e.g. --idx changes coordinates, so --concat before it."
        raise ValueError(message)


def _merge_species(first: List, second: List) -> dict:
    species = dict(second.metadata.species)
    for key, info in first.metadata.species.items():
        if key in species and species[key] != info:
            raise ValueError(f"can't concat {second.metadata.prepath} to {first.metadata.prepath}: both define species {key!r}, differently")
        species[key] = info
    return species


def _interleaved_partition_order(first_ranges: list[tuple[int, int]], second_ranges: list[tuple[int, int]], second_offset: int) -> tuple[list[int], list[tuple[int, int]]]:
    """The partition order that puts each step's partitions from both lists next to each other, and the resulting ranges."""
    order = []
    ranges = []
    for (first_start, first_end), (second_start, second_end) in zip(first_ranges, second_ranges, strict=True):
        start = len(order)
        order += range(first_start, first_end)
        order += range(second_offset + second_start, second_offset + second_end)
        ranges.append((start, len(order)))
    return order, ranges


def concat_lists(first: List, second: List, config: PscPlotConfig) -> List:
    """Append `second`'s rows to `first`'s. The result keeps `first`'s columns, prepath and active key."""
    _check_same_coordss(first, second)
    if first.metadata.weight_key != second.metadata.weight_key:
        raise ValueError(f"can't concat {second.metadata.prepath} to {first.metadata.prepath}: their weight keys differ ({first.metadata.weight_key} vs {second.metadata.weight_key})")

    columns = list(first.data.columns)
    for key in columns:
        second = ensure_derived(second, key, config)
    second_df = second.data[columns]

    partition_dim = None
    partition_ranges = None

    if isinstance(first, FullList) and isinstance(second, FullList):
        df = pd.concat([first.data, second_df], ignore_index=True)
        result_type = FullList
    else:
        first_df = first.data if isinstance(first, LazyList) else dd.from_pandas(first.data, npartitions=1)
        second_df = second_df if isinstance(second, LazyList) else dd.from_pandas(second_df, npartitions=1)
        df = dd.concat([first_df, second_df])
        result_type = LazyList

        # Keep the per-step partition layout that --idx and --bin rely on.
        md1, md2 = first.metadata, second.metadata
        if md1.partition_ranges is not None and md2.partition_ranges is not None and md1.partition_dim == md2.partition_dim:
            order, partition_ranges = _interleaved_partition_order(md1.partition_ranges, md2.partition_ranges, first_df.npartitions)
            df = df.partitions[order]
            partition_dim = md1.partition_dim

    metadata = first.metadata.assign(
        var_infos=second.metadata.var_infos | first.metadata.var_infos,
        species=_merge_species(first, second),
        subject=_concat_subjects(first.metadata.subject, second.metadata.subject),
        partition_dim=partition_dim,
        partition_ranges=partition_ranges,
    )
    return result_type(df, metadata)


class Concat(WorldAdaptor):
    def __init__(self, prepath: Prepath):
        self.prepath = prepath

    def apply_world(self, world):
        first = world.require_active_data()
        second = world.datas[self.prepath] if self.prepath in world.datas else load(world.config, self.prepath)
        if not isinstance(first, List) or not isinstance(second, List):
            raise ValueError("--concat only accepts list data (e.g. particles); try --concat before --bin")
        return world.with_active(data=concat_lists(first, second, world.config))

    def get_name_fragments(self) -> list[str]:
        return [f"concat_{self.prepath}"]


@arg_parser(
    dest="adaptors",
    flags="--concat",
    metavar="prepath",
    nargs="just one",
    help="Append the rows of the list (e.g. particles) at `prepath` to the current list, e.g. `prt.beam --concat prt.core`. The coordinates must match, so concat before e.g. --idx.",
)
def parse_concat(arg: str) -> Concat:
    return Concat(arg)
