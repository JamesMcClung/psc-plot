import argparse

import numpy as np
import xarray as xr

from ...dimension import DIMENSIONS, CartesianToPolar
from .. import parse_util
from ..adaptor_base import Adaptor
from ..registry import adaptor_parser


class TransformPolar(Adaptor[xr.DataArray]):
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

        xgrid, ygrid = self.transform.inverse(*np.meshgrid(rs, thetas, indexing="ij"))
        xgrid = xr.Variable([name_r, name_theta], xgrid)
        ygrid = xr.Variable([name_r, name_theta], ygrid)

        da = da.interp({name_x: xgrid, name_y: ygrid}, assume_sorted=True)
        da = da.drop_vars([name_x, name_y])
        da = da.assign_coords({name_r: rs, name_theta: thetas})

        return da

    def get_name_fragment(self) -> str:
        return f"polar_{self.transform.dim_x.name.plain},{self.transform.dim_y.name.plain}"


_POLAR_FORMAT = ("dim_1", "dim_2")


@adaptor_parser(
    "--transform-polar",
    metavar=_POLAR_FORMAT,
    help="perform a coordinate transform from cartesian (dim_1, dim_2) to polar (r, theta)",
    nargs=2,
)
def parse_transform_polar(args: list[str]) -> TransformPolar:
    # nargs=2 guarantees len(args) == 2 by this point
    parse_util.check_value(args[0], "dim_1", DIMENSIONS)
    parse_util.check_value(args[1], "dim_2", DIMENSIONS)

    dims = [DIMENSIONS[dim_name] for dim_name in args]

    try:
        transform = CartesianToPolar(*dims)
        return TransformPolar(transform)
    except ValueError as e:
        raise argparse.ArgumentError(None, *e.args)
