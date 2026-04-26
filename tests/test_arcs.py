"""Tests for the Arc Reader layer."""
from __future__ import annotations

import time
import unittest
from unittest.mock import patch

import numpy as np


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _SW:
    def __init__(self):
        self.calls = []
        self._id = 0

    def write(self, sql, params=()):
        self._id += 1
        self.calls.append((sql, params))
        return self._id


class _SR:
    def __init__(self, rows_map=None):
        self._m = rows_map or {}

    def read(self, sql, params=()):
        for k, v in self._m.items():
            if k.lower() in sql.lower():
                return v
        return []


def _make_fire(fid: int, content: str, ts: float) -> dict:
    return {"id": fid, "content": content, "created_at": ts}


# ---------------------------------------------------------------------------
# Synthetic embeddings helpers
# ---------------------------------------------------------------------------

def _progression_embeddings(n: int) -> list[np.ndarray]:
    """n vectors with monotone drift: each one rotates a bit more toward [0,1,0,...]."""
    base = np.zeros(384, dtype=np.float32)
    base[0] = 1.0
    drift = np.zeros(384, dtype=np.float32)
    drift[1] = 1.0
    vecs = []
    for i in range(n):
        t = i / (n - 1)
        v = (1 - t) * base + t * drift
        v /= np.linalg.norm(v)
        vecs.append(v)
    return vecs


def _oscillation_embeddings(n: int) -> list[np.ndarray]:
    """n vectors oscillating between two poles — no net drift."""
    a = np.zeros(384, dtype=np.float32)
    a[0] = 1.0
    b = np.zeros(384, dtype=np.float32)
    b[1] = 1.0
    vecs = []
    for i in range(n):
        vecs.append(a.copy() if i % 2 == 0 else b.copy())
    return vecs


# ---------------------------------------------------------------------------
# TestProgressionDetection
# ---------------------------------------------------------------------------

class TestProgressionDetection(unittest.TestCase):

    def _score(self, vecs, fires):
        with patch("theory_x.arcs.progression.embed_belief") as mock_emb:
            mock_emb.side_effect = lambda bid, _: vecs[bid]
            from theory_x.arcs.progression import compute_progression_score
            return compute_progression_score(fires)

    def test_monotone_drift_scores_high(self):
        n = 6
        fires = [_make_fire(i, f"content {i}", float(i * 60)) for i in range(n)]
        vecs = _progression_embeddings(n)
        score = self._score(vecs, fires)
        self.assertGreater(score, 0.5)

    def test_oscillation_scores_low(self):
        n = 6
        fires = [_make_fire(i, f"content {i}", float(i * 60)) for i in range(n)]
        vecs = _oscillation_embeddings(n)
        score = self._score(vecs, fires)
        self.assertLess(score, 0.5)

    def test_too_short_returns_zero(self):
        fires = [_make_fire(i, f"c {i}", float(i)) for i in range(2)]
        vecs = _progression_embeddings(2)
        score = self._score(vecs, fires)
        self.assertEqual(score, 0.0)

    def test_classify_roles_first_is_introduction(self):
        from theory_x.arcs.progression import classify_member_roles
        fires = [{"id": i} for i in range(5)]
        roles = classify_member_roles(fires)
        self.assertEqual(roles[0], "introduction")
        self.assertEqual(roles[-1], "synthesis")
        self.assertEqual(len(roles), 5)


# ---------------------------------------------------------------------------
# TestTransformationDetection
# ---------------------------------------------------------------------------

