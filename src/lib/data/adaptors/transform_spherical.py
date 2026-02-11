import argparse

import numpy as np
import xarray as xr

from lib.data.adaptor import CheckedAdaptor
from lib.data.data_with_attrs import Field, FullList
from lib.dimension import DIMENSIONS, CartesianToSpherical
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class TransformSpherical(CheckedAdaptor):
    def __init__(self, transform: CartesianToSpherical):
        self.transform = transform

    def apply_checked[D: Field | FullList](self, data: D) -> D:
        key_x = self.transform.dim_x.key
        key_y = self.transform.dim_y.key
        key_z = self.transform.dim_z.key
        key_r = self.transform.dim_r.key
        key_theta = self.transform.dim_theta.key
        key_phi = self.transform.dim_phi.key

        if isinstance(data, Field):
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
            nphi = 2 * (nx - 2) + 2 * (ny - 2) + 4  # perimeter, but don't double-count corners

            rs = np.linspace(0.0, max_r, nr, endpoint=False)
            thetas = np.linspace(0.0, max_theta, ntheta, endpoint=False)
            phis = np.linspace(0.0, max_phi, nphi, endpoint=False)

            xgrid, ygrid, zgrid = self.transform.inverse(*np.meshgrid(rs, thetas, phis, indexing="ij"))
            xgrid = xr.Variable([key_r, key_theta, key_phi], xgrid)
            ygrid = xr.Variable([key_r, key_theta, key_phi], ygrid)
            zgrid = xr.Variable([key_r, key_theta, key_phi], zgrid)

            da = data.data
            da = da.interp({key_x: xgrid, key_y: ygrid, key_z: zgrid}, assume_sorted=True)
            da = da.drop_vars([key_x, key_y, key_z])
            da = da.assign_coords({key_r: rs, key_theta: thetas, key_phi: phis})
            return data.assign_data(da)

        else:
            df = data.data
            rs, thetas, phis = self.transform.apply(df[key_x], df[key_y], df[key_z])
            df = df.assign(**{key_r: rs, key_theta: thetas, key_phi: phis})
            return data.assign_data(df)

    def get_key_fragments(self) -> list[str]:
        return [f"spherical_{self.transform.dim_x.key},{self.transform.dim_y.key},{self.transform.dim_z.key}"]


_SPHERICAL_FORMAT = ("dim_1", "dim_2", "dim_3")


@arg_parser(
    dest="adaptors",
    flags="--transform-spherical",
    metavar=_SPHERICAL_FORMAT,
    help="perform a coordinate transform from cartesian (dim_1, dim_2) to polar (r, theta)",
    nargs=3,
)
def parse_transform_spherical(args: list[str]) -> TransformSpherical:
    # nargs=3 guarantees len(args) == 3 by this point
    parse_util.check_value(args[0], "dim_1", DIMENSIONS)
    parse_util.check_value(args[1], "dim_2", DIMENSIONS)
    parse_util.check_value(args[2], "dim_3", DIMENSIONS)

    dims = [DIMENSIONS[dim_name] for dim_name in args]

    try:
        transform = CartesianToSpherical(*dims)
        return TransformSpherical(transform)
    except ValueError as e:
        raise argparse.ArgumentError(None, *e.args)
