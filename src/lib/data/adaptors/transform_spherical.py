import argparse

import numpy as np
import xarray as xr

from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field, List
from lib.dimension import RADIAN, Dimension, check_unit_compatability
from lib.latex import Latex
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


def _build_spherical_dims(dim_x: Dimension, dim_y: Dimension, dim_z: Dimension) -> tuple[Dimension, Dimension, Dimension]:
    check_unit_compatability(dim_x, dim_y, "spherical")
    check_unit_compatability(dim_x, dim_z, "spherical")
    r_symbol = "k" if dim_x.is_fourier() else "r"
    dim_r = Dimension(Latex(f"{r_symbol}_\\text{{spherical}}"), dim_x.unit, "spherical:r", key=f"{r_symbol}_s")
    dim_theta = Dimension(Latex("\\theta"), RADIAN, "spherical:theta")
    dim_phi = Dimension(Latex("\\phi"), RADIAN, "spherical:phi")
    return dim_r, dim_theta, dim_phi


def _cartesian_to_spherical(x, y, z):
    rho2 = x**2 + y**2
    r = (rho2 + z**2) ** 0.5
    theta = np.arctan2(rho2**0.5, z)
    phi = np.arctan2(y, x)
    return r, theta, phi


def _spherical_to_cartesian(r, theta, phi):
    x = r * np.sin(theta) * np.cos(phi)
    y = r * np.sin(theta) * np.sin(phi)
    z = r * np.cos(theta)
    return x, y, z


class TransformSpherical(MetadataAdaptor):
    def __init__(self, dim1_key: str, dim2_key: str, dim3_key: str):
        self.dim1_key = dim1_key
        self.dim2_key = dim2_key
        self.dim3_key = dim3_key

    def apply_field(self, data: Field) -> Field:
        dim_x = data.metadata.get_var_info(self.dim1_key)
        dim_y = data.metadata.get_var_info(self.dim2_key)
        dim_z = data.metadata.get_var_info(self.dim3_key)
        dim_r, dim_theta, dim_phi = _build_spherical_dims(dim_x, dim_y, dim_z)

        key_x, key_y, key_z = dim_x.key, dim_y.key, dim_z.key
        key_r, key_theta, key_phi = dim_r.key, dim_theta.key, dim_phi.key

        coords_x = data.coordss[key_x]
        coords_y = data.coordss[key_y]
        coords_z = data.coordss[key_z]

        max_x = float(abs(coords_x).max())
        max_y = float(abs(coords_y).max())
        max_z = float(abs(coords_z).max())

        nx = len(coords_x)
        ny = len(coords_y)
        nz = len(coords_z)

        dx = coords_x[1] - coords_x[0]
        dy = coords_y[1] - coords_y[0]
        dz = coords_z[1] - coords_z[0]

        max_r = (max_x**2 + max_y**2 + max_z**2) ** 0.5
        dr = min(dx, dy, dz)
        nr = int(max_r / dr)

        max_theta = np.pi
        ntheta = nz

        max_phi = 2 * np.pi
        nphi = 2 * (nx - 2) + 2 * (ny - 2) + 4

        rs = np.linspace(0.0, max_r, nr, endpoint=False)
        thetas = np.linspace(0.0, max_theta, ntheta, endpoint=False)
        phis = np.linspace(0.0, max_phi, nphi, endpoint=False)

        xgrid, ygrid, zgrid = _spherical_to_cartesian(*np.meshgrid(rs, thetas, phis, indexing="ij"))
        xgrid = xr.Variable([key_r, key_theta, key_phi], xgrid)
        ygrid = xr.Variable([key_r, key_theta, key_phi], ygrid)
        zgrid = xr.Variable([key_r, key_theta, key_phi], zgrid)

        da = data.active_data
        da = da.interp({key_x: xgrid, key_y: ygrid, key_z: zgrid}, assume_sorted=True)
        da = da.drop_vars([key_x, key_y, key_z])
        da = da.assign_coords({key_r: rs, key_theta: thetas, key_phi: phis})

        new_dims = {k: v for k, v in data.metadata.dims.items() if k not in {key_x, key_y, key_z}}
        new_dims[key_r] = dim_r
        new_dims[key_theta] = dim_theta
        new_dims[key_phi] = dim_phi
        new_var_info = {k: v for k, v in data.metadata.var_info.items() if k not in {key_x, key_y, key_z}}
        new_var_info[key_r] = dim_r
        new_var_info[key_theta] = dim_theta
        new_var_info[key_phi] = dim_phi
        return data.with_active_data(da).assign_metadata(dims=new_dims, var_info=new_var_info)

    def apply_list(self, data: List) -> List:
        dim_x = data.metadata.get_var_info(self.dim1_key)
        dim_y = data.metadata.get_var_info(self.dim2_key)
        dim_z = data.metadata.get_var_info(self.dim3_key)
        dim_r, dim_theta, dim_phi = _build_spherical_dims(dim_x, dim_y, dim_z)

        key_x, key_y, key_z = dim_x.key, dim_y.key, dim_z.key
        key_r, key_theta, key_phi = dim_r.key, dim_theta.key, dim_phi.key

        df = data.data
        rs, thetas, phis = _cartesian_to_spherical(df[key_x], df[key_y], df[key_z])
        df = df.assign(**{key_r: rs, key_theta: thetas, key_phi: phis})

        new_dims = dict(data.metadata.dims)
        new_dims[key_r] = dim_r
        new_dims[key_theta] = dim_theta
        new_dims[key_phi] = dim_phi
        new_var_info = dict(data.metadata.var_info)
        new_var_info[key_r] = dim_r
        new_var_info[key_theta] = dim_theta
        new_var_info[key_phi] = dim_phi
        return data.assign_data(df).assign_metadata(dims=new_dims, var_info=new_var_info)

    def get_name_fragments(self) -> list[str]:
        return [f"spherical_{self.dim1_key},{self.dim2_key},{self.dim3_key}"]


_SPHERICAL_FORMAT = ("dim_1", "dim_2", "dim_3")


@arg_parser(
    dest="adaptors",
    flags="--transform-spherical",
    metavar=_SPHERICAL_FORMAT,
    help="perform a coordinate transform from cartesian (dim_1, dim_2, dim_3) to spherical (r, theta, phi)",
    nargs=3,
)
def parse_transform_spherical(args: list[str]) -> TransformSpherical:
    for i, arg in enumerate(args, start=1):
        parse_util.check_identifier(arg, f"dim_{i}")
    try:
        return TransformSpherical(args[0], args[1], args[2])
    except ValueError as e:
        raise argparse.ArgumentError(None, *e.args)
