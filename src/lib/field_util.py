from pathlib import Path

from lib.config import CONFIG

from . import file_util


def get_available_field_steps(prefix: file_util.FieldPrefix) -> list[int]:
    return file_util.get_available_steps(f"{prefix}.", ".bp")


def get_path(prefix: file_util.FieldPrefix, step: int) -> Path:
    return CONFIG.data_dir / f"{prefix}.{step:09}.bp"
