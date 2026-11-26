"""Repository-boundary tests for scoped RDO reconciliation."""
from __future__ import annotations

import pytest

from rdo.reconcile import _grep


@pytest.mark.parametrize("target_kind", ["file", "directory"])
def test_scoped_reconciliation_refuses_symlinks_outside_repository(tmp_path, target_kind):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("needle outside the repository\n", encoding="utf-8")

    link = repo / "external"
    if target_kind == "file":
        link.symlink_to(secret)
    else:
        link.symlink_to(outside, target_is_directory=True)

    # None means the requested evidence scan is unavailable. It must not read
    # a path that merely looks repository-relative but resolves outside the tree.
    assert _grep("needle", str(repo), "external") is None


def test_scoped_reconciliation_allows_internal_symlink_targets(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    source = repo / "source.txt"
    source.write_text("needle inside the repository\n", encoding="utf-8")
    (repo / "alias.txt").symlink_to(source)

    result = _grep("needle", str(repo), "alias.txt")
    assert result
    assert result[0].startswith("alias.txt:")
