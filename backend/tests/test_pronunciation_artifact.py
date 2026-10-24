"""P5 tooling tests: export/inspect round-trips and fail-closed gates.

Synthetic only; no audio, no downloads. The runtime loader is exercised so a
bad artifact can never reach the engine.
"""

import json
from pathlib import Path

import pytest

from app.modules.speaking.pronunciation.calibration import (
    ArtifactInvalid,
    SCHEMA_VERSION,
    checksum_text,
    load_calibration_artifact,
)
from app.modules.speaking.pronunciation.feature_vector import (
    serialize_feature_vector,
)
from scripts.pronunciation import export_artifact, inspect_artifact


def _artifact_body() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": "examiner-cal-2026-01",
        "engine_version": "pronunciation-engine-v1",
        "feature_version": "pronunciation-features-v1",
        "calibration_version": "examiner-cal-2026-01",
        "model_class": "ordinal_regression",
        "coefficients": {"pitch_variance_norm": 0.4},
        "bias": 0.0,
        "standardization": {"mean": [1.0], "scale": [2.0]},
        "band_values": [5.0, 5.5, 6.0, 6.5],
        "thresholds": [0.1, 0.35, 0.7],
        "training": {"dataset_ids": ["learn4-pilot-1"], "samples": 10,
                     "speakers": 10},
        "metrics": {"status": "passed_release_gate", "mae": 0.35, "qwk": 0.75,
                    "bias": 0.02, "within_half": 0.85, "coverage": 1.0},
    }


def _write(tmp_path: Path, artifact: dict) -> Path:
    artifact["checksums"] = {"artifact": export_artifact.artifact_checksum(artifact)}
    path = tmp_path / "artifact.json"
    path.write_text(json.dumps(artifact, sort_keys=True, separators=(",", ":")),
                    encoding="utf-8")
    return path


def test_artifact_roundtrip_loads_clean(tmp_path):
    path = _write(tmp_path, _artifact_body())
    loaded = load_calibration_artifact(str(path))
    assert loaded is not None
    assert loaded["calibration_version"] == "examiner-cal-2026-01"
    assert loaded["metrics"]["status"] == "passed_release_gate"


def test_artifact_checksum_ranges_over_exact_body(tmp_path):
    """Any byte change under the same version string fails the checksum."""
    artifact = _artifact_body()
    path = _write(tmp_path, artifact)
    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["metrics"]["mae"] = 0.2
    tampered["checksums"] = {"artifact": checksum_text("x")}
    tampered_path = tmp_path / "tampered.json"
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ArtifactInvalid):
        load_calibration_artifact(str(tampered_path))
    # untouched sibling stays valid
    assert load_calibration_artifact(str(path)) is not None


@pytest.mark.parametrize("mutate,reason", [
    (lambda a: a.update(schema_version="pronunciation-artifact-v2"), "schema_version"),
    (lambda a: a.update(coefficients={}), "coefficients"),
    (lambda a: a.update(thresholds=[]), "thresholds"),
    (lambda a: a["metrics"].update(mae=None), "metrics"),
    (lambda a: a["metrics"].update(status="in_progress"), "not eligible"),
])
def test_artifact_fails_closed_on_every_gate(tmp_path, mutate, reason):
    artifact = _artifact_body()
    mutate(artifact)
    path = _write(tmp_path, artifact)
    with pytest.raises(ArtifactInvalid) as excinfo:
        load_calibration_artifact(str(path))
    assert reason in str(excinfo.value)


def test_inspect_reports_valid_artifact(tmp_path):
    path = _write(tmp_path, _artifact_body())
    report = inspect_artifact.summarize(str(path))
    assert report["valid"] is True
    assert report["summarized"]["calibration_version"] == "examiner-cal-2026-01"
    assert report["summarized"]["metrics"]["mae"] == 0.35


def test_inspect_reports_invalid_artifact_without_trusting_it(tmp_path):
    artifact = _artifact_body()
    artifact["calibration_version"] = "uncalibrated"
    path = _write(tmp_path, artifact)
    report = inspect_artifact.summarize(str(path))
    assert report["valid"] is False
    assert "not eligible" in report["reason"]


