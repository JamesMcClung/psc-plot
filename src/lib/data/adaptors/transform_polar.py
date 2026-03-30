import argparse

import numpy as np
import xarray as xr

from lib.data.adaptor import CheckedAdaptor
from lib.data.data_with_attrs import Field, List
from lib.dimension import DIMENSIONS, CartesianToPolar
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


class TransformPolar(CheckedAdaptor):
    def __init__(self, transform: CartesianToPolar):
        self.transform = transform

    def apply_field(self, data: Field) -> Field:
        key_x = self.transform.dim_x.key
        key_y = self.transform.dim_y.key
        key_r = self.transform.dim_r.key
        key_theta = self.transform.dim_theta.key

        coords_x = data.coordss[key_x]
        coords_y = data.coordss[key_y]

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
        xgrid = xr.Variable([key_r, key_theta], xgrid)
        ygrid = xr.Variable([key_r, key_theta], ygrid)

        da = data.data
        da = da.interp({key_x: xgrid, key_y: ygrid}, assume_sorted=True)
        da = da.drop_vars([key_x, key_y])
        da = da.assign_coords({key_r: rs, key_theta: thetas})
        return data.assign_data(da)

    def apply_list(self, data: List) -> List:
        key_x = self.transform.dim_x.key
        key_y = self.transform.dim_y.key
        key_r = self.transform.dim_r.key
        key_theta = self.transform.dim_theta.key

        df = data.data
        rs, thetas = self.transform.apply(df[key_x], df[key_y])
        df = df.assign(**{key_r: rs, key_theta: thetas})
        return data.assign_data(df)

    def get_key_fragments(self) -> list[str]:
        return [f"polar_{self.transform.dim_x.key},{self.transform.dim_y.key}"]


_POLAR_FORMAT = ("dim_1", "dim_2")


@arg_parser(
    dest="adaptors",
    flags="--transform-polar",
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
