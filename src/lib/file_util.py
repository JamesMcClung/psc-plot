import os
import pathlib
import typing

type BpPrefix = typing.Literal["pfd", "pfd_moments", "gauss", "continuity"]
BP_PREFIXES: list[BpPrefix] = list(BpPrefix.__value__.__args__)

type H5Prefix = typing.Literal["prt"]
H5_PREFIXES: list[H5Prefix] = list(H5Prefix.__value__.__args__)

type Prefix = BpPrefix | H5Prefix
type Suffix = typing.Literal["bp", "h5"]


def _load_root_data_path() -> pathlib.Path:
    maybe_path_str = os.environ.get(ROOT_DATA_PATH_ENV_VAR_NAME)
    if maybe_path_str:
        return pathlib.Path(maybe_path_str)

    message = f"Path to data not specified. Set the {ROOT_DATA_PATH_ENV_VAR_NAME} environment variable to specify."
    raise RuntimeError(message)


ROOT_DATA_PATH_ENV_VAR_NAME = "PSC_PLOT_ROOT_DATA_PATH"
ROOT_DIR = _load_root_data_path()
PREFIX_TO_SUFFIX: dict[Prefix, Suffix] = {bp_prefix: "bp" for bp_prefix in BP_PREFIXES} | {h5_prefix: "h5" for h5_prefix in H5_PREFIXES}


def get_available_steps(before_step: str, after_step: str) -> list[int]:
    files = ROOT_DIR.glob(f"{before_step}*{after_step}")
    steps = [int(file.name.removeprefix(before_step).removesuffix(after_step)) for file in files]

    if not steps:
        raise ValueError(f"No steps found matching {ROOT_DIR}/{before_step}*{after_step}")

    steps.sort()
    return steps
