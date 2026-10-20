"""Fit monotonic criterion-band mappings from double-rated examiner data."""

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

CRITERIA = {
    "fluency_coherence": ("fluency", "fluency"),
    "lexical_resource": ("vocab", "vocab"),
    "grammatical_range_accuracy": ("grammar", "grammar"),
}


def _half_band(value):
    value = float(value)
    if value < 0 or value > 9 or value * 2 != int(value * 2):
        raise ValueError(f"invalid IELTS half-band: {value}")
    return value


def _target(row, human_key):
    ratings = row.get("human_ratings") or []
    values = []
    examiners = set()
    for rating in ratings:
        if not rating.get("prediction_hidden"):
            raise ValueError(f"{row.get('sample_id')}: examiner saw model prediction")
        examiner = rating.get("examiner_id")
        if not examiner or examiner in examiners:
            raise ValueError(f"{row.get('sample_id')}: need distinct examiner IDs")
        examiners.add(examiner)
        if rating.get(human_key) is not None:
            values.append(_half_band(rating[human_key]))
    if len(values) < 2:
        raise ValueError(f"{row.get('sample_id')}: need two {human_key} ratings")
    if max(values) - min(values) > 1:
        resolved = (row.get("adjudication") or {}).get(human_key)
        if resolved is None:
            raise ValueError(f"{row.get('sample_id')}: material disagreement needs adjudication")
        return _half_band(resolved)
    return sum(values) / len(values)


def _prediction(row, prediction_key):
    value = (row.get("prediction") or {}).get(prediction_key)
    if isinstance(value, dict):
        value = value.get("band")
    return None if value is None else _half_band(value)


def _isotonic_knots(pairs):
    grouped = defaultdict(list)
    for x, y in pairs:
        grouped[x].append(y)
    blocks = [
        {"inputs": [x], "weight": len(values), "mean": sum(values) / len(values)}
        for x, values in sorted(grouped.items())
    ]
    index = 0
    while index < len(blocks) - 1:
        if blocks[index]["mean"] <= blocks[index + 1]["mean"]:
            index += 1
            continue
        left, right = blocks[index], blocks[index + 1]
        weight = left["weight"] + right["weight"]
        blocks[index:index + 2] = [{
            "inputs": left["inputs"] + right["inputs"],
            "weight": weight,
            "mean": (left["mean"] * left["weight"] + right["mean"] * right["weight"]) / weight,
        }]
        index = max(0, index - 1)
    return [
        {"input": x, "output": round(block["mean"], 4), "n": len(grouped[x])}
        for block in blocks for x in block["inputs"]
    ]


def fit(rows, *, min_samples=100, min_speakers=30, version="examiner-cal-v1"):
    train = [row for row in rows if row.get("split") == "train"]
    speakers = {row.get("speaker_id") for row in train if row.get("speaker_id")}
    if len(train) < min_samples:
        raise ValueError(f"need at least {min_samples} train samples; found {len(train)}")
    if len(speakers) < min_speakers:
        raise ValueError(f"need at least {min_speakers} train speakers; found {len(speakers)}")
    criteria = {}
    for criterion, (prediction_key, human_key) in CRITERIA.items():
        pairs = []
        criterion_speakers = set()
        for row in train:
            prediction = _prediction(row, prediction_key)
            if prediction is None:
                continue
            pairs.append((prediction, _target(row, human_key)))
            criterion_speakers.add(row["speaker_id"])
        if len(pairs) < min_samples:
            raise ValueError(f"{criterion}: only {len(pairs)} scored train samples")
        criteria[criterion] = {
            "samples": len(pairs),
            "speakers": len(criterion_speakers),
            "knots": _isotonic_knots(pairs),
        }
    return {
        "schema_version": "speaking-band-calibration-v1",
        "version": version,
        "fitted_at": datetime.now(timezone.utc).isoformat(),
        "method": "weighted_isotonic_regression",
        "criteria": criteria,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", default="examiner-cal-v1")
    parser.add_argument("--min-samples", type=int, default=100)
    parser.add_argument("--min-speakers", type=int, default=30)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.labels.read_text(encoding="utf-8").splitlines() if line.strip()]
    artifact = fit(rows, min_samples=args.min_samples, min_speakers=args.min_speakers, version=args.version)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} from {len([r for r in rows if r.get('split') == 'train'])} train samples")


if __name__ == "__main__":
    main()
