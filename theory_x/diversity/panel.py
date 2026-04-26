"""DIVERSITY panel data preparation."""
from __future__ import annotations


def overview(beliefs_reader) -> dict:
    try:
        top_collisions = beliefs_reader.read(
            """SELECT g.grade, g.input_distance, g.output_distance, g.rarity,
                      b.content, g.graded_at
               FROM collision_grades g
               JOIN beliefs b ON g.belief_id = b.id
               ORDER BY g.grade DESC LIMIT 10"""
        )
    except Exception:
        top_collisions = []

    try:
        grooves = beliefs_reader.read(
            "SELECT * FROM groove_alerts "
            "WHERE acknowledged_at IS NULL "
            "ORDER BY detected_at DESC LIMIT 5"
        )
    except Exception:
        grooves = []

    try:
        dormant = beliefs_reader.read(
            """SELECT d.dormancy_score, b.content, d.last_active_at
               FROM dormant_beliefs d JOIN beliefs b ON d.belief_id = b.id
               WHERE d.reanimated_at IS NULL
               ORDER BY d.dormancy_score DESC LIMIT 10"""
        )
    except Exception:
        dormant = []

    try:
        weights = beliefs_reader.read(
            "SELECT * FROM grader_versions ORDER BY version DESC LIMIT 10"
        )
    except Exception:
        weights = []

    return {
        "top_collisions": [dict(c) for c in top_collisions],
        "groove_alerts": [dict(g) for g in grooves],
        "dormant": [dict(d) for d in dormant],
        "grader_versions": [dict(w) for w in weights],
    }
