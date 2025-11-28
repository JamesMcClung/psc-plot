import numpy as np
import pandas as pd
import xarray as xr

from lib.data.adaptor import AtomicAdaptor
from lib.data.adaptors.registry import register_const_adaptor
from lib.data.keys import DEPENDENT_VAR_KEY


class Scatter(AtomicAdaptor):
    def apply_atomic(self, da: xr.DataArray) -> pd.DataFrame:
        coord_grids = np.meshgrid(*da.coords.values())

        df = pd.DataFrame({DEPENDENT_VAR_KEY: np.ravel(da.data)} | dict(zip(da.coords.keys(), (np.ravel(coord_grid) for coord_grid in coord_grids))))
        return df


register_const_adaptor(
    "--scatter",
    help="convert to list of values and coordinates",
    const=Scatter(),
)
