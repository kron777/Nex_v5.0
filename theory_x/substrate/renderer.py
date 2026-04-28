"""
Substrate renderer — graph-native parallel fountain output.
No LLM. No prompt assembly. Templates only.
"""
import math
import time
import sqlite3
from typing import Optional

HALFLIFE_SECONDS = 1800
MIN_ARC_MEMBERS = 15
SYNERGY_LOOKBACK_SECONDS = 86400  # 24h

TEMPLATE_MAIN = """\
Most active right now: "{content}" (touched {touches:.0f}x, last {age_min:.0f} min ago)"""

TEMPLATE_CONNECTED_HEADER = "\nConnected:"
TEMPLATE_CONNECTED_EDGE   = '  - {edge_type}: "{content}"'

TEMPLATE_SYNERGY = """\
\nRecent synergy:
  "{anchor}" x "{fresh}"
  -> produced: "{result}" """

TEMPLATE_ARC_HEADER = "\nOpen arcs above 15 members:"
TEMPLATE_ARC_LINE   = "  - {theme} ({member_count} fires, {arc_type})"

TEMPLATE_QUIET = "Substrate is quiet. No belief activated above baseline in the last 30 min."


def render_substrate_fire(
    beliefs_conn: sqlite3.Connection,
    dynamic_conn: sqlite3.Connection,
) -> str:
    now = time.time()

    # -- 1. Top-activated belief ----------------------------------------------
    row = beliefs_conn.execute("""
        SELECT ba.belief_id,
               ba.activation * EXP(-(? - ba.last_touched_at) / ?) AS eff_activation,
               ba.last_touched_at,
               b.content
        FROM belief_activation ba
        JOIN beliefs b ON ba.belief_id = b.id
        WHERE ba.activation * EXP(-(? - ba.last_touched_at) / ?) > 0.01
        ORDER BY eff_activation DESC
        LIMIT 1
    """, (now, HALFLIFE_SECONDS, now, HALFLIFE_SECONDS)).fetchone()

    if not row:
        return TEMPLATE_QUIET

    top_id       = row[0]
    eff_act      = row[1]
    last_touched = row[2]
    top_content  = row[3]
    age_min      = (now - last_touched) / 60.0

    parts = [TEMPLATE_MAIN.format(
        content=top_content,
        touches=eff_act,
        age_min=age_min,
    )]

    # -- 2. Connected beliefs via belief_edges --------------------------------
    edges = beliefs_conn.execute("""
        SELECT be.edge_type, b.content
        FROM belief_edges be
        JOIN beliefs b ON be.target_id = b.id
        WHERE be.source_id = ?
        ORDER BY be.weight DESC
        LIMIT 3
    """, (top_id,)).fetchall()

    if edges:
        parts.append(TEMPLATE_CONNECTED_HEADER)
        for edge_type, content in edges:
            parts.append(TEMPLATE_CONNECTED_EDGE.format(
                edge_type=edge_type, content=content
            ))

    # -- 3. Most recent synergizer pair (last 24h) ----------------------------
    syn = beliefs_conn.execute("""
        SELECT sl.belief_id_a, sl.belief_id_b, sl.result_content
        FROM synergizer_log sl
        WHERE sl.ts > ? AND sl.result_content IS NOT NULL
        ORDER BY sl.ts DESC
        LIMIT 1
    """, (now - SYNERGY_LOOKBACK_SECONDS,)).fetchone()

    if syn:
        b_a = beliefs_conn.execute(
            "SELECT content FROM beliefs WHERE id = ?", (syn[0],)
        ).fetchone()
        b_b = beliefs_conn.execute(
            "SELECT content FROM beliefs WHERE id = ?", (syn[1],)
        ).fetchone()
        if b_a and b_b and syn[2]:
            parts.append(TEMPLATE_SYNERGY.format(
                anchor=b_a[0], fresh=b_b[0], result=syn[2]
            ))

    # -- 4. Active arcs above member threshold --------------------------------
    arcs = beliefs_conn.execute("""
        SELECT theme_summary, member_count, arc_type
        FROM arcs
        WHERE member_count >= ?
        ORDER BY member_count DESC
        LIMIT 5
    """, (MIN_ARC_MEMBERS,)).fetchall()

    if arcs:
        parts.append(TEMPLATE_ARC_HEADER)
        for theme, member_count, arc_type in arcs:
            parts.append(TEMPLATE_ARC_LINE.format(
                theme=theme or "(no theme)",
                member_count=member_count,
                arc_type=arc_type,
            ))

    return "\n".join(parts)
