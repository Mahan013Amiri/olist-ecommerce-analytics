"""I/O utilities: parquet read/write and cache-hash logic (Task 1.3)."""

from pathlib import Path

import pandas as pd


def read_parquet(path: Path) -> pd.DataFrame:
    """Read a parquet file and return a DataFrame."""
    return pd.read_parquet(path)


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write a DataFrame to parquet, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def file_exists(path: Path) -> bool:
    """Check whether a file exists at the given path."""
    return path.is_file()