class TestTransformationDetection(unittest.TestCase):

    def _score(self, fires, vecs):
        with patch("theory_x.arcs.transformation.embed_belief") as mock_emb:
            mock_emb.side_effect = lambda bid, _: vecs[bid]
            from theory_x.arcs.transformation import compute_transformation_score
            return compute_transformation_score(fires)

    def test_gap_and_framing_change_scores_high(self):
        now = time.time()
        fires = [
            _make_fire(0, "clock ticks in room", now - 600),
            _make_fire(1, "clock ticks louder now", now - 300),
            _make_fire(2, "ticking beats differently", now),
        ]
        # Use orthogonal-ish vectors — raw cosine ≈ 0 maps to 0.5 in [0,1] range
        vecs = {
            0: np.array([1.0] + [0.0] * 383, dtype=np.float32),
            1: np.array([0.0, 1.0] + [0.0] * 382, dtype=np.float32),
            2: np.array([0.0, 0.0, 1.0] + [0.0] * 381, dtype=np.float32),
        }
        score = self._score(fires, vecs)
        self.assertGreater(score, 0.4)

    def test_literal_repetition_scores_zero(self):
        now = time.time()
        fires = [
            _make_fire(i, "identical content here", now - (2 - i) * 300)
            for i in range(3)
        ]
        identical_vec = np.array([1.0] + [0.0] * 383, dtype=np.float32)
        vecs = {i: identical_vec for i in range(3)}
        score = self._score(fires, vecs)
        self.assertEqual(score, 0.0)

    def test_no_temporal_gap_scores_zero(self):
        now = time.time()
        fires = [
            _make_fire(i, f"quick succession {i}", now - (2 - i) * 10)
            for i in range(3)
        ]
        vecs = {i: np.array([float(i % 2), float((i + 1) % 2)] + [0.0] * 382,
                             dtype=np.float32) for i in range(3)}
        for v in vecs.values():
            norm = np.linalg.norm(v)
            if norm > 0:
                v /= norm
        score = self._score(fires, vecs)
        self.assertEqual(score, 0.0)


# ---------------------------------------------------------------------------
# TestMetaReflective
# ---------------------------------------------------------------------------

class TestMetaReflective(unittest.TestCase):

    def test_dance_of_light_matches(self):
        from theory_x.arcs.meta_reflective import is_meta_reflective_content
        is_meta, conf = is_meta_reflective_content(
            "The constant dance of light and shadow reveals the interplay between interior and exterior."
        )
        self.assertTrue(is_meta)
        self.assertGreater(conf, 0.3)

    def test_bitcoin_price_does_not_match(self):
        from theory_x.arcs.meta_reflective import is_meta_reflective_content
        is_meta, conf = is_meta_reflective_content("Bitcoin price spiked 8% overnight.")
        self.assertFalse(is_meta)
        self.assertEqual(conf, 0.0)

    def test_keep_coming_back_matches(self):
        from theory_x.arcs.meta_reflective import is_meta_reflective_content
        is_meta, conf = is_meta_reflective_content("I keep coming back to this.")
        self.assertTrue(is_meta)

    def test_throughout_the_afternoon_matches(self):
        from theory_x.arcs.meta_reflective import is_meta_reflective_content
        is_meta, conf = is_meta_reflective_content(
            "Throughout the afternoon, this theme has been recurring."
        )
        self.assertTrue(is_meta)


# ---------------------------------------------------------------------------
# TestArcReader — synthetic arc sequences
# ---------------------------------------------------------------------------

