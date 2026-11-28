"""Symlink and special-file rejection for objective revision storage."""
import pytest

from rdo_adapters.objective_intake import ObjectiveInputError, ObjectiveInputStore


def _objective():
    return {
        "schema_version": "rdo.objective.v1",
        "objective_id": "path-safety",
        "revision": 1,
        "supersedes_sha256": None,
        "original_text": "Reject symlinked objective storage paths.",
        "intent": "Keep objective revision storage inside its configured directory.",
        "owner": "test",
        "source": {"kind": "human", "reference": "test:path-safety"},
        "scope": {"in_scope": ["objective intake"], "affected_paths": []},
        "constraints": [],
        "exclusions": [],
        "assumptions": [],
        "acceptance_criteria": ["Symlinked ledger and lock paths are rejected."],
        "seed_obligations": [{
            "key": "objective.path_safety",
            "title": "Safe objective storage paths",
            "kind": "persistence",
            "classification": "necessary",
            "rationale": "A symlink must not redirect the append-only ledger.",
            "impact": "A redirected ledger could overwrite or disclose unrelated files.",
            "evidence_needs": ["Verify ledger and lock paths are regular non-symlink files."],
            "assumptions": [],
            "confidence": "stated",
        }],
        "relationships": [],
        "reconciliation_signatures": {},
        "max_depth": 0,
    }


def test_dangling_objective_ledger_symlink_is_not_treated_as_empty(tmp_path):
    directory = tmp_path / "objectives"
    store = ObjectiveInputStore(str(directory))
    ledger = directory / "path-safety.jsonl"
    target = tmp_path / "missing-target.jsonl"
    ledger.symlink_to(target)

    with pytest.raises(ObjectiveInputError, match="ledger path must not be a symlink"):
        store.history("path-safety")
    with pytest.raises(ObjectiveInputError, match="ledger path must not be a symlink"):
        store.append(_objective())
    assert not target.exists()


def test_existing_objective_ledger_symlink_is_rejected_without_target_write(tmp_path):
    directory = tmp_path / "objectives"
    store = ObjectiveInputStore(str(directory))
    ledger = directory / "path-safety.jsonl"
    target = tmp_path / "outside.jsonl"
    target.write_text("untouched\n", encoding="utf-8")
    ledger.symlink_to(target)

    with pytest.raises(ObjectiveInputError, match="ledger path must not be a symlink"):
        store.history("path-safety")
    with pytest.raises(ObjectiveInputError, match="ledger path must not be a symlink"):
        store.append(_objective())
    assert target.read_text(encoding="utf-8") == "untouched\n"


def test_objective_lock_symlink_is_rejected_for_history_and_append(tmp_path):
    directory = tmp_path / "objectives"
    store = ObjectiveInputStore(str(directory))
    first = store.append(_objective())
    lock_path = directory / "path-safety.jsonl.lock"
    lock_path.unlink()
    target = tmp_path / "outside.lock"
    target.write_text("untouched lock\n", encoding="utf-8")
    lock_path.symlink_to(target)

    with pytest.raises(ObjectiveInputError, match="lock path must not be a symlink"):
        store.history("path-safety")
    second = _objective()
    second["revision"] = 2
    second["supersedes_sha256"] = first["sha256"]
    with pytest.raises(ObjectiveInputError, match="lock path must not be a symlink"):
        store.append(second)
    assert target.read_text(encoding="utf-8") == "untouched lock\n"


def test_objective_ledger_fifo_is_rejected_without_blocking(tmp_path):
    import os

    directory = tmp_path / "objectives"
    store = ObjectiveInputStore(str(directory))
    fifo = directory / "path-safety.jsonl"
    os.mkfifo(fifo)

    with pytest.raises(ObjectiveInputError, match="ledger path must be a regular file"):
        store.history("path-safety")
