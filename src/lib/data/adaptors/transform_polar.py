import argparse

import numpy as np
import xarray as xr

from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field, List
from lib.dimension import RADIAN, Dimension, check_unit_compatability
from lib.latex import Latex
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


def _build_polar_dims(dim_x: Dimension, dim_y: Dimension) -> tuple[Dimension, Dimension]:
    check_unit_compatability(dim_x, dim_y, "polar")
    r_symbol = "k" if dim_x.is_fourier() else "r"
    dim_r = Dimension(Latex(f"{r_symbol}_\\text{{polar}}"), dim_x.unit, "polar:r", key=f"{r_symbol}_p")
    dim_theta = Dimension(Latex("\\theta"), RADIAN, "polar:theta")
    return dim_r, dim_theta


def _cartesian_to_polar(x, y):
    r = (x**2 + y**2) ** 0.5
    theta = np.arctan2(y, x)
    return r, theta


def _polar_to_cartesian(r, theta):
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return x, y


class TransformPolar(MetadataAdaptor):
    def __init__(self, dim1_key: str, dim2_key: str):
        self.dim1_key = dim1_key
        self.dim2_key = dim2_key

    def apply_field(self, data: Field) -> Field:
        dim_x = data.metadata.get_var_info(self.dim1_key)
        dim_y = data.metadata.get_var_info(self.dim2_key)
        dim_r, dim_theta = _build_polar_dims(dim_x, dim_y)

        key_x, key_y = dim_x.key, dim_y.key
        key_r, key_theta = dim_r.key, dim_theta.key

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
        ntheta = 2 * (nx - 2) + 2 * (ny - 2) + 4

        rs = np.linspace(0.0, max_r, nr, endpoint=False)
        thetas = np.linspace(0.0, max_theta, ntheta, endpoint=False)

        xgrid, ygrid = _polar_to_cartesian(*np.meshgrid(rs, thetas, indexing="ij"))
        xgrid = xr.Variable([key_r, key_theta], xgrid)
        ygrid = xr.Variable([key_r, key_theta], ygrid)

        da = data.active_data
        da = da.interp({key_x: xgrid, key_y: ygrid}, assume_sorted=True)
        da = da.drop_vars([key_x, key_y])
        da = da.assign_coords({key_r: rs, key_theta: thetas})

        new_dims = {k: v for k, v in data.metadata.dims.items() if k not in {key_x, key_y}}
        new_dims[key_r] = dim_r
        new_dims[key_theta] = dim_theta
        new_var_info = {k: v for k, v in data.metadata.var_info.items() if k not in {key_x, key_y}}
        new_var_info[key_r] = dim_r
        new_var_info[key_theta] = dim_theta
        return data.with_active_data(da).assign_metadata(dims=new_dims, var_info=new_var_info)

    def apply_list(self, data: List) -> List:
        dim_x = data.metadata.get_var_info(self.dim1_key)
        dim_y = data.metadata.get_var_info(self.dim2_key)
        dim_r, dim_theta = _build_polar_dims(dim_x, dim_y)

        key_x, key_y = dim_x.key, dim_y.key
        key_r, key_theta = dim_r.key, dim_theta.key

        df = data.data
        rs, thetas = _cartesian_to_polar(df[key_x], df[key_y])
        df = df.assign(**{key_r: rs, key_theta: thetas})

        new_dims = dict(data.metadata.dims)
        new_dims[key_r] = dim_r
        new_dims[key_theta] = dim_theta
        new_var_info = dict(data.metadata.var_info)
        new_var_info[key_r] = dim_r
        new_var_info[key_theta] = dim_theta
        return data.assign_data(df).assign_metadata(dims=new_dims, var_info=new_var_info)

    def get_name_fragments(self) -> list[str]:
        return [f"polar_{self.dim1_key},{self.dim2_key}"]


_POLAR_FORMAT = ("dim_1", "dim_2")


@arg_parser(
    dest="adaptors",
    flags="--transform-polar",
    metavar=_POLAR_FORMAT,
    help="perform a coordinate transform from cartesian (dim_1, dim_2) to polar (r, theta)",
    nargs=2,
)
def parse_transform_polar(args: list[str]) -> TransformPolar:
    for i, arg in enumerate(args, start=1):
        parse_util.check_identifier(arg, f"dim_{i}")
    try:
        return TransformPolar(args[0], args[1])
    except ValueError as e:
        raise argparse.ArgumentError(None, *e.args)
