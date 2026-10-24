"""Inference-artifact loading for the examiner-calibrated band model.

Fail closed: any schema/version/checksum/compatibility mismatch, missing gate
status or unknown format means the engine abstains instead of scoring. No
examiner-calibrated artifact exists yet, so in practice every load path here
must end in abstention until the release gate has passed.

Artifact contract (``pronunciation-artifact-v1``)::

    {
      "schema_version": "pronunciation-artifact-v1",
      "artifact_id": "...",
      "engine_version": "pronunciation-engine-v1",
      "feature_version": "pronunciation-features-v1",
      "calibration_version": "examiner-cal-YYYY-MM",
      "model_class": "ordinal_regression",
      "coefficients": {...},
      "bias": <float>,
      "standardization": {"mean": [...], "scale": [...]},
      "band_values": [<learned half-band classes>],
      "thresholds": [...len(band_values)-1 cut points...],
      "checksums": {"artifact": "sha256hex"},
      "training": {"dataset_ids": [...], "samples": N, "speakers": N,
                   "test_metrics": [...]},
      "metrics": {"status": "passed_release_gate", "mae": ., "qwk": .,
                  "bias": ., "within_half": ., "coverage": .,
                  "ci95": {"mae": [low, high], ...}}
    }
"""

import hashlib
import json
from pathlib import Path
from typing import Optional

from .policy import band_eligibility

SCHEMA_VERSION = "pronunciation-artifact-v1"


class ArtifactInvalid(ValueError):
    """The artifact exists but cannot be trusted; callers must abstain."""


def checksum_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_calibration_artifact(path: str | None) -> Optional[dict]:
    """Load and fully validate an artifact; ``None`` when nothing configured."""
    if not path:
        return None
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ArtifactInvalid(f"artifact unreadable: {exc}") from exc
    try:
        artifact = json.loads(raw)
    except ValueError as exc:
        raise ArtifactInvalid(f"artifact is not valid JSON: {exc}") from exc
    if artifact.get("schema_version") != SCHEMA_VERSION:
        raise ArtifactInvalid("artifact schema_version mismatch")
    stored = (artifact.get("checksums") or {}).get("artifact")
    if not stored:
        raise ArtifactInvalid("artifact checksum missing")
    # The stored checksum covers the artifact body with its own field blanked.
    body = dict(artifact)
    body["checksums"] = {"artifact": ""}
    if checksum_text(json.dumps(body, sort_keys=True, separators=(",", ":"))) != stored:
        raise ArtifactInvalid("artifact checksum mismatch")
    eligible, reason = band_eligibility(artifact)
    if not eligible:
        raise ArtifactInvalid(f"artifact not eligible: {reason}")
    for field in ("coefficients", "thresholds"):
        if not artifact.get(field):
            raise ArtifactInvalid(f"artifact missing {field}")
    metrics = artifact.get("metrics") or {}
    for field in ("mae", "qwk", "bias", "within_half", "coverage"):
        if not isinstance(metrics.get(field), (int, float)):
            raise ArtifactInvalid(f"artifact metrics missing {field}")
    return artifact


def load_or_none(path: str | None) -> tuple[Optional[dict], str, str | None]:
    """Convenience wrapper: ``(artifact_or_None, detail, failure_reason)``."""
    if not path:
        return None, "no calibration artifact configured", "calibration_artifact_missing"
    try:
        artifact = load_calibration_artifact(path)
    except ArtifactInvalid as exc:
        return None, str(exc), "calibration_artifact_failed_closed"
    if artifact is None:
        return None, "no calibration artifact configured", "calibration_artifact_missing"
    return artifact, "artifact_loaded", None


def predicted_band(artifact: dict, score_unscaled: float) -> float:
    """Apply the ordinal baseline: nearest learned band on a linear score.

    The artifact must carry ``band_values`` (the classes the model actually
    learned) with ``len(band_values) == len(thresholds) + 1``; the runtime
    never falls back to a hard-coded half-band ladder.
    """
    thresholds = sorted(float(t) for t in artifact["thresholds"])
    band_values = artifact.get("band_values") or []
    if len(band_values) != len(thresholds) + 1:
        raise ArtifactInvalid("artifact_band_values_thresholds_mismatch")
    index = sum(1 for threshold in thresholds if score_unscaled >= threshold)
    return float(band_values[min(index, len(band_values) - 1)])
