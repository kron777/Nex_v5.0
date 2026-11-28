"""Durability guarantees for first objective revision creation."""
import os
import stat

from rdo_adapters.objective_intake import ObjectiveInputStore


def _objective():
    return {
        "schema_version": "rdo.objective.v1",
        "objective_id": "durability-check",
        "revision": 1,
        "supersedes_sha256": None,
        "original_text": "Preserve the first objective revision durably.",
        "intent": "Verify the objective ledger's first-create durability.",
        "owner": "test",
        "source": {"kind": "human", "reference": "test:durability"},
        "scope": {"in_scope": ["objective intake"], "affected_paths": []},
        "constraints": [],
        "exclusions": [],
        "assumptions": [],
        "acceptance_criteria": ["The first revision survives directory-entry loss."],
        "seed_obligations": [{
            "key": "objective.durability",
            "title": "Durable first revision",
            "kind": "persistence",
            "classification": "necessary",
            "rationale": "The objective revision is the durable source record.",
            "impact": "A lost directory entry would lose the first accepted revision.",
            "evidence_needs": ["Verify file and parent-directory fsync ordering."],
            "assumptions": [],
            "confidence": "stated",
        }],
        "relationships": [],
        "reconciliation_signatures": {},
        "max_depth": 0,
    }


def test_first_objective_revision_fsyncs_file_then_parent_directory(tmp_path, monkeypatch):
    real_fsync = os.fsync
    synced_directory_flags = []

    def recording_fsync(fd):
        synced_directory_flags.append(stat.S_ISDIR(os.fstat(fd).st_mode))
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", recording_fsync)
    store = ObjectiveInputStore(str(tmp_path / "objectives"))
    store.append(_objective())

    assert synced_directory_flags == [False, True]


def test_later_objective_revision_does_not_repeat_directory_creation_fsync(tmp_path, monkeypatch):
    real_fsync = os.fsync
    synced_directory_flags = []

    def recording_fsync(fd):
        synced_directory_flags.append(stat.S_ISDIR(os.fstat(fd).st_mode))
        return real_fsync(fd)

    monkeypatch.setattr(os, "fsync", recording_fsync)
    store = ObjectiveInputStore(str(tmp_path / "objectives"))
    first = store.append(_objective())
    assert synced_directory_flags == [False, True]

    synced_directory_flags.clear()
    second = _objective()
    second["revision"] = 2
    second["supersedes_sha256"] = first["sha256"]
    store.append(second)

    assert synced_directory_flags == [False]
