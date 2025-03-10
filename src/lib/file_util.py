import pathlib
import typing

type Prefix = typing.Literal["pfd", "pfd_moments", "prt"]
type Suffix = typing.Literal["bp", "h5"]

ROOT_DIR = pathlib.Path("/Users/james/Code/cc/PSC/psc-runs/psc_shock")
PREFIX_TO_SUFFIX: dict[Prefix, Suffix] = {
    "pfd": "bp",
    "pfd_moments": "bp",
    "prt": "h5",
}


def get_available_steps(before_step: str, after_step: str) -> list[int]:
    files = ROOT_DIR.glob(f"{before_step}*{after_step}")
    steps = [int(file.name.removeprefix(before_step).removesuffix(after_step)) for file in files]
    steps.sort()
    return steps