def test_inspect_missing_file_is_a_reported_reason(tmp_path):
    report = inspect_artifact.summarize(str(tmp_path / "nope.json"))
    assert report["valid"] is False
    assert report["reason"]


# --- export gates -------------------------------------------------------------

def _model() -> dict:
    return {
        "model_class": "ordinal_regression",
        "feature_version": "pronunciation-features-v1",
        "coefficients": {"pitch_variance_norm": 0.4},
        "bias": 0.1,
        "standardization": {"mean": [1.0], "scale": [2.0]},
        "band_values": [5.0, 5.5, 6.0],
        "thresholds": [0.1, 0.35],
        "training": {"datasets": ["learn4-pilot-1"], "samples": 10,
                     "speakers": 10},
    }


def _metrics(status: str = "passed_release_gate") -> dict:
    return {
        "status": status, "mae": 0.35, "qwk": 0.8, "bias": 0.02,
        "within_half": 0.85, "coverage": 1.0, "n": 10,
        "ci95": {"mae": (0.3, 0.4), "qwk": (0.78, 0.82), "bias": (0.0, 0.05),
                 "within_half": (0.82, 0.88), "coverage": (1.0, 1.0)},
        "slices": {},
    }


def test_export_refused_by_recomputed_gate_and_status_mismatch(tmp_path):
    # stored "failed" status but passing numbers: refused before writing
    with pytest.raises(ValueError) as excinfo:
        export_artifact.build_artifact(
            _model(), _metrics("failed_release_gate"), "examiner-cal-2026-01",
            artifact_id="a1", feature_rows=[
                {"speaker": "s1"}, {"speaker": "s2"},
            ],
        )
    assert "export_refused_status_inconsistent_with_metrics" in str(excinfo.value)
    assert not list(tmp_path.iterdir())
    # numbers that actually fail the gate: the recomputation itself refuses
    weak = _metrics("passed_release_gate")
    weak["qwk"] = 0.6  # below the plan's 0.75 gate despite stored status
    with pytest.raises(ValueError) as excinfo:
        export_artifact.build_artifact(
            _model(), weak, "examiner-cal-2026-01",
            artifact_id="a1", feature_rows=[
                {"speaker": "s1"}, {"speaker": "s2"},
            ],
        )
    assert "export_refused_release_gate_not_passed" in str(excinfo.value)
    assert "qwk_below_gate" in str(excinfo.value)
    assert not list(tmp_path.iterdir())  # nothing may be written


def test_export_refused_uncalibrated_version(tmp_path):
    with pytest.raises(ValueError) as excinfo:
        export_artifact.build_artifact(
            _model(), _metrics(), "uncalibrated", artifact_id="a1",
            feature_rows=[{"speaker": "s1"}, {"speaker": "s2"}],
        )
    assert "export_refused_uncalibrated_version" in str(excinfo.value)


def test_export_roundtrips_through_runtime_loader(tmp_path):
    model = _model()
    metrics = _metrics()
    rows = [{"speaker": "s1", "split": "test", "label": 5.0},
            {"speaker": "s2", "split": "test", "label": 6.0}]
    artifact = export_artifact.build_artifact(
        model, metrics, "examiner-cal-2026-01",
        artifact_id="a1", feature_rows=rows,
    )
    out = tmp_path / "artifact.json"
    out.write_text(json.dumps(artifact, sort_keys=True, indent=2), encoding="utf-8")
    loaded = load_calibration_artifact(str(out))
    assert isinstance(loaded, dict)
    assert loaded["artifact_id"] == "a1"


def test_serialized_feature_vector_shape():
    serialized = serialize_feature_vector({"pitch": 0.5})
    assert serialized["feature_version"] == "pronunciation-features-v1"
    assert len(serialized["checksum"]) == 64
    assert serialized["features"] == {"pitch": 0.5}
