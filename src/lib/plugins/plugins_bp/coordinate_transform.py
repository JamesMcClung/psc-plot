import argparse

import numpy as np
import xarray as xr

from ...dimension import DIMENSIONS, CartesianToPolar
from .. import parse_util
from ..plugin_base import PluginBp
from ..registry import plugin_parser


class PolarTransform(PluginBp):
    def __init__(self, transform: CartesianToPolar):
        self.transform = transform

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        name_x = self.transform.dim_x.name.plain
        name_y = self.transform.dim_y.name.plain
        name_r = self.transform.dim_r.name.plain
        name_theta = self.transform.dim_theta.name.plain

        coords_x: xr.DataArray = da.coords[name_x]
        coords_y: xr.DataArray = da.coords[name_y]

        max_x = float(abs(coords_x).max())
        max_y = float(abs(coords_y).max())

        nx = len(coords_x)
        ny = len(coords_y)

        dx = coords_x[1] - coords_x[0]
        dy = coords_y[1] - coords_y[0]

        max_r = (max_x**2 + max_y**2) ** 0.5
        dr = min(dx, dy)
        nr = int(max_r / dr)

        max_theta = 2 * np.pi
        ntheta = 2 * (nx - 2) + 2 * (ny - 2) + 4  # perimeter, but don't double-count corners

        rs = np.linspace(0.0, max_r, nr, endpoint=False)
        thetas = np.linspace(0.0, max_theta, ntheta, endpoint=False)

        new_dims = list(da.dims)
        new_dims.remove(name_x)
        new_dims.remove(name_y)
        new_dims = [name_r, name_theta] + new_dims

        new_coords = dict(da.coords)
        del new_coords[name_x]
        del new_coords[name_y]
        new_coords[name_r] = rs
        new_coords[name_theta] = thetas

        shape = [len(new_coords[dim_name]) for dim_name in new_dims]

        transformed = np.ndarray(shape)
        for ir, r in enumerate(rs):
            for itheta, theta in enumerate(thetas):
                x, y = self.transform.inverse(r, theta)
                transformed[ir, itheta, :] = da.interp({name_x: x, name_y: y}, assume_sorted=True)

        transformed_da = xr.DataArray(transformed, new_coords, new_dims, attrs=da.attrs)

        return transformed_da


_POLAR_FORMAT = ("dim_1", "dim_2")


@plugin_parser(
    "--transform-polar",
    metavar=_POLAR_FORMAT,
    help="perform a coordinate transform from cartesian (dim_1, dim_2) to polar (r, theta)",
    nargs=2,
)
def parse_transform(args: list[str]) -> PolarTransform:
    # nargs=2 guarantees len(args) == 2 by this point
    parse_util.check_value(args[0], "dim_1", DIMENSIONS)
    parse_util.check_value(args[1], "dim_2", DIMENSIONS)

    dims = [DIMENSIONS[dim_name] for dim_name in args]

    try:
        transform = CartesianToPolar(*dims)
        return PolarTransform(transform)
    except ValueError as e:
        raise argparse.ArgumentError(None, *e.args)
