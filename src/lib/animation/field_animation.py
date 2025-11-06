from __future__ import annotations

import functools
import typing

import numpy as np
import xarray as xr
from matplotlib.colors import LogNorm, Normalize
from matplotlib.projections.polar import PolarAxes

from .. import field_util, file_util, plt_util
from ..adaptors import FieldPipeline
from ..derived_field_variables import DERIVED_FIELD_VARIABLES
from ..dimension import DIMENSIONS
from .animation_base import Animation

__all__ = ["FieldAnimation"]


def get_extent(da: xr.DataArray, dim: str) -> tuple[float, float]:
    lower = da[dim][0]
    upper = da[dim][-1] + (da[dim][1] - da[dim][0])
    return (float(lower), float(upper))


def derive_variable(ds: xr.Dataset, var_name: str, ds_prefix: file_util.FieldPrefix):
    if var_name in ds.variables:
        return
    elif var_name in DERIVED_FIELD_VARIABLES[ds_prefix]:
        derived_var = DERIVED_FIELD_VARIABLES[ds_prefix][var_name]
        for base_var_name in derived_var.base_var_names:
            derive_variable(ds, base_var_name, ds_prefix)
        derived_var.assign_to(ds)
    else:
        message = f"No variable named '{var_name}'.\nThe following variables are defined: {list(ds.variables)}\n The following variables can be derived: {list(DERIVED_FIELD_VARIABLES[ds_prefix])}"
        raise ValueError(message)


type Scale = typing.Literal["linear", "log"]


class FieldAnimation(Animation):
    def __init__(
        self,
        steps: list[int],
        prefix: file_util.FieldPrefix,
        variable: str,
        pipeline: FieldPipeline,
        *,
        subplot_kw: dict[str, typing.Any] = {},
    ):
        super().__init__(steps, subplot_kw=subplot_kw)

        self.prefix = prefix
        self.variable = variable

        self.pipeline = pipeline

        self.indep_scale: Scale = "linear"
        self.dep_scale: Scale = "linear"

    @functools.cached_property
    def dep_var_name(self) -> str:
        """The latex-formatted name (including applied formulae) of the dependent variable"""
        # This is cached in order to defer its evaluation until after _load_data has been called,
        # and each adaptor has thus seen the data and determined what (if any) internal adaptors it needs
        # (as of the time of this comment, only Versus does this)
        return self.pipeline.get_modified_dep_var_name(f"\\text{{{self.variable}}}")

    def set_scale(self, indep_scale: Scale, dep_scale: Scale):
        self.indep_scale = indep_scale
        self.dep_scale = dep_scale

    def _load_data(self, step: int) -> xr.DataArray:
        ds = field_util.load_ds(self.prefix, step)
        derive_variable(ds, self.variable, self.prefix)
        da = ds[self.variable]

        da = self.pipeline.apply(da)

        da = da.assign_attrs(**ds.attrs)

        # filter out near-zero values
        if self.dep_scale == "log":
            new_data_inner = da.data
            new_data_inner[new_data_inner < 1e-40] = np.nan
            da[:] = new_data_inner

        return da

    def _get_var_bounds(self) -> tuple[float, float]:
        lower = np.inf
        upper = -np.inf
        for step in self.steps:
            data = self._load_data(step)
            lower = min(lower, np.nanmin(data.data))
            upper = max(upper, np.nanmax(data.data))

        return (lower, upper)

    @staticmethod
    def get_animation(
        steps: list[int],
        prefix: file_util.FieldPrefix,
        variable: str,
        pipeline: FieldPipeline,
        dims: list[str],
    ) -> FieldAnimation:
        if len(dims) == 1:
            return FieldAnimation1d(steps, prefix, variable, pipeline, dims[0])
        if len(dims) == 2:
            if DIMENSIONS[dims[0]].geometry == "polar:r" and DIMENSIONS[dims[1]].geometry == "polar:theta":
                return FieldAnimation2dPolar(steps, prefix, variable, pipeline, tuple(dims))
            else:
                return FieldAnimation2d(steps, prefix, variable, pipeline, tuple(dims))
        else:
            raise NotImplementedError("don't have 3D animations yet")

    def _get_default_save_path(self) -> str:
        adaptor_name_fragments = self.pipeline.get_name_fragments()
        return "-".join([self.prefix, self.variable] + adaptor_name_fragments) + ".mp4"


