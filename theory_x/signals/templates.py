"""Pattern templates — known signal shapes with prediction windows."""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class Template:
    name: str
    description: str
    predicted_window_seconds: int
    min_signals: int
    required_detectors: list
    prediction_text: str


TEMPLATES = {
    "triple_cooccurrence": Template(
        name="triple_cooccurrence",
        description="Same entity appears across 2+ branches — cross-domain convergence",
        predicted_window_seconds=86400,  # 24h
        min_signals=1,
        required_detectors=["co_occurrence"],
        prediction_text=(
            "Entity '{entity}' has appeared across {branch_count} "
            "branches ({branches}). Cross-domain convergence often "
            "precedes significant developments in that entity."
        ),
    ),
    "branch_silence_anomaly": Template(
        name="branch_silence_anomaly",
        description="Normally active stream has gone unusually quiet",
        predicted_window_seconds=14400,  # 4h
        min_signals=1,
        required_detectors=["silence"],
        prediction_text=(
            "Stream '{stream}' has been silent for "
            "{silence_seconds:.0f}s (normally every {avg_gap:.0f}s). "
            "Silence in active feeds often precedes activity."
        ),
    ),
    "pattern_recognition_burst": Template(
        name="pattern_recognition_burst",
        description="Multiple high-tier beliefs formed rapidly — heightened cognitive activity",
        predicted_window_seconds=3600,  # 1h
        min_signals=1,
        required_detectors=["burst"],
        prediction_text=(
            "{promotions} beliefs reached T6 in the last "
            "{window_minutes:.0f} minutes across {branch_count} branches. "
            "Burst activity often clusters around emerging themes."
        ),
    ),
}


class PatternTemplateLibrary:
    """Matches clusters of signals against known templates."""

    def __init__(self, writer=None, reader=None):
        self._writer = writer
        self._reader = reader

    def match(self, signal_rows: list) -> list[dict]:
        """
        Given recent signals (dicts with id, detector_name, payload keys),
        return template matches as pattern record dicts.
        """
        by_detector: dict[str, list] = {}
        for s in signal_rows:
            by_detector.setdefault(s["detector_name"], []).append(s)

        matches = []
        for tname, template in TEMPLATES.items():
            if not all(d in by_detector for d in template.required_detectors):
                continue

            matched_ids = []
            for d in template.required_detectors:
                for sig in by_detector[d]:
                    matched_ids.append(sig["id"])

            if len(matched_ids) < template.min_signals:
                continue

            try:
                primary = by_detector[template.required_detectors[0]][0]
                payload = json.loads(primary["payload"])

                if tname == "triple_cooccurrence":
                    prediction = template.prediction_text.format(
                        entity=payload.get("entity", "?"),
                        branch_count=len(payload.get("branches", [])),
                        branches=", ".join(payload.get("branches", [])),
                    )
                elif tname == "branch_silence_anomaly":
                    prediction = template.prediction_text.format(
                        stream=payload.get("stream", "?"),
                        silence_seconds=payload.get("current_silence_seconds", 0),
                        avg_gap=payload.get("avg_gap_seconds", 0),
                    )
                elif tname == "pattern_recognition_burst":
                    prediction = template.prediction_text.format(
                        promotions=payload.get("promotions", 0),
                        window_minutes=payload.get("window_seconds", 900) / 60,
                        branch_count=len(payload.get("branches", [])),
                    )
                else:
                    prediction = template.description
            except Exception:
                prediction = template.description

            matches.append({
                "template_name": tname,
                "signal_ids": matched_ids,
                "predicted_window_seconds": template.predicted_window_seconds,
                "prediction": prediction,
            })

        return matches