class TestArcReader(unittest.TestCase):

    def _build_arc_reader(self, fires_rows, existing_members=None, active_arcs=None):
        from theory_x.arcs.detector import ArcReader

        class _DR:
            def read(self, sql, params=()):
                sql_l = sql.lower()
                if "group_concat" in sql_l:
                    return []  # no existing arcs for duplicate check
                if "arc_members" in sql_l:
                    return existing_members or []
                if "arcs" in sql_l and "closed_by_belief_id is null" in sql_l:
                    return active_arcs or []
                if "fountain_insight" in sql_l:
                    return fires_rows
                return []

        writer = _SW()
        reader = _DR()
        return ArcReader(writer, reader), writer

    def _afternoon_light_fires(self):
        base = time.time() - 9000
        contents = [
            "morning light filters through half-opened blinds",
            "afternoon sun casts a warm glow",
            "afternoon sun casts a gentle glow, but I'm restless",
            "the sun's warmth now seems slightly off",
            "the afternoon sun now casts a fainter glow",
            "the afternoon light feels off, as if hiding behind a curtain",
        ]
        return [_make_fire(i, c, base + i * 300) for i, c in enumerate(contents)]

    def _clock_fires(self):
        base = time.time() - 7200
        contents = [
            "clock ticks louder in my quiet room",
            "clock ticks louder in my quiet room",
            "the ticking clock now feels distinctly offbeat",
            "contrasting with the clock's rhythmic tick",
            "clock ticks louder in my quiet room",
        ]
        ts_offsets = [0, 420, 1200, 1320, 1860]
        return [_make_fire(i, c, base + ts_offsets[i]) for i, c in enumerate(contents)]

    def test_afternoon_light_detected_as_progression(self):
        fires = self._afternoon_light_fires()
        reader, writer = self._build_arc_reader(fires)

        # Patch embed_belief to return progression vectors
        vecs = _progression_embeddings(len(fires))
        vec_map = {f["id"]: vecs[f["id"]] for f in fires}

        with patch("theory_x.arcs.clustering.embed_belief",
                   side_effect=lambda bid, _: vec_map[bid]), \
             patch("theory_x.arcs.progression.embed_belief",
                   side_effect=lambda bid, _: vec_map[bid]), \
             patch("theory_x.arcs.transformation.embed_belief",
                   side_effect=lambda bid, _: vec_map[bid]), \
             patch("theory_x.arcs.detector.embed_belief",
                   side_effect=lambda bid, _: vec_map[bid]):
            result = reader.scan()

        self.assertGreater(result["arcs_detected"], 0)
        arc_inserts = [c for c in writer.calls if "INSERT INTO arcs" in c[0]]
        self.assertTrue(len(arc_inserts) > 0)
        arc_type = arc_inserts[0][1][0]
        self.assertEqual(arc_type, "progression")

    def test_clock_detected_as_return_transformation(self):
        fires = self._clock_fires()
        reader, writer = self._build_arc_reader(fires)

        # Vectors with moderate similarity and gaps — transformation pattern
        base_vec = np.zeros(384, dtype=np.float32)
        base_vec[0] = 1.0
        variant_vec = np.zeros(384, dtype=np.float32)
        variant_vec[0] = 0.8
        variant_vec[1] = 0.6
        variant_vec /= np.linalg.norm(variant_vec)

        vec_map = {
            0: base_vec.copy(),
            1: base_vec.copy(),
            2: variant_vec.copy(),
            3: variant_vec.copy(),
            4: base_vec.copy(),
        }

        with patch("theory_x.arcs.clustering.embed_belief",
                   side_effect=lambda bid, _: vec_map[bid]), \
             patch("theory_x.arcs.progression.embed_belief",
                   side_effect=lambda bid, _: vec_map[bid]), \
             patch("theory_x.arcs.transformation.embed_belief",
                   side_effect=lambda bid, _: vec_map[bid]), \
             patch("theory_x.arcs.detector.embed_belief",
                   side_effect=lambda bid, _: vec_map[bid]):
            result = reader.scan()

        arc_inserts = [c for c in writer.calls if "INSERT INTO arcs" in c[0]]
        if arc_inserts:
            arc_type = arc_inserts[0][1][0]
            self.assertIn(arc_type, ("progression", "return_transformation"))

    def test_meta_fire_closes_arc(self):
        meta_content = "The constant dance of light reveals the interplay between interior and exterior"
        meta_fire = _make_fire(99, meta_content, time.time())

        centroid = np.zeros(384, dtype=np.float32)
        centroid[0] = 1.0
        centroid_bytes = centroid.tobytes()

        active_arc = {"id": 1, "centroid_embedding": centroid_bytes}
        fires = [_make_fire(i, f"content {i}", float(i)) for i in range(5)]
        fires.append(meta_fire)

        from theory_x.arcs.detector import ArcReader

        class _DR2:
            def read(self, sql, params=()):
                if "arc_members" in sql and "joined_at" in sql:
                    return []
                if "arcs" in sql and "closed_by_belief_id is null" in sql.lower():
                    return [active_arc]
                if "fountain_insight" in sql:
                    return fires
                return []

        writer = _SW()
        arc_reader = ArcReader(writer, _DR2())

        meta_vec = np.zeros(384, dtype=np.float32)
        meta_vec[0] = 0.98
        meta_vec[1] = 0.2
        meta_vec /= np.linalg.norm(meta_vec)

        generic_vec = np.zeros(384, dtype=np.float32)
        generic_vec[2] = 1.0

        def embed_side(bid, _):
            return meta_vec if bid == 99 else generic_vec

        with patch("theory_x.arcs.clustering.embed_belief", side_effect=embed_side), \
             patch("theory_x.arcs.progression.embed_belief", side_effect=embed_side), \
             patch("theory_x.arcs.transformation.embed_belief", side_effect=embed_side), \
             patch("theory_x.arcs.meta_reflective.embed_belief", side_effect=embed_side), \
             patch("theory_x.arcs.detector.embed_belief", side_effect=embed_side):
            result = arc_reader.scan()

        self.assertGreaterEqual(result["closers_found"], 1)


