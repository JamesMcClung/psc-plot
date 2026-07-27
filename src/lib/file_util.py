from pathlib import Path

type Prepath = str
"""Path from data root directory to the data-containing directory plus the data prefix, e.g. `"run5/pfd"`."""


def get_available_steps(data_dir: Path, before_step: str, after_step: str) -> list[int]:
    files = data_dir.glob(f"{before_step}*{after_step}")
    steps = [int(file.name.removeprefix(before_step).removesuffix(after_step)) for file in files]

    if not steps:
        raise ValueError(f"No steps found matching {data_dir}/{before_step}*{after_step}")

    steps.sort()
    return steps


def split_prepath(prepath: Prepath) -> tuple[Path, str]:
    components = prepath.rsplit("/", maxsplit=1)
    if len(components) == 1:
        return (Path("."), components[0])
    return Path(components[0]), components[1]
