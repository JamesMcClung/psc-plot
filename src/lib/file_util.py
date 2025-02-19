import pathlib


ROOT_DIR = pathlib.Path("/Users/james/Code/cc/PSC/psc-runs/psc_shock")


def get_available_steps(prefix: str, suffix: str) -> list[int]:
    files = ROOT_DIR.glob(f"{prefix}.*.{suffix}")
    steps = [int(file.name.split(".")[1]) for file in files]
    steps.sort()
    return steps
