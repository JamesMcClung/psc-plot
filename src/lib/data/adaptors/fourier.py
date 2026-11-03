import argparse

import numpy as np
import xarray as xr
import xrft

from lib.data.adaptor import MetadataAdaptor
from lib.data.data_with_attrs import Field
from lib.parsing import parse_util
from lib.parsing.args_registry import arg_parser
from lib.var_info import FOURIER_ANGLES, FourierAngle, VarInfo


def _scale_coord(da: xr.DataArray, key: str, factor: float) -> xr.DataArray:
    coord = da.coords[key]
    return da.assign_coords({key: (coord * factor).assign_attrs(coord.attrs)})


def toggle_fourier(da: xr.DataArray, info: VarInfo, f_info: VarInfo) -> xr.DataArray:
    temp_prefix = "temp_"

    # xrft's frequencies are in revolutions; multiply/divide by 2pi to go to/from radians

    if info.is_fourier():
        if info.fourier_angle == "rad":
            da = _scale_coord(da, info.key, 1 / (2 * np.pi))
        # fft recorded the original coords' offset; passing it back restores them
        da = xrft.ifft(da, dim=info.key, prefix=temp_prefix, lag=da.coords[info.key].attrs["direct_lag"])
        da = da.rename({temp_prefix + info.key: f_info.key})
    else:
        da = xrft.fft(da, dim=info.key, prefix=temp_prefix)
        da = da.rename({temp_prefix + info.key: f_info.key})
        if f_info.fourier_angle == "rad":
            da = _scale_coord(da, f_info.key, 2 * np.pi)

    return da


def _conjugate_info(info: VarInfo, angle: FourierAngle) -> VarInfo:
    if not info.is_fourier():
        return info.to_fourier(angle)
    if info.fourier_angle != angle:
        raise ValueError(f"{info.key} is in {info.fourier_angle}, not {angle}; inverse transform it with {info.key}={info.fourier_angle}")
    return info.from_fourier()


class Fourier(MetadataAdaptor):
    def __init__(self, dims: dict[str, FourierAngle], *, no_display: bool = False, positive_only: bool = False, drop_nyquist: bool = False):
        self.dims = dims
        self.no_display = no_display
        self.positive_only = positive_only
        self.drop_nyquist = drop_nyquist

    def _options(self) -> list[str]:
        flags = {"nodisplay": self.no_display, "positiveonly": self.positive_only, "dropnyquist": self.drop_nyquist}
        return [option for option, flag in flags.items() if flag]

    def apply_field(self, data: Field) -> Field:
        pre_dim_latexs = [data.metadata.var_infos[key].display.latex for key in self.dims]
        forward_only_options = [option for option in self._options() if option in FORWARD_ONLY_OPTIONS]

        da = data.require_active_subdata()
        new_var_infos = data.metadata.var_infos.copy()

        for key, angle in self.dims.items():
            info = new_var_infos[key]
            if info.is_fourier() and forward_only_options:
                raise ValueError(f"--fourier {' '.join(forward_only_options)} only applies to forward transforms, but {key} is already a Fourier dimension")
            f_info = _conjugate_info(info, angle)
            new_var_infos[f_info.key] = f_info
            da = toggle_fourier(da, info, f_info)

            # xrft orders modes from -N/2 up, so an even length's unpaired Nyquist mode comes first
            if self.drop_nyquist and da.sizes[f_info.key] % 2 == 0:
                da = da.isel({f_info.key: slice(1, None)})
            if self.positive_only:
                da = da.isel({f_info.key: da.coords[f_info.key].values > 0})

        if not self.no_display:
            old_active_info = data.active_info
            new_display = f"\\mathcal{{F}}_{{{','.join(pre_dim_latexs)}}}[{old_active_info.display}]"
            new_var_infos[data.metadata.active_key] = old_active_info.assign(display=new_display)

        return data.with_active(data=da).assign(var_infos=new_var_infos)

    def get_name_fragments(self) -> list[str]:
        dims = ",".join(f"{key}={angle}" for key, angle in self.dims.items())
        return ["_".join(["fourier", *self._options(), dims])]


FORWARD_ONLY_OPTIONS = ("positiveonly", "dropnyquist")
FOURIER_OPTIONS = {"nodisplay": "no_display", "positiveonly": "positive_only", "dropnyquist": "drop_nyquist"}
FOURIER_FORMAT = f"[{'] ['.join(FOURIER_OPTIONS)}] dim_key[,dim_key...]={{rev,rad}} [...]"


@arg_parser(
    dest="adaptors",
    flags=["--fourier", "-f"],
    metavar=FOURIER_FORMAT,
    help="perform a Fourier transform along the given dimensions, measuring the conjugate dimension in revolutions (rev) or radians (rad) per original unit; transforming a Fourier dimension (e.g. k_y) inverts it. Options: nodisplay leaves the variable's label alone; positiveonly keeps only modes with k > 0; dropnyquist drops the unpaired Nyquist mode of even-length dimensions",
    nargs="+",
)
def parse_fourier(args: list[str]) -> Fourier:
    dims = {}
    options = {}
    for arg in args:
        if "=" not in arg:
            option = parse_util.parse_value(arg, "option", FOURIER_OPTIONS)
            options[FOURIER_OPTIONS[option]] = True
            continue
        dims_arg, angle_arg = parse_util.parse_assignment(arg, FOURIER_FORMAT)
        angle = parse_util.parse_value(angle_arg, "angle", FOURIER_ANGLES)
        for dim_key in parse_util.parse_comma_separated_list(dims_arg):
            parse_util.parse_identifier(dim_key, "dim_key")
            dims[dim_key] = angle

    if not dims:
        raise argparse.ArgumentTypeError(f"Expected at least one dimension of form 'dim_key[,dim_key...]={{rev,rad}}'; got only options {args}")

    return Fourier(dims, **options)
