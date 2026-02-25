import dask

from lib import parsing

dask.config.set(num_workers=1)

args = parsing.get_parsed_args()

anim = args.get_animation()

if args.show:
    anim.show()
if args.save is not None:
    args.save.mkdir(exist_ok=True)
    anim.save(args.save)
