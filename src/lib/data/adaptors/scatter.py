import dask.array as da
import dask.dataframe as dd
import numpy as np

from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field, LazyList, ListMetadata
from lib.parsing.args_registry import const_arg


@const_arg(
    dest="adaptors",
    flags="--scatter",
    help="convert to list of values and coordinates",
)
class Scatter(MetadataAdaptor):
    def apply_field(self, data: Field) -> LazyList:
        # note:  dims and coords are not necessarily in the same order. Data dimensions follow the order of dims.
        coordss = data.coordss
        ordered_coordss = [coordss[dim] for dim in data.dims]
        coord_grids = np.meshgrid(*ordered_coordss, indexing="ij")

        vars = {data.metadata.var_name: da.ravel(data.active_data)} | dict(zip(data.dims, (da.ravel(coord_grid) for coord_grid in coord_grids)))

        df = dd.from_dask_array(da.vstack(vars.values()).T, columns=list(vars))

        metadata = ListMetadata.create_from(
            data.metadata,
            coordss=coordss,
            dependent_var=data.metadata.var_name,
            weight_var=data.metadata.var_name,
        )

        return LazyList(df, metadata)
