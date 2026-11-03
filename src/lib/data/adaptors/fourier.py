import numpy as np
import xarray as xr
import xrft

from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.var_info import FOURIER_ANGLES, FourierAngle, VarInfo


def toggle_fourier(da: xr.DataArray, info: VarInfo, f_info: VarInfo) -> xr.DataArray:
    temp_prefix = "temp_"

    # xrft's frequencies are in revolutions; multiply/divide by 2pi to go to/from radians

    if info.is_fourier():
        if info.fourier_angle == "rad":
            da = da.assign_coords({info.key: da.coords[info.key] / (2 * np.pi)})
        da = xrft.ifft(da, dim=info.key, prefix=temp_prefix, lag=0.0)
        da = da.rename({temp_prefix + info.key: f_info.key})
    else:
        da = xrft.fft(da, dim=info.key, prefix=temp_prefix)
        da = da.rename({temp_prefix + info.key: f_info.key})
        if f_info.fourier_angle == "rad":
            da = da.assign_coords({f_info.key: da.coords[f_info.key] * (2 * np.pi)})

    return da


def _conjugate_info(info: VarInfo, angle: FourierAngle) -> VarInfo:
    if not info.is_fourier():
        return info.to_fourier(angle)
    if info.fourier_angle != angle:
        raise ValueError(f"{info.key} is in {info.fourier_angle}, not {angle}; inverse transform it with {info.key}={info.fourier_angle}")
    return info.from_fourier()


class Fourier(MetadataAdaptor):
    def __init__(self, dims: dict[str, FourierAngle]):
        self.dims = dims

    def apply_field(self, data: Field) -> Field:
        pre_dim_latexs = [data.metadata.var_infos[key].display.latex for key in self.dims]

        da = data.require_active_subdata()
        new_var_infos = data.metadata.var_infos.copy()

        for key, angle in self.dims.items():
            info = new_var_infos[key]
            f_info = _conjugate_info(info, angle)
            new_var_infos[f_info.key] = f_info
            da = toggle_fourier(da, info, f_info)

        old_active_info = data.active_info
        new_display = f"\\mathcal{{F}}_{{{','.join(pre_dim_latexs)}}}[{old_active_info.display}]"
        new_var_infos[data.metadata.active_key] = old_active_info.assign(display=new_display)

        return data.with_active(data=da).assign(var_infos=new_var_infos)

    def get_name_fragments(self) -> list[str]:
        return [f"fourier_{','.join(f'{key}={angle}' for key, angle in self.dims.items())}"]


FOURIER_FORMAT = "dim_key={rev,rad}"


@arg_parser(
    dest="adaptors",
    flags=["--fourier", "-f"],
    metavar=FOURIER_FORMAT,
    help="perform a Fourier transform along the given dimensions, measuring the conjugate dimension in revolutions (rev) or radians (rad) per original unit; transforming a Fourier dimension (e.g. k_y) inverts it",
    nargs="+",
)
def parse_fourier(args: list[str]) -> Fourier:
    dims = {}
    for arg in args:
        dim_key, angle = parse_util.parse_assignment(arg, FOURIER_FORMAT)
        parse_util.parse_identifier(dim_key, "dim_key")
        dims[dim_key] = parse_util.parse_value(angle, "angle", FOURIER_ANGLES)

    return Fourier(dims)
