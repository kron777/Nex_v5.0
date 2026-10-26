"""NEX5_IDENTITY_BLOCK — the guaranteed identity block, observed in the real prompt.

Behavioural, not "the flag flips": each test builds actual fountain prompts from
an initialised store and checks what she would read. Today a seeded identity
claim reaches roughly 1 fire in 10 (seed sampling + affinity draws); with the
block on it must reach every fire, and affinity must change only how much.
"""
import json
import os
import time
import unittest

from tests.test_retrieval import _cleanup, _make_env, _make_generator
from theory_x.stage6_fountain import identity_block

_CLAIMS = [f"I am standing claim {i}, authored for me" for i in range(5)]
_FIRES = 25


class TestIdentityBlock(unittest.TestCase):

    def setUp(self):
        self.writers, self.readers, self.tmp = _make_env()
        self.gen = _make_generator(self.writers, self.readers)
        os.environ.pop("NEX5_IDENTITY_BLOCK", None)

    def tearDown(self):
        os.environ.pop("NEX5_IDENTITY_BLOCK", None)
        _cleanup(self.writers, self.tmp)

    def _insert(self, content, source, affinity=None):
        self.writers["beliefs"].write(
            "INSERT INTO beliefs (content, tier, confidence, created_at, source, "
            "branch_id, locked, affinity) VALUES (?, 1, 1.0, ?, ?, 'systems', 1, ?)",
            (content, time.time(), source, affinity))

    def _seed_claims(self, affinity=None):
        for c in _CLAIMS:
            self._insert(c, "identity", affinity)
        time.sleep(0.2)  # let the writer thread commit

    def _block_lines(self, prompt):
        """The belief lines under the block header, or None if no block."""
        lines = prompt.splitlines()
        if identity_block.HEADER not in lines:
            return None
        out = []
        for ln in lines[lines.index(identity_block.HEADER) + 1:]:
            if not ln.strip():
                break
            out.append(ln.strip()[2:])
        return out

    def _fires(self, n=_FIRES):
        return [self.gen._build_prompt({}, 10, {}) for _ in range(n)]

    def test_off_by_default_no_block_in_any_prompt(self):
        self._seed_claims()
        for prompt, manifest in self._fires():
            self.assertNotIn(identity_block.HEADER, prompt)
            self.assertFalse([m for m in manifest if m[1] == identity_block.SLOT])

    def test_on_every_fire_carries_a_standing_claim(self):
        # Fresh-store shape: affinity unrated, identity_log empty. Without the
        # block, nothing guarantees she meets her self-model on any given fire.
        self._seed_claims()
        os.environ["NEX5_IDENTITY_BLOCK"] = "1"
        for prompt, manifest in self._fires():
            lines = self._block_lines(prompt)
            self.assertIsNotNone(lines, "a fire assembled without the identity block")
            self.assertEqual(len(lines), 1)            # floor only: nothing rated yet
            self.assertIn(lines[0], _CLAIMS)
            self.assertEqual(
                len([m for m in manifest if m[1] == identity_block.SLOT]), 1)

    def test_affinity_governs_how_much_not_whether(self):
        os.environ["NEX5_IDENTITY_BLOCK"] = "1"
        self._seed_claims(affinity=0.10)              # below threshold: floor only
        for prompt, _ in self._fires(5):
            self.assertEqual(len(self._block_lines(prompt)), 1)
        self.writers["beliefs"].write(
            "UPDATE beliefs SET affinity=0.9 WHERE source='identity'", ())
        time.sleep(0.2)
        for prompt, _ in self._fires(5):
            lines = self._block_lines(prompt)
            self.assertEqual(len(lines), 3)           # floor + default max 2 extras
            self.assertEqual(len(set(lines)), 3)      # the floor is never repeated
            self.assertTrue(set(lines) <= set(_CLAIMS))

    def test_falls_back_to_self_location_when_no_authored_claims(self):
        os.environ["NEX5_IDENTITY_BLOCK"] = "1"
        self._insert("I am inside. I have a vantage point.", "self_location")
        time.sleep(0.2)
        prompt, _ = self.gen._build_prompt({}, 10, {})
        self.assertEqual(self._block_lines(prompt),
                         ["I am inside. I have a vantage point."])

    def test_defers_to_identity_ablation_treatment_arm(self):
        # Arms B/C of the self-as-cause experiment remove the identity claim;
        # the block must not put one back, or A-vs-B is confounded.
        from substrate.paths import data_dir
        self._seed_claims()
        os.environ["NEX5_IDENTITY_BLOCK"] = "1"
        cond = data_dir() / "identity_ablation.json"
        cond.write_text(json.dumps({"mode": "reframe"}))
        try:
            for prompt, _ in self._fires(5):
                self.assertNotIn(identity_block.HEADER, prompt)
        finally:
            cond.write_text(json.dumps({"mode": "normal"}))
            os.utime(cond, (time.time() + 5, time.time() + 5))  # bust mtime cache
        prompt, _ = self.gen._build_prompt({}, 10, {})
        self.assertIsNotNone(self._block_lines(prompt))


if __name__ == "__main__":
    unittest.main()
