"""One-pen persistence tests for the boot-time ResumptionSeeder."""
from __future__ import annotations

import json
import time

from substrate import Reader, Writer, connect
from theory_x.memory.resumption import ResumptionSeeder


def test_resumption_uses_injected_beliefs_and_probes_writers(tmp_path):
    beliefs_path = tmp_path / "beliefs.db"
    probes_path = tmp_path / "probes.db"
    snapshot_path = tmp_path / "state_snapshot.json"

    cx = connect(beliefs_path)
    cx.execute("CREATE TABLE beliefs (id INTEGER PRIMARY KEY, created_at INTEGER)")
    cx.executemany(
        "INSERT INTO beliefs VALUES (?, ?)",
        [(1, 100), (2, 200), (3, 300)],
    )
    cx.commit()
    cx.close()

    cx = connect(probes_path)
    cx.execute(
        "CREATE TABLE probes (id INTEGER PRIMARY KEY, asked_at REAL, notes TEXT, "
        "response_received_at REAL)"
    )
    cx.executemany(
        "INSERT INTO probes VALUES (?, ?, ?, ?)",
        [(10, 100.0, "first", None), (11, 200.0, "already answered", 250.0)],
    )
    cx.commit()
    cx.close()

    snapshot_path.write_text(json.dumps({
        "snapshot_ts": time.time(),
        "recent_belief_ids": [1, 2],
        "pending_probes": [{"id": 10}, {"id": 11}, {"missing": True}],
    }))

    b_writer = Writer(beliefs_path, name="resumption-test-beliefs")
    p_writer = Writer(probes_path, name="resumption-test-probes")
    try:
        seeder = ResumptionSeeder(
            str(beliefs_path), str(probes_path), str(snapshot_path),
            beliefs_writer=b_writer, probes_writer=p_writer,
        )
        result = seeder.run()
        assert result["executed"] is True
        assert result["promoted_count"] == 2
        assert result["probes_reissued"] == 2

        beliefs = Reader(beliefs_path)
        rows = beliefs.read("SELECT id, created_at FROM beliefs ORDER BY id")
        assert rows[0]["created_at"] == rows[1]["created_at"]
        assert int(time.time()) - 2 <= rows[0]["created_at"] <= int(time.time()) - 1
        assert rows[2]["created_at"] == 300

        probes = Reader(probes_path)
        first = probes.read_one("SELECT asked_at, notes FROM probes WHERE id=10")
        second = probes.read_one("SELECT asked_at, notes FROM probes WHERE id=11")
        assert "[reissued_after_restart]" in first["notes"]
        assert first["asked_at"] > 100.0
        assert second["asked_at"] == 200.0
        assert second["notes"] == "already answered"
        assert not snapshot_path.exists()
        assert snapshot_path.with_name("state_snapshot.json.consumed").exists()
    finally:
        b_writer.close()
        p_writer.close()
