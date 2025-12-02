import numpy as np
import pandas as pd
import xarray as xr

from lib.data.adaptor import AtomicAdaptor
from lib.data.adaptors.registry import register_const_adaptor
from lib.data.keys import DEPENDENT_VAR_KEY


class Scatter(AtomicAdaptor):
    def apply_atomic(self, da: xr.DataArray) -> pd.DataFrame:
        # note: dims and coords are not necessarily in the same order. Data dimensions follow the order of dims.
        ordered_coords = [da.coords[dim] for dim in da.dims]
        coord_grids = np.meshgrid(*ordered_coords, indexing="ij")

        df = pd.DataFrame({DEPENDENT_VAR_KEY: np.ravel(da)} | dict(zip(da.dims, (np.ravel(coord_grid) for coord_grid in coord_grids))))
        return df


register_const_adaptor(
    "--scatter",
    help="convert to list of values and coordinates",
    const=Scatter(),
)
