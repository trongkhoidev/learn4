"""Validate the pronunciation dataset manifest before any training step.

This validator is the leakage/consent gate required by plan §P5:

- speaker-disjoint splits (a speaker may never appear in two splits),
- unexpired, per-session consent,
- duplicate-audio detection inside/across splits,
- examiner annotation rules (two independent raters, adjudication when they
  disagree by more than one band),
- dataset licence/provenance completeness.

It returns machine-readable reason codes (an empty list means the manifest is
usable). It never touches raw audio and never scores anything.
"""

import argparse
import json
import math
import sys
from datetime import date
from pathlib import Path

SCHEMA_VERSION = "learn4-pronunciation-dataset-manifest-v1"
SPLITS = ("train", "validation", "test")
VALID_SPLITS = set(SPLITS)


def _as_date(value: str) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _disagreement(first: float, second: float) -> float:
    return abs(float(first) - float(second))


def validate_manifest(manifest: dict, *, today: date | None = None) -> list[str]:
    """Deterministically list every violation; empty list means valid."""
    today = today or date.today()
    reasons: list[str] = []

    def fail(reason: str, session_id: str | None = None) -> None:
        reasons.append(f"{session_id}: {reason}" if session_id else reason)

    if not isinstance(manifest, dict):
        return ["manifest_not_an_object"]
    if manifest.get("schema_version") != SCHEMA_VERSION:
        fail("manifest_schema_version_mismatch")

    datasets = manifest.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        fail("datasets_missing")
    known_datasets = set()
    for entry in datasets or []:
        if not isinstance(entry, dict):
            fail("dataset_entry_not_an_object")
            continue
        ds_id = entry.get("id")
        known_datasets.add(ds_id)
        for field in ("source", "license", "license_url", "provenance"):
            if not entry.get(field):
                fail(f"dataset_missing_{field}", ds_id)

    sessions = manifest.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        fail("sessions_missing")
        sessions = []

    seen_speakers: dict[str, str] = {}
    seen_audio: dict[str, str] = {}
    for session in sessions:
        if not isinstance(session, dict):
            fail("session_not_an_object")
            continue
        session_id = session.get("session_id")
        prefix = session_id or "?"
        for field in ("session_id", "speaker", "dataset_id", "consent_until",
                      "audio_sha256"):
            if not session.get(field):
                fail(f"session_missing_{field}")
        split = session.get("split")
        if split not in VALID_SPLITS:
            fail("session_split_invalid", prefix)
        if session.get("dataset_id") and known_datasets and \
                session["dataset_id"] not in known_datasets:
            fail("session_unknown_dataset", prefix)

        consent = _as_date(session.get("consent_until") or "")
        if consent is None:
            fail("session_consent_unparseable", prefix)
        elif consent < today:
            fail("session_consent_expired", prefix)

        checksum = session.get("audio_sha256")
        if checksum:
            if checksum in seen_audio:
                fail(f"duplicate_audio_with:{seen_audio[checksum]}", prefix)
            seen_audio[checksum] = prefix

        speaker = session.get("speaker")
        if speaker:
            prior = seen_speakers.get(speaker, split)
            if split in VALID_SPLITS and prior != split:
                fail(f"speaker_split_leakage_train_and_{split}", prefix)
            seen_speakers[speaker] = split

        examiners = session.get("examiners") or {}
        first = (examiners.get("first") or {}).get("pronun")
        second = (examiners.get("second") or {}).get("pronun")
        if not isinstance(first, (int, float)) or not isinstance(second, (int, float)):
            fail("session_examiner_bands_missing", prefix)
        else:
            # Two independent raters: both ratings must carry rater IDs and
            # the IDs must differ; otherwise one rater could supply both.
            first_id = (examiners.get("first") or {}).get("rater_id")
            second_id = (examiners.get("second") or {}).get("rater_id")
            if not first_id or not second_id:
                fail("session_examiner_rater_id_missing", prefix)
            elif first_id == second_id:
                fail("session_examiner_rater_ids_identical", prefix)
            if _disagreement(first, second) > 1.0:
                adjudicated = examiners.get("adjudicated") or {}
                adjudicator_band = adjudicated.get("pronun")
                adjudicator_id = adjudicated.get("rater_id")
                if not isinstance(adjudicator_band, (int, float)) or not adjudicator_id:
                    fail("session_adjudication_missing", prefix)
                elif adjudicator_id in (first_id, second_id):
                    fail("session_adjudicator_conflicts_rater", prefix)
    return reasons


def resolved_pronun_band(session: dict) -> float | None:
    """Training label: adjudicated band when present, else half-band average.

    Public-corpus scores are never mapped directly to IELTS bands (plan §P5);
    examiner labels for Learn4 sessions only.
    """
    examiners = session.get("examiners") or {}
    adjudicated = (examiners.get("adjudicated") or {}).get("pronun")
    if isinstance(adjudicated, (int, float)):
        return float(adjudicated)
    first = (examiners.get("first") or {}).get("pronun")
    second = (examiners.get("second") or {}).get("pronun")
    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        if _disagreement(first, second) > 1.0:
            return None  # no adjudication: unresolvable, count as missing label
        average = (first + second) / 2
        return math.floor(average * 2 + 0.5) / 2  # nearest half band, half-up
    return None


def load_and_validate(path: str, *, today: date | None = None) -> tuple[dict, list[str]]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    return manifest, validate_manifest(manifest, today=today)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="path to the dataset manifest JSON")
    args = parser.parse_args(argv)
    try:
        _, reasons = load_and_validate(args.manifest)
    except OSError as exc:
        print(f"manifest unreadable: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"manifest is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if reasons:
        for reason in reasons:
            print(f"ISSUE {reason}")
        return 1
    print("manifest valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
