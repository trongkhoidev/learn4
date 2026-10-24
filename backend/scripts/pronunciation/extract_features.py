"""Extract and freeze the pronunciation feature table from session metadata.

Plan §P5: training/evaluation always run from *frozen* numeric feature rows,
so that identical inputs produce byte-identical vectors under one
``pronunciation-features-v1`` version. This script never re-scores audio and
never downloads anything: feature payloads come from per-session metadata
JSON files produced by the offline extraction pipeline (private storage only).
"""

import argparse
import json
import sys
from pathlib import Path

from app.modules.speaking.pronunciation import feature_vector

from .validate_manifest import load_and_validate, resolved_pronun_band


def feature_rows(manifest: dict, sessions_dir: Path) -> list[dict]:
    """Build frozen feature rows; duplicate audiochecksums collapse to one row."""
    rows: list[dict] = []
    seen_checksums: dict[str, str] = {}
    for session in manifest.get("sessions") or []:
        if not isinstance(session, dict):
            continue
        session_id = session.get("session_id")
        features = session.get("features")
        if not isinstance(features, dict) or not features:
            raise ValueError(f"session_missing_frozen_features:{session_id}")
        checksum = feature_vector.feature_vector_checksum(features)

        session_file = sessions_dir / f"{session_id}.json"
        audio_checksum = (session_file_json(session_file) or {}).get("audio_sha256", "")
        if audio_checksum != session.get("audio_sha256"):
            raise ValueError(f"session_audio_checksum_mismatch:{session_id}")
        if audio_checksum and audio_checksum in seen_checksums:
            raise ValueError(
                f"duplicate_audio:{session_id}:matches:{seen_checksums[audio_checksum]}"
            )
        if audio_checksum:
            seen_checksums[audio_checksum] = str(session_id)

        serialized = feature_vector.serialize_feature_vector(features)
        if serialized["checksum"] != checksum:  # paranoid: canonicalization drift
            raise ValueError(f"feature_checksum_drift:{session_id}")
        label = resolved_pronun_band(session)
        if label is None:
            continue  # unresolvable labels are excluded, never guessed
        # Slice fields travel with the row so slice evaluation never degrades
        # to "unknown" for a field the manifest actually records (plan §P6).
        acoustic = session.get("acoustic") or {}
        rows.append({
            "session_id": session_id,
            "speaker": session.get("speaker"),
            "dataset_id": session.get("dataset_id"),
            "split": session.get("split"),
            "feature_version": serialized["feature_version"],
            "checksum": checksum,
            "features": serialized["features"],
            "slice": {
                "region": (acoustic.get("region") or "unknown"),
                "device": (acoustic.get("device") or "unknown"),
                "noise": (acoustic.get("noise") or "unknown"),
                "part": (acoustic.get("part") or "unknown"),
            },
            "label": label,
        })
    if not rows:
        raise ValueError("no_usable_feature_rows")
    return rows


def session_file_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="dataset manifest JSON path")
    parser.add_argument("--sessions-dir", required=True,
                        help="directory of per-session metadata JSON")
    parser.add_argument("--out", required=True, help="output feature table JSON")
    args = parser.parse_args(argv)
    try:
        manifest, reasons = load_and_validate(args.manifest)
        if reasons:
            for reason in reasons:
                print(f"ISSUE {reason}", file=sys.stderr)
            return 1
        rows = feature_rows(manifest, Path(args.sessions_dir))
        Path(args.out).write_text(json.dumps({
            "feature_version": rows[0]["feature_version"],
            "rows": rows,
        }, sort_keys=True), encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {len(rows)} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
