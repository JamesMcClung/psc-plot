import numpy as np
import xarray as xr
import xrft

from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field
from lib.dimension import VarInfo
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser


def toggle_fourier(da: xr.DataArray, dim: VarInfo) -> xr.DataArray:
    temp_prefix = "temp_"
    f_dim = dim.toggle_fourier()

    # multiply/or divide coords by 2pi to go from frequency <-> angular frequency

    if dim.is_fourier():
        da = da.assign_coords({dim.key: da.coords[dim.key] / (2 * np.pi)})
        da = xrft.ifft(da, dim=dim.key, prefix=temp_prefix, lag=0.0)
        da = da.rename({temp_prefix + dim.key: f_dim.key})
    else:
        da = xrft.fft(da, dim=dim.key, prefix=temp_prefix)
        da = da.rename({temp_prefix + dim.key: f_dim.key})
        da = da.assign_coords({f_dim.key: da.coords[f_dim.key] * (2 * np.pi)})

    return da


class Fourier(MetadataAdaptor):
    def __init__(self, dim_keys: str | list[str]):
        if isinstance(dim_keys, str):
            dim_keys = [dim_keys]
        self.dim_keys = dim_keys

    def apply_field(self, data: Field) -> Field:
        pre_dim_latexs = [data.metadata.var_info[key].display.latex for key in self.dim_keys]

        da = data.active_data
        new_var_info = dict(data.metadata.var_info)
        for key in self.dim_keys:
            dim = new_var_info[key]
            f_dim = dim.toggle_fourier()
            da = toggle_fourier(da, dim)
            del new_var_info[key]
            new_var_info[f_dim.key] = f_dim

        if data.metadata.active_key is not None and data.metadata.active_key in new_var_info:
            old_active = new_var_info[data.metadata.active_key]
            new_display = f"\\mathcal{{F}}_{{{','.join(pre_dim_latexs)}}}[{old_active.display}]"
            new_var_info[data.metadata.active_key] = old_active.assign(display=new_display)

        return data.with_active_data(da).assign_metadata(var_info=new_var_info)

    def get_modified_display_latex(self, metadata) -> str:
        return metadata.active_var_info.display.latex

    def get_modified_unit_latex(self, metadata) -> str:
        return metadata.active_var_info.unit.latex

    def get_name_fragments(self) -> list[str]:
        return [f"fourier_{','.join(self.dim_keys)}"]


FOURIER_FORMAT = "dim_name"


@arg_parser(
    dest="adaptors",
    flags=["--fourier", "-f"],
    metavar=FOURIER_FORMAT,
    help="perform a Fourier transform along the given dimensions",
    nargs="+",
)
def parse_fourier(args: list[str]) -> Fourier:
    for dim_name in args:
        parse_util.check_identifier(dim_name, "dim_name")

    return Fourier(args)
