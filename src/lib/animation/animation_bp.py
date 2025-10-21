import numpy as np
import xarray as xr

from .. import bp_util, file_util, plt_util
from ..derived_variables_bp import DERIVED_VARIABLE_BP_REGISTRY
from ..dimension import DIMENSIONS
from ..plugins import PluginBp
from .animation_base import Animation

__all__ = ["BpAnimation2d", "BpAnimation1d"]


def get_extent(da: xr.DataArray, dim: str) -> tuple[float, float]:
    lower = da[dim][0]
    upper = da[dim][-1] + (da[dim][1] - da[dim][0])
    return (float(lower), float(upper))


def derive_variable(ds: xr.Dataset, var_name: str, ds_prefix: file_util.BpPrefix):
    if var_name in ds.variables:
        return
    elif var_name in DERIVED_VARIABLE_BP_REGISTRY[ds_prefix]:
        derived_var = DERIVED_VARIABLE_BP_REGISTRY[ds_prefix][var_name]
        for base_var_name in derived_var.base_var_names:
            derive_variable(ds, base_var_name, ds_prefix)
        derived_var.assign_to(ds)
    else:
        message = f"No variable named '{var_name}'.\nThe following variables are defined: {list(ds.variables)}\n The following variables can be derived: {list(DERIVED_VARIABLE_BP_REGISTRY[ds_prefix])}"
        raise ValueError(message)


class BpAnimation(Animation):
    def __init__(self, steps: list[int], prefix: file_util.BpPrefix, variable: str):
        super().__init__(steps)

        self.prefix = prefix
        self.variable = variable

        self.plugins: list[PluginBp] = []

    def add_plugin(self, plugin: PluginBp):
        self.plugins.append(plugin)

    def _load_data(self, step: int) -> xr.DataArray:
        ds = bp_util.load_ds(self.prefix, step)
        derive_variable(ds, self.variable, self.prefix)
        da = ds[self.variable]

        for plugin in self.plugins:
            da = plugin.apply(da)

        da = da.assign_attrs(**ds.attrs)

        return da

    def _get_var_bounds(self) -> tuple[float, float]:
        lower = np.inf
        upper = -np.inf
        for step in self.steps:
            data = self._load_data(step)
            lower = min(lower, np.nanmin(data.data))
            upper = max(upper, np.nanmax(data.data))

        return (lower, upper)


class RetainDims(PluginBp):
    def __init__(self, dims: list[str]):
        self.dims = dims

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        for dim in da.dims:
            if dim not in self.dims:
                da = da.reduce(np.mean, dim)
        return da


class ReorderDims(PluginBp):
    def __init__(self, ordered_dims: list[str]):
        self.ordered_dims = ordered_dims

    def apply(self, da: xr.DataArray) -> xr.DataArray:
        return da.transpose(*self.ordered_dims, transpose_coords=True)


class BpAnimation2d(BpAnimation):
    def __init__(self, steps: list[int], prefix: file_util.BpPrefix, variable: str, dims: tuple[str, str]):
        super().__init__(steps, prefix, variable)

        self.dims = dims

        self.add_plugin(RetainDims(dims))
        self.add_plugin(ReorderDims(list(reversed(dims))))

    def _init_fig(self):
        data = self._load_data(self.steps[0])

        left_right_bottom_top = (*get_extent(data, self.dims[0]), *get_extent(data, self.dims[1]))
        self.im = self.ax.imshow(data, origin="lower", extent=left_right_bottom_top)

        self.fig.colorbar(self.im)
        data_lower, data_upper = self._get_var_bounds()
        plt_util.update_cbar(self.im, data_min_override=data_lower, data_max_override=data_upper)

        plt_util.update_title(self.ax, self.variable, DIMENSIONS["t"].get_coordinate_label(data.time))
        self.ax.set_aspect(1 / self.ax.get_data_ratio())
        self.ax.set_xlabel(DIMENSIONS[self.dims[0]].to_axis_label())
        self.ax.set_ylabel(DIMENSIONS[self.dims[1]].to_axis_label())

    def _update_fig(self, step: int):
        data = self._load_data(step)

        self.im.set_array(data)

        plt_util.update_title(self.ax, self.variable, DIMENSIONS["t"].get_coordinate_label(data.time))
        return [self.im, self.ax.title]


class BpAnimation1d(BpAnimation):
    def __init__(self, steps: list[int], prefix: file_util.BpPrefix, variable: str, dim: str):
        super().__init__(steps, prefix, variable)

        self.dim = dim

        self.add_plugin(RetainDims([dim]))

    def _init_fig(self):
        data = self._load_data(self.steps[0])
        xdata = np.linspace(*get_extent(data, self.dim), len(data), endpoint=False)

        [self.line] = self.ax.plot(xdata, data)

        plt_util.update_title(self.ax, self.variable, DIMENSIONS["t"].get_coordinate_label(data.time))
        self._update_ybounds()
        self.ax.set_xlabel(DIMENSIONS[self.dim].to_axis_label())
        self.ax.set_ylabel(f"{self.variable}")

    def _update_fig(self, step: int):
        data = self._load_data(step)

        self.line.set_ydata(data)

        plt_util.update_title(self.ax, self.variable, DIMENSIONS["t"].get_coordinate_label(data.time))
        return [self.line, self.ax.yaxis, self.ax.title]

    def _update_ybounds(self):
        ymin, ymax = plt_util.symmetrize_bounds(*self._get_var_bounds())
        self.ax.set_ybound(ymin, ymax)
