"""Tests for pipeline caching: load_data(rebuild=False). (Task 1.3)"""

import pandas as pd
import pytest

from src.data import pipeline


def _sample_df(n_rows: int = 3) -> pd.DataFrame:
    return pd.DataFrame({"id": range(n_rows), "value": [f"v{i}" for i in range(n_rows)]})


@pytest.fixture(autouse=True)
def small_table_lists(monkeypatch):
    """Use a tiny 2-table universe instead of the real 8/9 tables, so tests
    stay fast and independent of the actual project schema."""
    monkeypatch.setattr(pipeline, "CLEAN_TABLES", ["orders", "customers"])
    monkeypatch.setattr(pipeline, "RAW_TABLES", ["orders", "customers"])


@pytest.fixture
def fake_dirs(tmp_path, monkeypatch):
    processed_dir = tmp_path / "processed"
    interim_dir = tmp_path / "interim"
    monkeypatch.setattr(pipeline, "PROCESSED_DATA_DIR", processed_dir)
    monkeypatch.setattr(pipeline, "INTERIM_DATA_DIR", interim_dir)
    return processed_dir, interim_dir


def _write_processed_cache(processed_dir, table_names):
    for name in table_names:
        pipeline.write_parquet(_sample_df(), processed_dir / f"{name}_clean.parquet")


def _write_interim_cache(interim_dir, table_names):
    for name in table_names:
        pipeline.write_parquet(_sample_df(), interim_dir / f"{name}.parquet")


def test_uses_processed_cache_when_available(fake_dirs, monkeypatch):
    processed_dir, _ = fake_dirs
    _write_processed_cache(processed_dir, pipeline.CLEAN_TABLES)

    def _fail_ingest():
        pytest.fail("ingest_all() should not be called when processed cache is complete")

    def _fail_clean(interim):
        pytest.fail("clean_all_tables() should not be called when processed cache is complete")

    monkeypatch.setattr(pipeline, "ingest_all", _fail_ingest)
    monkeypatch.setattr(pipeline, "clean_all_tables", _fail_clean)

    result = pipeline.load_data(rebuild=False)

    assert set(result.keys()) == set(pipeline.CLEAN_TABLES)
    for name in pipeline.CLEAN_TABLES:
        assert len(result[name]) == 3


def test_uses_interim_cache_when_processed_missing(fake_dirs, monkeypatch):
    processed_dir, interim_dir = fake_dirs
    _write_interim_cache(interim_dir, pipeline.RAW_TABLES)

    def _fail_ingest():
        pytest.fail("ingest_all() should not be called when interim cache is complete")

    calls = {}

    def _fake_clean(interim):
        calls["interim_keys"] = set(interim.keys())
        return {name: _sample_df(n_rows=5) for name in pipeline.CLEAN_TABLES}

    monkeypatch.setattr(pipeline, "ingest_all", _fail_ingest)
    monkeypatch.setattr(pipeline, "clean_all_tables", _fake_clean)

    result = pipeline.load_data(rebuild=False)

    assert calls["interim_keys"] == set(pipeline.RAW_TABLES)
    assert all(len(df) == 5 for df in result.values())
    # cleaned tables must have been persisted to the processed cache
    for name in pipeline.CLEAN_TABLES:
        assert (processed_dir / f"{name}_clean.parquet").is_file()


def test_rebuild_true_forces_ingestion_even_if_caches_exist(fake_dirs, monkeypatch):
    processed_dir, interim_dir = fake_dirs
    _write_processed_cache(processed_dir, pipeline.CLEAN_TABLES)
    _write_interim_cache(interim_dir, pipeline.RAW_TABLES)

    calls = {"ingest": False, "clean": False}

    def _fake_ingest():
        calls["ingest"] = True
        return {name: _sample_df() for name in pipeline.RAW_TABLES}

    def _fake_clean(interim):
        calls["clean"] = True
        return {name: _sample_df() for name in pipeline.CLEAN_TABLES}

    monkeypatch.setattr(pipeline, "ingest_all", _fake_ingest)
    monkeypatch.setattr(pipeline, "clean_all_tables", _fake_clean)

    pipeline.load_data(rebuild=True)

    assert calls["ingest"] is True
    assert calls["clean"] is True


def test_calls_ingest_when_no_cache_exists(fake_dirs, monkeypatch):
    calls = {"ingest": False}

    def _fake_ingest():
        calls["ingest"] = True
        return {name: _sample_df() for name in pipeline.RAW_TABLES}

    def _fake_clean(interim):
        return {name: _sample_df() for name in pipeline.CLEAN_TABLES}

    monkeypatch.setattr(pipeline, "ingest_all", _fake_ingest)
    monkeypatch.setattr(pipeline, "clean_all_tables", _fake_clean)

    pipeline.load_data(rebuild=False)

    assert calls["ingest"] is True