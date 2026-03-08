from pathlib import Path

from mnemo.injector.hash_debounce import HashDebounceStore, canonicalize, compute_hash


def test_canonicalize_removes_dynamic_keys() -> None:
    obj = {"a": 1, "updated_at": "x", "nested": {"timestamp": "y", "b": 2}}
    out = canonicalize(obj)
    assert "updated_at" not in out
    assert "timestamp" not in out["nested"]


def test_compute_hash_stable() -> None:
    assert compute_hash("abc") == compute_hash("abc")


def test_store_set_and_get(tmp_path: Path) -> None:
    store = HashDebounceStore(tmp_path)
    store.set_hash("snapshot", "h1", "2026-01-01T00:00:00Z", ["id1"])
    assert store.get_hash("snapshot") == "h1"