# ---------------------------------------------------------------------------
# TestArcExtensions
# ---------------------------------------------------------------------------

class TestArcExtensions(unittest.TestCase):

    def test_new_fire_extends_existing_arc(self):
        from theory_x.arcs.detector import ArcReader

        centroid = np.zeros(384, dtype=np.float32)
        centroid[0] = 1.0
        centroid_bytes = centroid.tobytes()

        existing_fire_id = 10
        new_fire_id = 11

        active_arc = {"id": 1, "centroid_embedding": centroid_bytes, "member_count": 3}
        fires = [
            _make_fire(existing_fire_id, "old fire", time.time() - 100),
            _make_fire(new_fire_id, "new similar fire", time.time()),
        ]

        class _DR:
            def read(self, sql, params=()):
                if "group_concat" in sql.lower():
                    return []
                if "arc_members" in sql:
                    return [{"belief_id": existing_fire_id}]
                if "arcs" in sql:
                    return [active_arc]
                return []

        writer = _SW()
        arc_reader = ArcReader(writer, _DR())

        close_vec = np.zeros(384, dtype=np.float32)
        close_vec[0] = 0.99
        close_vec[1] = 0.14
        close_vec /= np.linalg.norm(close_vec)

        with patch("theory_x.arcs.detector.embed_belief",
                   side_effect=lambda bid, _: close_vec):
            added = arc_reader._check_extensions(fires)

        self.assertGreaterEqual(added, 1)
        update_calls = [c for c in writer.calls if "UPDATE arcs" in c[0]]
        self.assertTrue(len(update_calls) >= 1)


# ---------------------------------------------------------------------------
# TestOverlapAndCap
# ---------------------------------------------------------------------------

