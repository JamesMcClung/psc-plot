import typing

from lib.config import CONFIG

type FieldPrefix = typing.Literal["pfd", "pfd_moments", "gauss", "continuity"]
FIELD_PREFIXES: list[FieldPrefix] = list(FieldPrefix.__value__.__args__)

type ParticlePrefix = typing.Literal["prt"]
PARTICLE_PREFIXES: list[ParticlePrefix] = list(ParticlePrefix.__value__.__args__)

type Prefix = FieldPrefix | ParticlePrefix


def get_available_steps(before_step: str, after_step: str) -> list[int]:
    files = CONFIG.data_dir.glob(f"{before_step}*{after_step}")
    steps = [int(file.name.removeprefix(before_step).removesuffix(after_step)) for file in files]

    if not steps:
        raise ValueError(f"No steps found matching {CONFIG.data_dir}/{before_step}*{after_step}")

    steps.sort()
    return steps
