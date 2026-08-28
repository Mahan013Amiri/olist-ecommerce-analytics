"""Smoke tests for project setup (Task 0.1)."""

from pathlib import Path

from src.utils.config import (
    CLEAN_TABLES,
    DATA_DIR,
    INTERIM_DATA_DIR,
    PROCESSED_DATA_DIR,
    PROJECT_ROOT,
    RAW_DATA_DIR,
    RAW_TABLES,
)


def test_project_root_exists():
    assert PROJECT_ROOT.is_dir()


def test_data_directories_exist():
    for directory in (DATA_DIR, RAW_DATA_DIR, INTERIM_DATA_DIR, PROCESSED_DATA_DIR):
        assert directory.is_dir(), f"Missing: {directory}"


def test_raw_tables_count():
    assert len(RAW_TABLES) == 9


def test_clean_tables_count():
    assert len(CLEAN_TABLES) == 8


def test_docs_exist():
    docs = PROJECT_ROOT / "docs"
    for filename in ("architecture.md", "grain_registry.md", "feature_registry.md"):
        assert (docs / filename).is_file(), f"Missing: {filename}"