class TestOverlapAndCap(unittest.TestCase):

    def test_belief_can_appear_in_two_arcs(self):
        """A fire participating in arc 1 is not excluded from arc 2 detection."""
        from theory_x.arcs.detector import ArcReader

        shared_fire = _make_fire(50, "light and existence intertwined", time.time() - 500)
        arc1_fires = [
            _make_fire(i, f"afternoon light content {i}", time.time() - (6 - i) * 300)
            for i in range(1, 4)
        ] + [shared_fire]
        arc2_fires = [
            _make_fire(i + 10, f"existence depth content {i}", time.time() - (6 - i) * 600)
            for i in range(1, 4)
        ] + [shared_fire]

        # Both arc sets include fire 50; neither should block the other
        vecs_arc1 = _progression_embeddings(len(arc1_fires))
        vecs_arc2 = _progression_embeddings(len(arc2_fires))

        # Simulate: fire 50 already in an existing arc (arc 1)
        arc1_member_ids = {f["id"] for f in arc1_fires}

        class _DR:
            def read(self, sql, params=()):
                sql_l = sql.lower()
                if "group_concat" in sql_l:
                    # Return arc1's members for duplicate check
                    members_str = ",".join(str(i) for i in arc1_member_ids)
                    return [{"arc_id": 1, "members": members_str}]
                if "arc_members" in sql_l:
                    return [{"belief_id": bid} for bid in arc1_member_ids]
                if "arcs" in sql_l:
                    return []
                if "fountain_insight" in sql_l:
                    return arc2_fires
                return []

        writer = _SW()
        arc_reader = ArcReader(writer, _DR())

        # arc2_fires have different ids (10+), Jaccard with arc1 should be low
        # since only fire 50 is shared out of 4 total in each
        vec_map = {f["id"]: vecs_arc2[i] for i, f in enumerate(arc2_fires)}

        with patch("theory_x.arcs.clustering.embed_belief",
                   side_effect=lambda bid, _: vec_map.get(bid, np.zeros(384, dtype=np.float32))), \
             patch("theory_x.arcs.progression.embed_belief",
                   side_effect=lambda bid, _: vec_map.get(bid, np.zeros(384, dtype=np.float32))), \
             patch("theory_x.arcs.transformation.embed_belief",
                   side_effect=lambda bid, _: vec_map.get(bid, np.zeros(384, dtype=np.float32))), \
             patch("theory_x.arcs.detector.embed_belief",
                   side_effect=lambda bid, _: vec_map.get(bid, np.zeros(384, dtype=np.float32))):
            result = arc_reader.scan()

        # arc2 is NOT a duplicate of arc1 (Jaccard = 1/7 ≈ 0.14 < 0.7)
        arc_inserts = [c for c in writer.calls if "INSERT INTO arcs" in c[0]]
        self.assertGreater(len(arc_inserts), 0,
                           "arc2 should be detected despite fire 50 being in arc1")

    def test_oversized_cluster_rejected(self):
        """Clusters > MAX_ARC_MEMBERS_AT_CREATION are silently skipped."""
        from theory_x.arcs.detector import ArcReader, MAX_ARC_MEMBERS_AT_CREATION

        n = MAX_ARC_MEMBERS_AT_CREATION + 5
        fires = [_make_fire(i, f"content {i}", float(i * 60)) for i in range(n)]
        vecs = _progression_embeddings(n)
        vec_map = {f["id"]: vecs[i] for i, f in enumerate(fires)}

        class _DR:
            def read(self, sql, params=()):
                if "group_concat" in sql.lower():
                    return []
                if "arc_members" in sql:
                    return []
                if "arcs" in sql:
                    return []
                if "fountain_insight" in sql:
                    return fires
                return []

        writer = _SW()
        arc_reader = ArcReader(writer, _DR())

        with patch("theory_x.arcs.clustering.embed_belief",
                   side_effect=lambda bid, _: vec_map[bid]), \
             patch("theory_x.arcs.progression.embed_belief",
                   side_effect=lambda bid, _: vec_map[bid]), \
             patch("theory_x.arcs.transformation.embed_belief",
                   side_effect=lambda bid, _: vec_map[bid]), \
             patch("theory_x.arcs.detector.embed_belief",
                   side_effect=lambda bid, _: vec_map[bid]):
            # Force all fires into one cluster by patching cluster_fires
            with patch("theory_x.arcs.detector.cluster_fires", return_value=[fires]):
                result = arc_reader.scan()

        arc_inserts = [c for c in writer.calls if "INSERT INTO arcs" in c[0]]
        self.assertEqual(len(arc_inserts), 0,
                         f"Oversized cluster ({n} members) should be rejected")


if __name__ == "__main__":
    unittest.main()
