def _distributed_available() -> bool:
    # not importlib.util.find_spec: dask ships a dask.distributed shim that exists, then fails to import, without the distributed package
    try:
        import dask.distributed  # noqa: F401
    except ImportError:
        return False
    return True


def candidate_schedulers() -> list[str]:
    """The schedulers --suggest-config times. synchronous is never faster than threads, only easier to debug."""
    return ["threads", "processes", *(["distributed"] if _distributed_available() else [])]


def guess_scheduler(workers: int) -> str:
    """The scheduler to suggest without a pipeline to measure."""
    return "distributed" if workers > 1 and _distributed_available() else "threads"
