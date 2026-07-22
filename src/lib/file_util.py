from pathlib import Path


def get_available_steps(data_dir: Path, before_step: str, after_step: str) -> list[int]:
    files = data_dir.glob(f"{before_step}*{after_step}")
    steps = [int(file.name.removeprefix(before_step).removesuffix(after_step)) for file in files]

    if not steps:
        raise ValueError(f"No steps found matching {data_dir}/{before_step}*{after_step}")

    steps.sort()
    return steps
