"""P5 dataset manifest validation + feature-table tests (synthetic only).

Covers: manifest structure, speaker-disjoint splits, consent expiry, duplicate
audio, examiner annotation rules, feature freezing with deterministic
checksums, and label resolution.
"""

import json
import tempfile
from datetime import date
from pathlib import Path

import pytest

from scripts.pronunciation import extract_features, validate_manifest

from app.modules.speaking.pronunciation.feature_vector import (
    feature_vector_checksum,
)

TODAY = date(2026, 10, 21)


def manifest(**overrides) -> dict:
    def rater(band: float, rater_id: str) -> dict:
        return {"pronun": band, "rater_id": rater_id}

    base = {
        "schema_version": "learn4-pronunciation-dataset-manifest-v1",
        "datasets": [{
            "id": "learn4-pilot-1", "source": "learn4-private",
            "license": "internal-consented", "license_url": "example://consent",
            "provenance": {"created_by": "examiner-panel"},
        }],
        "sessions": [{
            "session_id": "s1", "speaker": "sp1", "dataset_id": "learn4-pilot-1",
            "split": "train", "consent_until": "2027-01-01",
            "audio_sha256": "a" * 64, "audio_path": "s3://private/audio/s1.webm",
            "examiners": {"first": rater(5.0, "ex-1"), "second": rater(5.5, "ex-2")},
        }],
    }
    base["sessions"].extend(overrides.pop("extra_sessions", []))
    base.update(overrides)
    return base


def test_valid_manifest_passes():
    assert validate_manifest.validate_manifest(manifest(), today=TODAY) == []


def test_speaker_appearing_in_two_splits_is_leakage():
    extra = [{
        "session_id": "s2", "speaker": "sp1", "dataset_id": "learn4-pilot-1",
        "split": "test", "consent_until": "2027-01-01",
        "audio_sha256": "b" * 64, "audio_path": "s3://private/audio/s2.webm",
        "examiners": {"first": {"pronun": 5.0}, "second": {"pronun": 5.0}},
    }]
    reasons = validate_manifest.validate_manifest(
        manifest(extra_sessions=extra), today=TODAY,
    )
    assert any("speaker_split_leakage" in r for r in reasons)


def test_expired_consent_blocks_the_session():
    reasons = validate_manifest.validate_manifest(manifest(), today=date(2027, 2, 1))
    assert "s1: session_consent_expired" in reasons


def test_duplicate_audio_checksums_fail():
    dup = dict(manifest()["sessions"][0])
    dup["session_id"], dup["audio_path"] = "s2", "s3://private/audio/x.webm"
    dup["speaker"] = "sp2"
    del dup["examiners"]  # keep focus on duplicate audio
    reasons = validate_manifest.validate_manifest(
        manifest(extra_sessions=[dup]), today=TODAY,
    )
    assert any("duplicate_audio" in r for r in reasons)


@pytest.mark.parametrize("first,second,adjudicated,expected", [
    (5.0, 5.5, None, None),          # agreement <= 1 band: averaged later
    (5.0, 6.5, None, "session_adjudication_missing"),
    (5.0, 6.5, 6.0, None),           # adjudicated: fine
])
def test_examiner_disagreement_rule(first, second, adjudicated, expected):
    session = manifest()["sessions"][0]
    examiners = {
        "first": {"pronun": first, "rater_id": "ex-1"},
        "second": {"pronun": second, "rater_id": "ex-2"},
    }
    if adjudicated is not None:
        examiners["adjudicated"] = {"pronun": adjudicated, "rater_id": "ex-3"}
    session["examiners"] = examiners
    reasons = validate_manifest.validate_manifest(
        manifest(sessions=[session]), today=TODAY,
    )
    if expected is None:
        assert reasons == []
    else:
        assert any(expected in reason for reason in reasons)


