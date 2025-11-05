import os
import pathlib
import typing

type FieldPrefix = typing.Literal["pfd", "pfd_moments", "gauss", "continuity"]
FIELD_PREFIXES: list[FieldPrefix] = list(FieldPrefix.__value__.__args__)

type ParticlePrefix = typing.Literal["prt"]
PARTICLE_PREFIXES: list[ParticlePrefix] = list(ParticlePrefix.__value__.__args__)

type Prefix = FieldPrefix | ParticlePrefix
type Suffix = typing.Literal["bp", "h5"]


def _load_root_data_path() -> pathlib.Path:
    maybe_path_str = os.environ.get(ROOT_DATA_PATH_ENV_VAR_NAME)
    if maybe_path_str:
        return pathlib.Path(maybe_path_str)

    message = f"Path to data not specified. Set the {ROOT_DATA_PATH_ENV_VAR_NAME} environment variable to specify."
    raise RuntimeError(message)


ROOT_DATA_PATH_ENV_VAR_NAME = "PSC_PLOT_ROOT_DATA_PATH"
ROOT_DIR = _load_root_data_path()
PREFIX_TO_SUFFIX: dict[Prefix, Suffix] = {field_prefix: "bp" for field_prefix in FIELD_PREFIXES} | {particle_prefix: "h5" for particle_prefix in PARTICLE_PREFIXES}


def get_available_steps(before_step: str, after_step: str) -> list[int]:
    files = ROOT_DIR.glob(f"{before_step}*{after_step}")
    steps = [int(file.name.removeprefix(before_step).removesuffix(after_step)) for file in files]

    if not steps:
        raise ValueError(f"No steps found matching {ROOT_DIR}/{before_step}*{after_step}")

    steps.sort()
    return steps
