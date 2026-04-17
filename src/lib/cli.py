import sys
import warnings

import dask
import matplotlib.pyplot as plt

from lib import parsing
from lib.config import CONFIG


def _resolve_save_ext(args) -> str | None:
    if args.save is None:
        if args.save_format is not None:
            print("error: --save-format requires --save", file=sys.stderr)
            sys.exit(1)
        return None

    if args.save_format == "mp4":
        if not CONFIG.ffmpeg_bin:
            print("error: --save-format mp4 requires ffmpeg", file=sys.stderr)
            sys.exit(1)
        return ".mp4"

    if args.save_format == "gif":
        return ".gif"

    # save_format is None: try mp4, fall back to gif
    if CONFIG.ffmpeg_bin:
        return ".mp4"

    warnings.warn("ffmpeg not found; saving as gif instead of mp4")
    return ".gif"


def main():
    dask.config.set(num_workers=CONFIG.dask_num_workers)

    args = parsing.get_parsed_args()
    save_ext = _resolve_save_ext(args)

    if save_ext == ".mp4" and CONFIG.ffmpeg_bin:
        plt.rcParams["animation.ffmpeg_path"] = str(CONFIG.ffmpeg_bin)

    anim = args.get_animation()

    if args.show:
        anim.show()
    if args.save is not None:
        args.save.mkdir(exist_ok=True)
        anim.save(args.save, ext=save_ext)
