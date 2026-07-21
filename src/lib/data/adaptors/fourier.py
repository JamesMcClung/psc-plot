import numpy as np
import xarray as xr
import xrft

from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.var_info import VarInfo


def toggle_fourier(da: xr.DataArray, info: VarInfo) -> xr.DataArray:
    temp_prefix = "temp_"
    f_info = info.toggle_fourier()

    # multiply/or divide coords by 2pi to go from frequency <-> angular frequency

    if info.is_fourier():
        da = da.assign_coords({info.key: da.coords[info.key] / (2 * np.pi)})
        da = xrft.ifft(da, dim=info.key, prefix=temp_prefix, lag=0.0)
        da = da.rename({temp_prefix + info.key: f_info.key})
    else:
        da = xrft.fft(da, dim=info.key, prefix=temp_prefix)
        da = da.rename({temp_prefix + info.key: f_info.key})
        da = da.assign_coords({f_info.key: da.coords[f_info.key] * (2 * np.pi)})

    return da


class Fourier(MetadataAdaptor):
    def __init__(self, dim_keys: str | list[str]):
        if isinstance(dim_keys, str):
            dim_keys = [dim_keys]
        self.dim_keys = dim_keys

    def apply_field(self, data: Field) -> Field:
        pre_dim_latexs = [data.metadata.var_infos[key].display.latex for key in self.dim_keys]

        da = data.active_data
        new_var_infos = data.metadata.var_infos.copy()

        for key in self.dim_keys:
            info = new_var_infos[key]
            f_info = info.toggle_fourier()
            new_var_infos[f_info.key] = f_info
            da = toggle_fourier(da, info)

        old_active_info = data.metadata.active_var_info
        new_display = f"\\mathcal{{F}}_{{{','.join(pre_dim_latexs)}}}[{old_active_info.display}]"
        new_var_infos[data.metadata.active_key] = old_active_info.assign(display=new_display)

        return data.with_active_data(da).assign_metadata(var_infos=new_var_infos)

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
        parse_util.parse_identifier(dim_name, "dim_name")

    return Fourier(args)
