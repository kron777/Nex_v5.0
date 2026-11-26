"""Forward-consistency guard for the nex_config feature-flag registry.

`nex_config.KNOWN_FLAGS` is the authoritative registry of NEX5_* flags; its
`unknown_flags()` reports any NEX5_* env var NOT in the registry as "almost always
a typo that is silently doing nothing". That protection has a blind spot: if the
CODE reads a NEX5_ flag that was never ADDED to the registry, a real flag a user
sets would be silently mis-reported as a typo. This guard closes that blind spot:
every NEX5_ flag read in NEX source must be registered.

Reconciled at creation: 167 registered, 151 literal reads in source, 0
read-but-unregistered — the invariant holds, so this is a proactive guard (no
production change). Scope: NEX source .py only (tests/ set arbitrary flags for
their own fixtures; watcher/ and rdo/ are external instruments that do not read NEX
flags). It covers literal env reads (environ.get / getenv / environ[...]); a flag
read via a dynamically constructed name is out of scope by design.
"""
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import nex_config

# literal reads of a NEX5_ flag from the environment (the common access forms)
_READ_RE = re.compile(r'(?:environ\.get|getenv|environ\[)\(?\s*[\'"](NEX5_[A-Z0-9_]+)[\'"]')
# scope exclusions: test fixtures set arbitrary flags; watcher/rdo are external
_EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "node_modules", "tests", "watcher", "rdo"}


def _read_flags(root: str) -> dict:
    """Map each NEX5_ flag literally read from the environment under `root` to a
    file that reads it. Prunes the excluded directories."""
    found: dict = {}
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in _EXCLUDE_DIRS]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(d, f)
            try:
                text = open(path, encoding="utf-8").read()
            except Exception:
                continue
            for m in _READ_RE.finditer(text):
                found.setdefault(m.group(1), os.path.relpath(path, root))
    return found


class TestFlagRegistryConsistency(unittest.TestCase):
    def test_every_read_flag_is_registered(self):
        """The invariant: every NEX5_ flag read in NEX source is in KNOWN_FLAGS."""
        root = str(Path(__file__).resolve().parent.parent)
        reads = _read_flags(root)
        self.assertTrue(reads, "scanner found no NEX5_ reads — guard would be vacuous")
        unregistered = sorted(k for k in reads if k not in nex_config.KNOWN_FLAGS)
        self.assertEqual(
            unregistered, [],
            "NEX5_ flags read in source but missing from nex_config.KNOWN_FLAGS "
            "(register them, or unknown_flags() will mis-flag them as typos): "
            + ", ".join(f"{k} <- {reads[k]}" for k in unregistered))

    def test_guard_catches_an_unregistered_read(self):
        """Non-vacuous: the scanner detects an unregistered read, so the guard would
        FAIL if such a read were added to source."""
        tmp = tempfile.mkdtemp(prefix="nex5_flagscan_")
        try:
            with open(os.path.join(tmp, "mod.py"), "w", encoding="utf-8") as fh:
                fh.write('import os\nx = os.environ.get("NEX5_DEFINITELY_NOT_REGISTERED_XYZ")\n')
            reads = _read_flags(tmp)
            self.assertIn("NEX5_DEFINITELY_NOT_REGISTERED_XYZ", reads)
            self.assertNotIn("NEX5_DEFINITELY_NOT_REGISTERED_XYZ", nex_config.KNOWN_FLAGS)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_scanner_finds_a_known_read(self):
        """Sanity: the scanner recognises a registered literal read."""
        tmp = tempfile.mkdtemp(prefix="nex5_flagscan_")
        try:
            any_known = next(iter(nex_config.KNOWN_FLAGS))
            with open(os.path.join(tmp, "m.py"), "w", encoding="utf-8") as fh:
                fh.write(f'import os\nos.environ.get("{any_known}")\n')
            self.assertIn(any_known, _read_flags(tmp))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
