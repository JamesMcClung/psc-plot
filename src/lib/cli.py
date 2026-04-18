import sys
import warnings

import dask
import matplotlib.pyplot as plt

from lib import parsing
from lib.config import CONFIG
from lib.parsing.args import Args
from lib.plotting.plot import SaveFormat


def _resolve_save_format(args: Args) -> SaveFormat | None:
    if args.save is None:
        if args.save_format is not None:
            print("error: --save-format requires --save", file=sys.stderr)
            sys.exit(1)
        return None

    if args.save_format == "mp4":
        if not CONFIG.ffmpeg_bin:
            print("error: --save-format mp4 requires ffmpeg", file=sys.stderr)
            sys.exit(1)
        return "mp4"

    if args.save_format == "gif":
        return "gif"

    # save_format is None: try mp4, fall back to gif
    if CONFIG.ffmpeg_bin:
        return "mp4"

    message = "ffmpeg not found; will save animations as gif instead of mp4"
    warnings.warn(message)
    return "gif"


def main():
    dask.config.set(num_workers=CONFIG.dask_num_workers)

    args = parsing.get_parsed_args()
    # resolve format BEFORE applying pipeline in order to fail early
    format = _resolve_save_format(args)

    if format == "mp4":
        plt.rcParams["animation.ffmpeg_path"] = str(CONFIG.ffmpeg_bin)

    plot = args.get_animation()

    if args.show:
        plot.show()
    if args.save is not None:
        args.save.mkdir(exist_ok=True)

        if format not in plot.allowed_save_formats():
            if format == args.save_format:  # user actually specified this format
                message = f"{format} is incompatible with the data; reverting to default ({plot.default_save_format()})"
                warnings.warn(message)
            else:
                assert args.save_format is None

            format = plot.default_save_format()

        plot.save(args.save, format=format)
