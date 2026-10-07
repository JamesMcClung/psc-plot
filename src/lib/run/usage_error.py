class UsageError(Exception):
    """The run can't proceed with these flags in this environment. `cli.main` prints it as `error: <message>` and exits 1."""
