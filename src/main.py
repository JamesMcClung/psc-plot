import argparse
import numpy as np

from lib import bp_util, h5_util, file_util
from lib.animation import H5Animation, BpAnimation


class TypedArgs(argparse.Namespace):
    prefix: file_util.Prefix
    variable: str

    @property
    def suffix(self) -> file_util.Suffix:
        return file_util.PREFIX_TO_SUFFIX[self.prefix]


parser = argparse.ArgumentParser("psc-plot")
parser.add_argument("prefix", choices=file_util.PREFIX_TO_SUFFIX.keys())
parser.add_argument("-v", "--variable")

args = parser.parse_args(namespace=TypedArgs())

print(args)

if args.suffix == "bp":
    bp_name = "pfd_moments"
    bp_var = "rho_e"
    steps = bp_util.get_available_steps_bp(bp_name)

    anim = BpAnimation(steps, bp_name, bp_var)
    anim.show()
elif args.suffix == "h5":
    h5_name = "prt"
    steps = h5_util.get_available_steps_h5(h5_name)

    x_edges = np.linspace(0, 500, 1000, endpoint=True)
    y_edges = np.linspace(0, 20, 40, endpoint=True)

    anim = H5Animation(steps, h5_name, ("y", "z"), (x_edges, y_edges))
    anim.show()
else:
    raise Exception(f"Unrecognized suffix: {args.suffix}")
