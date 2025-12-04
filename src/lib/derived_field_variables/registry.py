import numpy as np
import pscpy
from xarray import DataArray, Dataset

from ..data.adaptors.field_adaptors.fourier import Fourier
from ..data.adaptors.field_adaptors.mag import Magnitude
from ..data.pipeline import Pipeline
from ..dimension import DIMENSIONS
from .derived_field_variable import derived_field_variable

__all__ = []


@derived_field_variable("pfd_moments")
def rho(rho_i: DataArray, rho_e: DataArray) -> DataArray:
    return rho_i + rho_e


@derived_field_variable("gauss")
def error(rho: DataArray, dive: DataArray) -> DataArray:
    return rho - dive


@derived_field_variable("continuity")
def error(d_rho: DataArray, dt_divj: DataArray) -> DataArray:
    return d_rho + dt_divj


@derived_field_variable("pfd")
def h2_cc(hx_fc: DataArray, hy_fc: DataArray, hz_fc: DataArray) -> DataArray:
    h = Dataset({"h2x_fc": hx_fc**2, "h2y_fc": hy_fc**2, "h2z_fc": hz_fc**2})
    pscpy.auto_recenter(h, "cc", x="periodic", y="periodic", z="periodic")
    return h["h2x_cc"] + h["h2y_cc"] + h["h2z_cc"]


@derived_field_variable("pfd")
def hxz2_cc(hx_fc: DataArray, hz_fc: DataArray) -> DataArray:
    h = Dataset({"h2x_fc": hx_fc**2, "h2z_fc": hz_fc**2})
    pscpy.auto_recenter(h, "cc", x="periodic", y="periodic", z="periodic")
    return h["h2x_cc"] + h["h2z_cc"]


@derived_field_variable("pfd")
def hxzhat2(hx_fc: DataArray, hz_fc: DataArray) -> DataArray:
    pipeline = Pipeline(Fourier([DIMENSIONS["x"], DIMENSIONS["y"], DIMENSIONS["z"]]), Magnitude())

    hx_hat = pipeline.apply(hx_fc)
    hz_hat = pipeline.apply(hz_fc)

    return hx_hat**2 + hz_hat**2


@derived_field_variable("pfd")
def hhat2(hx_fc: DataArray, hy_fc: DataArray, hz_fc: DataArray) -> DataArray:
    pipeline = Pipeline(Fourier([DIMENSIONS["x"], DIMENSIONS["y"], DIMENSIONS["z"]]), Magnitude())

    hx_hat = pipeline.apply(hx_fc)
    hy_hat = pipeline.apply(hy_fc)
    hz_hat = pipeline.apply(hz_fc)

    return hx_hat**2 + hy_hat**2 + hz_hat**2


@derived_field_variable("pfd")
def h_cc(h2_cc: DataArray) -> DataArray:
    return np.sqrt(h2_cc)


@derived_field_variable("pfd")
def div_h_cc(hx_fc: DataArray, hy_fc: DataArray, hz_fc: DataArray) -> DataArray:
    coords = hx_fc.coords  # they should all have the same coords
    dims = {"x", "y", "z"}
    noninvariant_dims = {dim for dim in dims if len(coords[dim]) > 1}
    h_comps = {"x": hx_fc, "y": hy_fc, "z": hz_fc}

    div_h_cc = None
    for d in noninvariant_dims:
        other_dims = noninvariant_dims - {d}
        # ideally, we'd have an extra index in the dth dimension of the dth component of h, but PSC doesn't write that
        # so instead, cut off 1 index from the non-dth dimension of the dth component of h
        hd_sliced = h_comps[d].isel({other_dim: slice(0, -1) for other_dim in other_dims})

        # doing this diff then reduces the dth dimension by 1 index, so all deltas have the same dimension
        delta_hd = hd_sliced.isel({d: slice(1, None)}).data - hd_sliced.isel({d: slice(0, -1)}).data
        delta_d = float(coords[d][1] - coords[d][0])
        diff_hd = delta_hd / delta_d

        div_h_cc = diff_hd if div_h_cc is None else div_h_cc + diff_hd

    new_coords = {d: (coord[:-1] if d in noninvariant_dims else coord) for d, coord in coords.items()}

    return DataArray(div_h_cc, new_coords, dims=hx_fc.dims)
