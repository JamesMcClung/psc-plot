def format_bytes(n: int | None) -> str:
    return "n/a" if n is None else f"{n / 2**30:.1f} GB"
