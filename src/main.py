import dask
import matplotlib.pyplot as plt

from lib import parsing
from lib.config import CONFIG

dask.config.set(num_workers=1)

args = parsing.get_parsed_args()

anim = args.get_animation()

if args.show:
    anim.show()
if args.save is not None:
    if CONFIG.ffmpeg_bin:
        plt.rcParams["animation.ffmpeg_path"] = CONFIG.ffmpeg_bin
    args.save.mkdir(exist_ok=True)
    anim.save(args.save)
