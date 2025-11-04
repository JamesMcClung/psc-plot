import argparse

import numpy as np
import xarray as xr

from ...dimension import DIMENSIONS, CartesianToSpherical
from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser


class TransformSpherical(PluginBp):
    def __init__(self, transform: CartesianToSpherical):
        self.transform = transform

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        name_x = self.transform.dim_x.name.plain
        name_y = self.transform.dim_y.name.plain
        name_z = self.transform.dim_z.name.plain
        name_r = self.transform.dim_r.name.plain
        name_theta = self.transform.dim_theta.name.plain
        name_phi = self.transform.dim_phi.name.plain

        coords_x: xr.DataArray = da.coords[name_x]
        coords_y: xr.DataArray = da.coords[name_y]
        coords_z: xr.DataArray = da.coords[name_z]

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

        new_dims = list(da.dims)
        new_dims.remove(name_x)
        new_dims.remove(name_y)
        new_dims.remove(name_z)
        new_dims = [name_r, name_theta, name_phi] + new_dims

        new_coords = dict(da.coords)
        del new_coords[name_x]
        del new_coords[name_y]
        del new_coords[name_z]
        new_coords[name_r] = rs
        new_coords[name_theta] = thetas
        new_coords[name_phi] = phis

        shape = [len(new_coords[dim_name]) for dim_name in new_dims]

        transformed = np.ndarray(shape)
        for ir, r in enumerate(rs):
            for itheta, theta in enumerate(thetas):
                for iphi, phi in enumerate(phis):
                    x, y, z = self.transform.inverse(r, theta, phi)
                    indexer = [ir, itheta, iphi]
                    if len(da.shape) > 3:
                        indexer.append(slice(None))
                    transformed[*indexer] = da.interp({name_x: x, name_y: y, name_z: z}, assume_sorted=True)

        transformed_da = xr.DataArray(transformed, new_coords, new_dims, attrs=da.attrs)

        return transformed_da

    def get_name_fragment(self) -> str:
        return f"spherical_{self.transform.dim_x.name.plain},{self.transform.dim_y.name.plain},{self.transform.dim_z.name.plain}"


_SPHERICAL_FORMAT = ("dim_1", "dim_2", "dim_3")


@plugin_parser(
    "--transform-spherical",
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
