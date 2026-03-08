from mnemo.injector.block_builder import build_block, block_tags, render_block


def test_block_tags_format() -> None:
    start, end = block_tags("snapshot")
    assert "UNIFIED_BLOCK:snapshot:START" in start
    assert "UNIFIED_BLOCK:snapshot:END" in end


def test_build_block_defaults() -> None:
    block = build_block("urgent", "- a")
    assert block.block_id == "urgent"
    assert block.item_ids == []


def test_render_block_contains_marker() -> None:
    block = build_block("preconscious", "- id1")
    txt = render_block(block)
    assert "[UNIFIED_MEMORY_BLOCK_V1_DO_NOT_CAPTURE]" in txt
    assert "UNIFIED_BLOCK:preconscious:START" in txt
