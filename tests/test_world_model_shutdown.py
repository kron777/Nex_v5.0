"""World Model producer stop-boundary regressions."""
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from theory_x.stage3_world_model.harmonizer import Harmonizer
from theory_x.stage3_world_model.erosion import ProvenanceErosion
from theory_x.stage3_world_model.synergizer import Synergizer


def test_harmonizer_stops_between_heuristic_and_semantic_pair_scoring():
    stop = threading.Event()
    reader = MagicMock()
    reader.read.return_value = [
        {"id": 1, "content": "claim one", "tier": 5},
        {"id": 2, "content": "claim two", "tier": 5},
    ]
    harmonizer = Harmonizer(MagicMock(), reader, MagicMock(), MagicMock())

    def score_and_stop(*_args, **_kwargs):
        stop.set()
        return 0.2

    with patch("theory_x.stage3_world_model.harmonizer._conflict_score", side_effect=score_and_stop):
        with patch("theory_x.stage3_world_model.harmonizer._semantic_conflict_score") as semantic:
            result = harmonizer.scan_for_conflicts(stop_event=stop)

    assert result == []
    semantic.assert_not_called()


def test_erosion_finishes_current_update_and_undo_pair_then_stops():
    stop = threading.Event()
    reader = MagicMock()
    reader.read.return_value = [
        {"id": 1, "source": "external", "erosion_stage": "external", "reinforce_count": 10, "locked": 0},
        {"id": 2, "source": "external", "erosion_stage": "external", "reinforce_count": 10, "locked": 0},
    ]
    writer = MagicMock()

    def write_one(*_args, **_kwargs):
        stop.set()

    writer.write.side_effect = write_one
    erosion = ProvenanceErosion(writer, reader)

    advanced = erosion.erosion_pass(stop_event=stop)

    assert advanced == 1
    assert reader.read.call_count == 1
    assert writer.write.call_count == 2


def test_synergizer_discards_voice_result_if_stop_arrives_during_call():
    stop = threading.Event()
    writer = MagicMock()
    reader = MagicMock()
    voice = MagicMock()
    voice.speak.side_effect = lambda _req: (stop.set() or SimpleNamespace(text="A meaningful synthesis sentence."))
    synergizer = Synergizer(writer, reader, voice)
    synergizer._select_pair = lambda: (
        {"id": 1, "content": "A", "branch_id": "a"},
        {"id": 2, "content": "B", "branch_id": "b"},
    )

    result = synergizer.synthesize(stop_event=stop)

    assert result is None
    voice.speak.assert_called_once()
    writer.write.assert_not_called()


def test_world_consolidator_stops_between_embedding_calls():
    import os
    from theory_x.stage3_world_model.world_consolidation import WorldConsolidator

    stop = threading.Event()
    reader = MagicMock()
    reader.read.return_value = [
        {"id": i, "content": f"Global market activity continues across several independent sectors, report number {i}."}
        for i in range(1, 7)
    ]
    promoter = MagicMock()
    consolidator = WorldConsolidator(reader, promoter)

    def embed_and_stop(_content):
        stop.set()
        return [1.0, 0.0]

    with patch.dict(os.environ, {"NEX5_WORLD_CONSOLIDATE": "1"}):
        with patch("theory_x.diversity.embeddings.embed", side_effect=embed_and_stop):
            result = consolidator.tick(stop_event=stop)

    assert result["state"] == "stopped"
    promoter.corroborate.assert_not_called()
