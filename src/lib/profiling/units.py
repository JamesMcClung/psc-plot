_MIN_WALL_FOR_CORES = 0.05


def format_bytes(n: int | None) -> str:
    return "n/a" if n is None else f"{n / 2**30:.1f} GB"


def format_cores(cpu: float, wall: float) -> str:
    """Cores busy on average, or "-" when the wall is too short for the ratio to mean anything."""
    return f"{cpu / wall:.1f}" if wall >= _MIN_WALL_FOR_CORES else "-"
