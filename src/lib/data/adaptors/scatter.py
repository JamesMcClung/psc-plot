import dask.array as da
import dask.dataframe as dd
import numpy as np

from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field, LazyList, ListMetadata
from lib.latex import Latex
from lib.parsing.args_registry import arg_parser


class Scatter(MetadataAdaptor):
    def __init__(self, subject: Latex | None):
        self.subject = subject

    def apply_field(self, data: Field) -> LazyList:
        coordss = data.coordss
        ordered_coordss = [coordss[dim] for dim in data.dims]
        coord_grids = np.meshgrid(*ordered_coordss, indexing="ij")

        vars = {data.metadata.active_key: da.ravel(data.active_data)} | dict(zip(data.dims, (da.ravel(coord_grid) for coord_grid in coord_grids)))

        df = dd.from_dask_array(da.vstack(vars.values()).T, columns=list(vars))

        metadata = ListMetadata.create_from(
            data.metadata,
            coordss=coordss,
            weight_var=data.metadata.active_key,
            subject=self.subject,
        )

        return LazyList(df, metadata)


@arg_parser(
    dest="adaptors",
    flags="--scatter",
    metavar="name",
    help="convert to list of values and coordinates, optionally naming the result",
    nargs="*",
)
def parse_scatter(args: list[str]) -> Scatter:
    if args:
        return Scatter(Latex(args[0]))
    return Scatter(None)