def test_missing_examiner_bands_fail():
    session = manifest()["sessions"][0]
    session["examiners"] = {"first": {"pronun": 5.0, "rater_id": "ex-1"}}
    reasons = validate_manifest.validate_manifest(
        manifest(sessions=[session]), today=TODAY,
    )
    assert "s1: session_examiner_bands_missing" in reasons


def test_examiner_rater_ids_required_and_distinct():
    session = manifest()["sessions"][0]
    session["examiners"] = {
        "first": {"pronun": 5.0}, "second": {"pronun": 5.5, "rater_id": "ex-2"},
    }
    reasons = validate_manifest.validate_manifest(
        manifest(sessions=[session]), today=TODAY,
    )
    assert any("rater_id_missing" in r for r in reasons)

    session["examiners"] = {
        "first": {"pronun": 5.0, "rater_id": "ex-1"},
        "second": {"pronun": 5.5, "rater_id": "ex-1"},  # same rater: refused
    }
    reasons = validate_manifest.validate_manifest(
        manifest(sessions=[session]), today=TODAY,
    )
    assert any("rater_ids_identical" in r for r in reasons)


def test_adjudicator_must_differ_from_both_raters():
    session = manifest()["sessions"][0]
    session["examiners"] = {
        "first": {"pronun": 5.0, "rater_id": "ex-1"},
        "second": {"pronun": 6.5, "rater_id": "ex-2"},
        "adjudicated": {"pronun": 6.0, "rater_id": "ex-1"},  # conflicts
    }
    reasons = validate_manifest.validate_manifest(
        manifest(sessions=[session]), today=TODAY,
    )
    assert any("adjudicator_conflicts_rater" in r for r in reasons)


def test_audio_path_optional():
    session = manifest()["sessions"][0]
    session.pop("audio_path")
    assert validate_manifest.validate_manifest(
        manifest(sessions=[session]), today=TODAY,
    ) == []


def test_unknown_dataset_and_missing_licence_fail():
    session = manifest()["sessions"][0]
    session["dataset_id"] = "ghost-dataset"
    bad_dataset = dict(manifest()["datasets"][0])
    del bad_dataset["license"]
    reasons = validate_manifest.validate_manifest(
        manifest(sessions=[session], datasets=[bad_dataset]), today=TODAY,
    )
    assert any("session_unknown_dataset" in r for r in reasons)
    assert any("dataset_missing_license" in r for r in reasons)


def test_label_resolution_adjudicated_vs_average():
    session = manifest()["sessions"][0]
    session["examiners"] = {
        "first": {"pronun": 5.0, "rater_id": "ex-1"},
        "second": {"pronun": 5.5, "rater_id": "ex-2"},
    }
    assert validate_manifest.resolved_pronun_band(session) == 5.5  # round-half-up
    session["examiners"]["adjudicated"] = {"pronun": 6.0, "rater_id": "ex-3"}
    assert validate_manifest.resolved_pronun_band(session) == 6.0
    session["examiners"] = {
        "first": {"pronun": 4.0, "rater_id": "ex-1"},
        "second": {"pronun": 6.0, "rater_id": "ex-2"},
    }
    assert validate_manifest.resolved_pronun_band(session) is None  # no adjudication


def test_manifest_schema_version_mismatch():
    reasons = validate_manifest.validate_manifest(
        manifest(schema_version="v0"), today=TODAY,
    )
    assert "manifest_schema_version_mismatch" in reasons


# --- feature table ------------------------------------------------------------

def test_feature_rows_freeze_checksum_and_label():
    session = manifest()["sessions"][0]
    features = {"speech_rate_wpm": 120.0, "voiced_coverage": 0.6}
    session = {**session, "features": features}
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "s1.json").write_text(
            json.dumps({"audio_sha256": session["audio_sha256"]}), encoding="utf-8")
        rows = extract_features.feature_rows(manifest(sessions=[session]), Path(tmp))
    assert len(rows) == 1
    row = rows[0]
    assert row["split"] == "train"
    assert row["feature_version"] == "pronunciation-features-v1"
    assert row["checksum"] == feature_vector_checksum(features)
    assert row["label"] == 5.5
