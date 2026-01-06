import numpy as np
import pandas as pd

from lib.data.adaptor import CheckedAdaptor
from lib.data.adaptors.registry import register_const_adaptor
from lib.data.data_with_attrs import Field, FullList, ListMetadata


class Scatter(CheckedAdaptor):
    def apply_checked(self, data: Field) -> FullList:
        # note:  dims and coords are not necessarily in the same order. Data dimensions follow the order of dims.
        coordss = data.coordss
        ordered_coordss = [coordss[dim] for dim in data.dims]
        coord_grids = np.meshgrid(*ordered_coordss, indexing="ij")

        df = pd.DataFrame({data.metadata.var_name: np.ravel(data.data)} | dict(zip(data.dims, (np.ravel(coord_grid) for coord_grid in coord_grids))))

        metadata = ListMetadata.create_from(
            data.metadata,
            coordss=coordss,
            dependent_var=data.metadata.var_name,
            weight_var=data.metadata.var_name,
        )

        return FullList(df, metadata)


register_const_adaptor(
    "--scatter",
    help="convert to list of values and coordinates",
    const=Scatter(),
)