class FieldAnimation2d(FieldAnimation):
    def __init__(
        self,
        steps: list[int],
        prefix: file_util.FieldPrefix,
        variable: str,
        pipeline: FieldPipeline,
        dims: tuple[str, str],
    ):
        super().__init__(steps, prefix, variable, pipeline)

        self.dims = dims

    def _init_fig(self):
        data = self._load_data(self.steps[0])

        # must set scale (log, linear) before making image
        self.ax.set_xscale(self.indep_scale)
        self.ax.set_yscale(self.indep_scale)

        self.im = self.ax.imshow(
            data.T,
            origin="lower",
            extent=(*get_extent(data, self.dims[0]), *get_extent(data, self.dims[1])),
            norm={"linear": Normalize(), "log": LogNorm()}[self.dep_scale],
        )

        self.fig.colorbar(self.im)
        data_lower, data_upper = self._get_var_bounds()
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(self.ax, self.dep_var_name, DIMENSIONS["t"].get_coordinate_label(data.time))

        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.ax.set_xlabel(DIMENSIONS[self.dims[0]].to_axis_label())
        self.ax.set_ylabel(DIMENSIONS[self.dims[1]].to_axis_label())

        self.fig.tight_layout()

    def _update_fig(self, step: int):
        data = self._load_data(step)

        self.im.set_array(data.T)

        plt_util.update_title(self.ax, self.dep_var_name, DIMENSIONS["t"].get_coordinate_label(data.time))
        return [self.im, self.ax.title]


class FieldAnimation2dPolar(FieldAnimation):
    ax: PolarAxes

    def __init__(
        self,
        steps: list[int],
        prefix: file_util.FieldPrefix,
        variable: str,
        pipeline: FieldPipeline,
        dims: tuple[str, str],
    ):
        super().__init__(steps, prefix, variable, pipeline, subplot_kw={"projection": "polar"})

        self.dims = dims

    def _init_fig(self):
        data = self._load_data(self.steps[0])

        # must set scale (log, linear) before making image
        if self.indep_scale == "log":
            self.ax.set_rscale("symlog")

        vertices_theta = np.concat((data.coords[self.dims[1]].data, [2 * np.pi]))
        vertices_theta -= vertices_theta[1] / 2
        vertices_r = list(data.coords[self.dims[0]].data)
        vertices_r += [vertices_r[-1] + vertices_r[1]]

        self.im = self.ax.pcolormesh(
            *np.meshgrid(vertices_theta, vertices_r),
            data,
            shading="flat",
            norm={"linear": Normalize(), "log": LogNorm()}[self.dep_scale],
        )

        self.fig.colorbar(self.im)
        data_lower, data_upper = self._get_var_bounds()
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(self.ax, self.dep_var_name, DIMENSIONS["t"].get_coordinate_label(data.time))

        # FIXME make the labels work
        # self.ax.set_xlabel(DIMENSIONS[self.dims[1]].to_axis_label())
        # self.ax.set_ylabel(DIMENSIONS[self.dims[0]].to_axis_label())

        self.fig.tight_layout()

    def _update_fig(self, step: int):
        data = self._load_data(step)

        self.im.set_array(data)

        plt_util.update_title(self.ax, self.dep_var_name, DIMENSIONS["t"].get_coordinate_label(data.time))
        return [self.im, self.ax.title]


class FieldAnimation1d(FieldAnimation):
    def __init__(
        self,
        steps: list[int],
        prefix: file_util.FieldPrefix,
        variable: str,
        pipeline: FieldPipeline,
        dim: str,
    ):
        super().__init__(steps, prefix, variable, pipeline)

        self.dim = dim

    def _init_fig(self):
        data = self._load_data(self.steps[0])
        xdata = np.linspace(*get_extent(data, self.dim), len(data), endpoint=False)

        [self.line] = self.ax.plot(xdata, data)

        plt_util.update_title(self.ax, self.dep_var_name, DIMENSIONS["t"].get_coordinate_label(data.time))
        self._update_ybounds()
        self.ax.set_xlabel(DIMENSIONS[self.dim].to_axis_label())
        self.ax.set_ylabel(f"${self.dep_var_name}$")

        self.ax.set_xscale(self.indep_scale)
        self.ax.set_yscale(self.dep_scale)

        self.fig.tight_layout()

    def _update_fig(self, step: int):
        data = self._load_data(step)

        self.line.set_ydata(data)

        plt_util.update_title(self.ax, self.dep_var_name, DIMENSIONS["t"].get_coordinate_label(data.time))
        return [self.line, self.ax.yaxis, self.ax.title]

    def _update_ybounds(self):
        ymin, ymax = plt_util.symmetrize_bounds(*self._get_var_bounds())
        self.ax.set_ybound(ymin, ymax)
