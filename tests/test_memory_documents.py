"""Tests for markdown memory document storage."""

from pathlib import Path

import yaml

from memory.documents import MemoryDocumentStore


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    _, payload = text.split("---\n", 1)
    raw_meta, body = payload.split("\n---\n", 1)
    meta = yaml.safe_load(raw_meta) or {}
    return meta, body


def test_ensure_initialized_creates_default_documents(tmp_path: Path):
    """Document store should create the expected markdown files."""
    store = MemoryDocumentStore(str(tmp_path / "memory"))
    store.ensure_initialized()

    assert store.shiyi_path.exists()
    assert store.identity_state_path.exists()
    assert store.user_path.exists()
    assert store.project_path.exists()
    assert store.insights_path.exists()


def test_write_initial_identity_overwrites_shiyi_and_user(tmp_path: Path):
    """Onboarding write should persist custom identity texts."""
    store = MemoryDocumentStore(str(tmp_path / "memory"))
    store.ensure_initialized()

    shiyi_identity = "你是十一，负责高效协作。"
    user_identity = "用户是腿哥，偏好 Python。"
    store.write_initial_identity(shiyi_identity, user_identity)

    shiyi_text = store.shiyi_path.read_text(encoding="utf-8")
    user_text = store.user_path.read_text(encoding="utf-8")
    assert shiyi_text.startswith("---\n")
    assert user_text.startswith("---\n")
    assert shiyi_identity in shiyi_text
    assert user_identity in user_text


def test_upsert_user_fact_adds_and_updates_key(tmp_path: Path):
    """Hard fields should be written into frontmatter and updated in place."""
    store = MemoryDocumentStore(str(tmp_path / "memory"))
    store.ensure_initialized()

    store.upsert_user_fact("display_name", "腿哥")
    store.upsert_user_fact("preferred_tech", "Python")
    store.upsert_user_fact("preferred_tech", "Go")
    store.upsert_user_fact("collab_note", "高效率")

    text = store.user_path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    assert meta.get("display_name") == "腿哥"
    assert "tech_stack" in text
    assert "Python" in text
    assert "Go" in text
    assert "- collab_note: 高效率" in body


def test_identity_state_read_and_write(tmp_path: Path):
    """Identity state should use explicit confirmation marker file."""
    store = MemoryDocumentStore(str(tmp_path / "memory"))
    store.ensure_initialized()

    initial_state = store.read_identity_state()
    assert initial_state["identity_confirmed"] is None

    store.write_identity_state(True, "腿哥")
    state = store.read_identity_state()
    assert state["identity_confirmed"] is True
    assert state["display_name"] == "腿哥"
