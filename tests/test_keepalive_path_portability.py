from __future__ import annotations

from pathlib import Path
import subprocess


def test_keepalive_resolves_checkout_from_its_own_location(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    source = (repo / "nex_keepalive.sh").read_text(encoding="utf-8")

    # Execute only the real path-resolution preamble from a copied script,
    # with a different working directory. Nothing after LOCKFILE is run.
    preamble = source.split("LOCKFILE=", 1)[0]
    probe_dir = tmp_path / "mounted-volume" / "nex5"
    probe_dir.mkdir(parents=True)
    probe = probe_dir / "nex_keepalive.sh"
    probe.write_text(
        preamble + '\nprintf "resolved=%s\\n" "$SCRIPT_DIR"\\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", str(probe)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"resolved={probe_dir.resolve()}"


def test_keepalive_has_no_host_specific_checkout_path():
    repo = Path(__file__).resolve().parents[1]
    source = (repo / "nex_keepalive.sh").read_text(encoding="utf-8")

    assert "/home/rr/Desktop/Desktop/nex5" not in source
    assert 'dirname -- "${BASH_SOURCE[0]}"' in source
    assert 'cd -- "${SCRIPT_DIR}"' in source

    result = subprocess.run(
        ["bash", "-n", str(repo / "nex_keepalive.sh")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
