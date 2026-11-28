"""mind_map anchor drift: a cited line range must still hold the lines it held
when the anchor was written.

STALE compares a file's last commit date with last_verified at day granularity,
so an edit later on the same day -- or a branch merged after the anchor was set
-- shifts cited lines without any warning. 2026-11-28 had three such shifts
(nex_keepalive.sh via 14873c10, gui/server.py via G-84 steps 3-4). The drift
check blames the YAML line that holds each quoted ref, reads the cited range at
that commit, and compares it with the working tree. Fixtures run in a throwaway
git repository; nothing here touches the real map.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mind_map import mind_map

_SRC = "\n".join(f"line {i}" for i in range(1, 11)) + "\n"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
                        "HOME": str(root), "PATH": "/usr/bin:/bin:/usr/local/bin"})


def _map(ref: str) -> str:
    return ("nodes:\n"
            "  - id: probe\n"
            "    source:\n"
            "      kind: composite\n"
            "      refs:\n"
            f"        - \"{ref}\"\n")


@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text(_SRC)
    (tmp_path / "MAP.yaml").write_text(_map("pkg/mod.py:3-4"))
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "anchor")
    return tmp_path


def _drift(root):
    return mind_map.anchor_drift_warnings(root / "MAP.yaml", root)


def test_unchanged_source_is_quiet(repo):
    assert _drift(repo) == []


def test_lines_inserted_above_are_reported_with_the_new_position(repo):
    (repo / "pkg" / "mod.py").write_text("new\nnew\n" + _SRC)
    _git(repo, "commit", "-qam", "insert two lines above the cited range")
    [warning] = _drift(repo)
    assert "probe: DRIFT" in warning
    assert "pkg/mod.py:3-4" in warning
    assert "now at :5-6" in warning


def test_ambiguous_duplicate_matches_are_not_automatically_reanchored(repo):
    (repo / "pkg" / "mod.py").write_text(
        "new\nnew\n" + _SRC + "line 3\nline 4\n"
    )
    _git(repo, "commit", "-qam", "shift and duplicate the cited block")

    [warning] = _drift(repo)
    assert "ambiguous duplicate matches" in warning

    applied, review = mind_map.reanchor(repo / "MAP.yaml", repo)
    assert applied == []
    assert len(review) == 1
    assert "multiple identical destinations" in review[0]
    assert '"pkg/mod.py:3-4"' in (repo / "MAP.yaml").read_text()


def test_an_edit_inside_the_range_is_reported_as_changed(repo):
    (repo / "pkg" / "mod.py").write_text(_SRC.replace("line 3", "line three"))
    _git(repo, "commit", "-qam", "edit a cited line")
    [warning] = _drift(repo)
    assert "content changed or removed" in warning


def test_re_anchoring_in_a_later_commit_clears_the_warning(repo):
    (repo / "pkg" / "mod.py").write_text("new\nnew\n" + _SRC)
    _git(repo, "commit", "-qam", "shift")
    (repo / "MAP.yaml").write_text(_map("pkg/mod.py:5-6"))
    _git(repo, "commit", "-qam", "re-anchor")
    assert _drift(repo) == []


def test_uncommitted_working_tree_shift_is_reported(repo):
    (repo / "pkg" / "mod.py").write_text("new\n" + _SRC)      # not committed
    [warning] = _drift(repo)
    assert "now at :4-5" in warning


def test_an_uncommitted_anchor_is_not_judged(repo):
    (repo / "MAP.yaml").write_text(_map("pkg/mod.py:7-8"))   # being edited now
    assert _drift(repo) == []


def test_edits_outside_the_cited_range_are_quiet(repo):
    (repo / "pkg" / "mod.py").write_text(_SRC + "appended\n")
    _git(repo, "commit", "-qam", "append below")
    assert _drift(repo) == []


def test_refs_in_inline_lists_and_single_ref_form_are_checked(repo):
    (repo / "MAP.yaml").write_text(
        "nodes:\n"
        "  - id: a\n"
        '    source: { kind: composite, refs: ["pkg/mod.py:2", "pkg/mod.py:9-10"] }\n'
        "  - id: b\n"
        '    source: { kind: file, ref: "pkg/mod.py:5" }\n')
    _git(repo, "commit", "-qam", "more refs")
    (repo / "pkg" / "mod.py").write_text("x\n" + _SRC)
    _git(repo, "commit", "-qam", "shift by one")
    warnings = _drift(repo)
    assert len(warnings) == 3
    assert {w.split(":")[0] for w in warnings} == {"a", "b"}


def _map_verified(ref: str, verified: str) -> str:
    return ("nodes:\n"
            "  - id: probe\n"
            "    source:\n"
            "      kind: composite\n"
            "      refs:\n"
            f"        - \"{ref}\"\n"
            f"    last_verified: {verified}\n"
            "findings:\n"
            "  - id: not_a_node\n")


def test_a_later_re_verification_resets_the_baseline(repo):
    (repo / "MAP.yaml").write_text(_map_verified("pkg/mod.py:3-4", "2026-11-27"))
    _git(repo, "commit", "-qam", "dated")
    (repo / "pkg" / "mod.py").write_text(_SRC.replace("line 3", "line three"))
    _git(repo, "commit", "-qam", "edit inside the range")
    assert len(_drift(repo)) == 1
    # Someone re-reads the edited lines, keeps the anchor and re-dates the node.
    (repo / "MAP.yaml").write_text(_map_verified("pkg/mod.py:3-4", "2026-11-28"))
    _git(repo, "commit", "-qam", "re-verified")
    assert _drift(repo) == []


def test_reanchor_moves_only_pure_shifts_and_reports_edits(repo):
    (repo / "MAP.yaml").write_text(
        "nodes:\n"
        "  - id: a\n"
        '    source: { kind: composite, refs: ["pkg/mod.py:3-4", "pkg/mod.py:8"] }\n'
        "    last_verified: 2026-11-27\n")
    _git(repo, "commit", "-qam", "two refs")
    (repo / "pkg" / "mod.py").write_text(
        "new\n" + _SRC.replace("line 8", "line eight"))
    _git(repo, "commit", "-qam", "shift one ref, edit the other")
    applied, review = mind_map.reanchor(repo / "MAP.yaml", repo)
    assert applied == ['a: "pkg/mod.py:3-4" -> "pkg/mod.py:4-5"']
    assert len(review) == 1 and "pkg/mod.py:8 content changed" in review[0]
    text = (repo / "MAP.yaml").read_text()
    assert '"pkg/mod.py:4-5"' in text and '"pkg/mod.py:8"' in text
    assert "last_verified: 2026-11-27" in text          # dates are never touched
    _git(repo, "commit", "-qam", "reanchored")
    assert [w for w in _drift(repo) if "4-5" in w] == []


def test_quoted_code_pointers_in_notes_are_not_treated_as_source_anchors(repo):
    (repo / "MAP.yaml").write_text(
        "nodes:\n"
        "  - id: probe\n"
        "    source:\n"
        "      kind: composite\n"
        "      refs:\n"
        '        - "pkg/mod.py:3-4"\n'
        "    notes: >\n"
        '      This prose mentions "pkg/mod.py:3-4" but is not an anchor.\n'
        "  - id: second\n"
        "    notes: >\n"
        '      This second node also mentions "pkg/mod.py:3-4" as prose.\n'
    )
    _git(repo, "commit", "-qam", "add prose pointer")
    (repo / "pkg" / "mod.py").write_text("new\n" + _SRC)
    _git(repo, "commit", "-qam", "shift the real source anchor")

    warnings = _drift(repo)
    assert len(warnings) == 1
    assert "pkg/mod.py:3-4" in warnings[0]
    applied, review = mind_map.reanchor(repo / "MAP.yaml", repo)
    assert applied == ['probe: "pkg/mod.py:3-4" -> "pkg/mod.py:4-5"']
    assert review == []
    content = (repo / "MAP.yaml").read_text()
    assert '        - "pkg/mod.py:4-5"' in content
    assert 'This prose mentions "pkg/mod.py:3-4"' in content


def test_findings_ids_are_not_mistaken_for_nodes(repo):def test_findings_ids_are_not_mistaken_for_nodes(repo):
    (repo / "MAP.yaml").write_text(_map_verified("pkg/mod.py:3-4", "2026-11-27"))
    _git(repo, "commit", "-qam", "dated")
    (repo / "pkg" / "mod.py").write_text("x\n" + _SRC)
    _git(repo, "commit", "-qam", "shift")
    [warning] = _drift(repo)
    assert warning.startswith("probe: DRIFT")
