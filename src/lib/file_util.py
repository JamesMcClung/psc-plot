import pathlib


ROOT_DIR = pathlib.Path("/Users/james/Code/cc/PSC/psc-runs/psc_shock")


def get_available_steps(before_step: str, after_step: str) -> list[int]:
    files = ROOT_DIR.glob(f"{before_step}*{after_step}")
    steps = [int(file.name.removeprefix(before_step).removesuffix(after_step)) for file in files]
    steps.sort()
    return steps


def get_data_path(prefix: str, step: int, suffix: str) -> pathlib.Path:
    return ROOT_DIR / f"{prefix}.{step:09}.{suffix}"
