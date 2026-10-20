"""Validate consented ASR manifests and emit a verbatim-only train export."""

import argparse
import json
from datetime import date
from pathlib import Path, PurePosixPath

REQUIRED = (
    "sample_id", "speaker_id", "session_id", "split", "part", "question_id",
    "audio_path", "reference_verbatim", "human_unclear_spans",
    "annotation_version", "consent_id", "retention_until", "metadata",
)
SPLITS = {"train", "validation", "test"}


def validate_rows(rows: list[dict], *, as_of: date | None = None) -> list[str]:
    as_of = as_of or date.today()
    errors = []
    sample_ids = set()
    speaker_splits = {}
    session_splits = {}
    for line, row in enumerate(rows, start=1):
        prefix = f"line {line}"
        if not isinstance(row, dict):
            errors.append(f"{prefix}: row must be a JSON object")
            continue
        missing = [field for field in REQUIRED if field not in row]
        if missing:
            errors.append(f"{prefix}: missing required fields: {', '.join(missing)}")
            continue
        for field in ("sample_id", "speaker_id", "session_id", "question_id", "audio_path", "annotation_version", "consent_id"):
            if not isinstance(row[field], str) or not row[field].strip():
                errors.append(f"{prefix}: {field} must be a non-empty string")
        sample_id = row.get("sample_id")
        if isinstance(sample_id, str):
            if sample_id in sample_ids:
                errors.append(f"{prefix}: duplicate sample_id {sample_id!r}")
            sample_ids.add(sample_id)
        if not isinstance(row["split"], str) or row["split"] not in SPLITS:
            errors.append(f"{prefix}: split must be one of {sorted(SPLITS)}")
        if row["part"] not in (1, 2, 3):
            errors.append(f"{prefix}: part must be 1, 2, or 3")
        path = PurePosixPath(str(row["audio_path"]))
        if path.is_absolute() or ".." in path.parts:
            errors.append(f"{prefix}: audio_path must be a safe relative path")
        if not isinstance(row["reference_verbatim"], str):
            errors.append(f"{prefix}: reference_verbatim must be a string")
        if not isinstance(row["human_unclear_spans"], list):
            errors.append(f"{prefix}: human_unclear_spans must be a list")
        else:
            for span_index, span in enumerate(row["human_unclear_spans"]):
                try:
                    start, end = float(span["start"]), float(span["end"])
                    decision = span["decision"]
                    if start < 0 or end <= start or not isinstance(decision, str) or not decision.strip():
                        raise ValueError
                except (KeyError, TypeError, ValueError):
                    errors.append(f"{prefix}: invalid human_unclear_spans[{span_index}]")
        try:
            retention = date.fromisoformat(row["retention_until"])
            if retention < as_of:
                errors.append(f"{prefix}: consent retention expired on {retention.isoformat()}")
        except (TypeError, ValueError):
            errors.append(f"{prefix}: retention_until must be an ISO date")
        metadata = row["metadata"]
        if not isinstance(metadata, dict) or any(not metadata.get(k) for k in ("device", "region", "noise")):
            errors.append(f"{prefix}: metadata needs device, region, and noise")
        for key, registry in (("speaker_id", speaker_splits), ("session_id", session_splits)):
            value = row.get(key)
            split = row.get("split")
            if isinstance(value, str) and value:
                previous = registry.setdefault(value, split)
                if previous != split:
                    errors.append(f"{prefix}: {key} {value!r} appears in multiple splits")
    return errors


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON: {exc}") from exc
    return rows


def training_inputs(rows: list[dict]) -> list[dict]:
    return [
        {
            "sample_id": row["sample_id"],
            "audio_path": row["audio_path"],
            "text": row["reference_verbatim"],
        }
        for row in rows if row["split"] == "train"
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--train-inputs", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    rows = load_jsonl(args.manifest)
    errors = validate_rows(rows, as_of=args.as_of)
    if errors:
        for error in errors:
            print(error)
        raise SystemExit(2)
    if args.train_inputs:
        output = training_inputs(rows)
        args.train_inputs.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in output),
            encoding="utf-8",
        )
        print(f"validated {len(rows)} rows; exported {len(output)} verbatim train inputs")
    else:
        print(f"validated {len(rows)} rows across {len({r['speaker_id'] for r in rows})} speakers")


if __name__ == "__main__":
    main()
