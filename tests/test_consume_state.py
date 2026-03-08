import json
from pathlib import Path

from mnemo.consumer.consume_state import UnifiedConsumeState


def test_load_default(tmp_path: Path) -> None:
    st = UnifiedConsumeState(tmp_path)
    data = st.load()
    assert data["version"] == "1.0"


def test_update_block_persists(tmp_path: Path) -> None:
    st = UnifiedConsumeState(tmp_path)
    st.update_block("snapshot", "2026-01-01T00:00:00Z", "h1")
    data = st.load()
    assert data["blocks"]["snapshot"]["hash"] == "h1"


def test_migrate_from_legacy(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy"
    legacy.mkdir(parents=True)
    (legacy / "preconscious_consumed.json").write_text(json.dumps({"delivered": {"x": "t"}, "pruned": {}}), encoding="utf-8")
    (legacy / "preconscious_inject_hash.json").write_text(json.dumps({"last_hash": "ph", "last_injected_at": "pt"}), encoding="utf-8")
    (legacy / "snapshot_inject_hash.json").write_text(json.dumps({"last_hash": "sh", "updated_at": "st"}), encoding="utf-8")

    st = UnifiedConsumeState(tmp_path)
    out = st.migrate_from_legacy(legacy)
    assert out["blocks"]["preconscious"]["hash"] == "ph"
    assert out["blocks"]["snapshot"]["hash"] == "sh"
    assert out["blocks"]["preconscious"]["consumed_ids"]["x"]["status"] == "injected"
