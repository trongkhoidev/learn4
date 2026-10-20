"""Validate double-rated labels and evaluate Speaking bands with speaker CIs.

This evaluator never fits on test data and counts abstentions in coverage.
"""

import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

CRITERIA = ("fluency", "vocab", "grammar", "pronun", "overall")
ALIASES = {
    "fluency": ("fluency", "fluency_coherence"),
    "vocab": ("vocab", "lexical_resource"),
    "grammar": ("grammar", "grammatical_range_accuracy"),
    "pronun": ("pronun", "pronunciation"),
    "overall": ("overall",),
}
SPLITS = {"train", "validation", "test"}


def half_band(value):
    return math.floor(float(value) * 2 + 0.5) / 2.0


def speaker_split(speaker_id):
    """Stable legacy helper; new manifests should store a frozen split explicitly."""
    bucket = int(hashlib.sha256(str(speaker_id).encode()).hexdigest()[:8], 16) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "validation"
    return "test"


def _value(mapping, criterion):
    if not isinstance(mapping, dict):
        return None
    for alias in ALIASES[criterion]:
        value = mapping.get(alias)
        if isinstance(value, dict):
            return value.get("band", value.get("score"))
        if value is not None:
            return value
    return None


def _ratings_for(ratings, criterion):
    values = []
    examiner_ids = []
    for rating in ratings or []:
        value = _value(rating, criterion)
        if value is None:
            continue
        values.append(float(value))
        examiner_ids.append(str(rating.get("examiner_id", "")))
    return values, examiner_ids


def examiner_truth(ratings, criterion):
    values, _ = _ratings_for(ratings, criterion)
    if len(values) < 2:
        raise ValueError(f"criterion {criterion} requires at least two examiner ratings")
    return half_band(sum(values) / len(values))


def validate_rows(rows):
    errors = []
    sample_ids = set()
    speaker_splits, session_splits = {}, {}
    for index, row in enumerate(rows, start=1):
        prefix = f"row {index}"
        if not isinstance(row, dict):
            errors.append(f"{prefix}: must be an object")
            continue
        for key in ("sample_id", "speaker_id", "session_id", "split"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                errors.append(f"{prefix}: {key} is required")
        if not isinstance(row.get("split"), str) or row.get("split") not in SPLITS:
            errors.append(f"{prefix}: split must be train, validation, or test")
        sample_id = row.get("sample_id")
        if isinstance(sample_id, str):
            if sample_id in sample_ids:
                errors.append(f"{prefix}: duplicate sample_id {sample_id!r}")
            sample_ids.add(sample_id)
        for key, registry in (("speaker_id", speaker_splits), ("session_id", session_splits)):
            value = row.get(key)
            if isinstance(value, str) and row.get("split") in SPLITS:
                previous = registry.setdefault(value, row["split"])
                if previous != row["split"]:
                    errors.append(f"{prefix}: {key} {value!r} leaks across splits")
        ratings = row.get("human_ratings")
        if not isinstance(ratings, list):
            errors.append(f"{prefix}: human_ratings must be an array")
            continue
        examiner_ids = [str(r.get("examiner_id", "")).strip() for r in ratings]
        for criterion in CRITERIA:
            values, ids = _ratings_for(ratings, criterion)
            if len(values) < 2 or len(set(ids)) < 2 or any(not value for value in ids):
                errors.append(f"{prefix}: {criterion} needs two distinct examiner IDs and ratings")
                continue
            if any(value < 0 or value > 9 or abs(value * 2 - round(value * 2)) > 1e-8 for value in values):
                errors.append(f"{prefix}: {criterion} ratings must be IELTS half-bands in [0, 9]")
            if max(values) - min(values) > 1.0:
                adjudication = row.get("adjudication")
                resolved = (adjudication or {}).get("resolved", {}) if isinstance(adjudication, dict) else {}
                adjudicator = (adjudication or {}).get("adjudicator_id") if isinstance(adjudication, dict) else None
                if not adjudicator or _value(resolved, criterion) is None:
                    errors.append(f"{prefix}: {criterion} disagreement requires adjudicator and resolved band")
        if len(set(examiner_ids)) != len(examiner_ids):
            errors.append(f"{prefix}: examiner IDs must be unique within sample")
        if any(rating.get("prediction_hidden") is not True for rating in ratings):
            errors.append(f"{prefix}: every examiner rating must record prediction_hidden=true")
        prediction = row.get("prediction")
        if not isinstance(prediction, dict):
            errors.append(f"{prefix}: prediction must be a criterion object")
        else:
            for criterion in CRITERIA:
                value = _value(prediction, criterion)
                raw = next((prediction.get(alias) for alias in ALIASES[criterion] if prediction.get(alias) is not None), None)
                status = raw.get("status") if isinstance(raw, dict) else None
                if value is not None and status != "scored":
                    errors.append(f"{prefix}: {criterion} band requires status=scored")
                if value is None and status not in {"insufficient_evidence", "needs_review", "failed", "partial"}:
                    errors.append(f"{prefix}: null {criterion} band requires an abstention status")
                if value is not None:
                    try:
                        numeric = float(value)
                        if numeric < 0 or numeric > 9 or abs(numeric * 2 - round(numeric * 2)) > 1e-8:
                            raise ValueError
                    except (TypeError, ValueError):
                        errors.append(f"{prefix}: {criterion} prediction must be an IELTS half-band in [0, 9]")
    return sorted(set(errors))


def quadratic_weighted_kappa(truth, predicted, minimum=0.0, maximum=9.0, step=0.5):
    if not truth:
        return 0.0
    size = int(round((maximum - minimum) / step)) + 1
    observed = [[0.0] * size for _ in range(size)]
    truth_hist = [0.0] * size
    pred_hist = [0.0] * size
    for left, right in zip(truth, predicted):
        i = max(0, min(size - 1, round((left - minimum) / step)))
        j = max(0, min(size - 1, round((right - minimum) / step)))
        observed[i][j] += 1
        truth_hist[i] += 1
        pred_hist[j] += 1
    count = float(len(truth))
    numerator = denominator = 0.0
    divisor = float((size - 1) ** 2 or 1)
    for i in range(size):
        for j in range(size):
            weight = ((i - j) ** 2) / divisor
            numerator += weight * observed[i][j]
            denominator += weight * (truth_hist[i] * pred_hist[j] / count)
    return 1.0 - numerator / denominator if denominator else 0.0


def metric_block(pairs):
    truth = [left for left, _ in pairs]
    predicted = [right for _, right in pairs]
    errors = [right - left for left, right in pairs]
    count = len(pairs)
    if not count:
        return {"n": 0, "mae": None, "mean_bias": None, "within_half": None, "exact": None, "qwk": None}
    return {
        "n": count,
        "mae": round(sum(abs(value) for value in errors) / count, 4),
        "mean_bias": round(sum(errors) / count, 4),
        "within_half": round(sum(abs(value) <= 0.5 for value in errors) / count, 4),
        "exact": round(sum(value == 0 for value in errors) / count, 4),
        "qwk": round(quadratic_weighted_kappa(truth, predicted), 4),
    }


def _truth(row, criterion):
    adjudication = row.get("adjudication") or {}
    resolved = _value(adjudication.get("resolved"), criterion)
    if resolved is not None:
        return half_band(resolved)
    return examiner_truth(row.get("human_ratings") or [], criterion)


def _prediction(row, criterion):
    value = _value(row.get("prediction"), criterion)
    return half_band(value) if value is not None else None


def _cluster_ci(grouped_pairs, *, samples=1000, seed=17):
    speakers = list(grouped_pairs)
    if len(speakers) < 2 or samples <= 0:
        return {"speaker_count": len(speakers), "samples": samples, "mae_95_ci": None, "within_half_95_ci": None}
    rng = random.Random(seed)
    maes, within = [], []
    for _ in range(samples):
        pairs = [pair for speaker in rng.choices(speakers, k=len(speakers)) for pair in grouped_pairs[speaker]]
        block = metric_block(pairs)
        if block["mae"] is not None:
            maes.append(block["mae"])
            within.append(block["within_half"])
    maes.sort()
    within.sort()
    def interval(values):
        if not values:
            return None
        return [values[math.floor(0.025 * (len(values) - 1))], values[math.ceil(0.975 * (len(values) - 1))]]
    return {
        "speaker_count": len(speakers), "samples": samples,
        "mae_95_ci": interval(maes), "within_half_95_ci": interval(within),
    }


def _status(row, criterion):
    prediction = row.get("prediction") or {}
    for alias in ALIASES[criterion]:
        value = prediction.get(alias)
        if isinstance(value, dict):
            return value.get("status")
    return "scored" if _prediction(row, criterion) is not None else "insufficient_evidence"


def _feedback_metrics(rows):
    claims = [claim for row in rows for claim in (row.get("human_audited_claims") or [])]
    confirmed = sum(bool(claim.get("confirmed_by_audio")) for claim in claims)
    fabricated = sum(bool(claim.get("fabricated_quote")) for claim in claims)
    return {
        "audited_claims": len(claims),
        "confirmed_claims": confirmed,
        "precision": confirmed / len(claims) if claims else None,
        "fabricated_quote_count": fabricated,
    }


def evaluate(rows, split="test", min_slice=10, min_speakers=30, bootstrap_samples=1000):
    validation_errors = validate_rows(rows)
    if validation_errors:
        raise ValueError("Invalid calibration data: " + "; ".join(validation_errors))
    selected = [row for row in rows if row["split"] == split]
    sample_count = len(selected)
    speaker_count = len({row["speaker_id"] for row in selected})
    by_criterion = {criterion: [] for criterion in CRITERIA}
    by_speaker = {criterion: defaultdict(list) for criterion in CRITERIA}
    coverage = {criterion: {"eligible": sample_count, "scored": 0, "abstained": 0, "rate": 0.0}
                for criterion in CRITERIA}
    slices = defaultdict(lambda: {criterion: [] for criterion in CRITERIA})
    slice_speakers = defaultdict(set)
    for row in selected:
        metadata = row.get("metadata") or {}
        for criterion in CRITERIA:
            pred = _prediction(row, criterion)
            if pred is None:
                coverage[criterion]["abstained"] += 1
            else:
                coverage[criterion]["scored"] += 1
                pair = (_truth(row, criterion), pred)
                by_criterion[criterion].append(pair)
                by_speaker[criterion][row["speaker_id"]].append(pair)
                for field in ("device", "noise", "region", "accent", "band"):
                    value = metadata.get(field)
                    if field == "band" and value is None:
                        value = _truth(row, criterion)
                    if value is not None:
                        slices[(field, str(value))][criterion].append(pair)
                        slice_speakers[(field, str(value))].add(row["speaker_id"])
    for criterion in CRITERIA:
        item = coverage[criterion]
        item["rate"] = item["scored"] / item["eligible"] if item["eligible"] else 0.0
    metrics = {criterion: metric_block(pairs) for criterion, pairs in by_criterion.items()}
    slice_report = {}
    for key, criteria in sorted(slices.items()):
        field, value = key
        slice_report[f"{field}={value}"] = {
            "sample_count": max((len(pairs) for pairs in criteria.values()), default=0),
            "speaker_count": len(slice_speakers[key]),
            "eligible_for_gate": (
                max((len(pairs) for pairs in criteria.values()), default=0) >= min_slice
                and len(slice_speakers[key]) >= min(min_speakers, min_slice)
            ),
            "criteria": {criterion: metric_block(pairs) for criterion, pairs in criteria.items()},
        }
    data_quality = {
        "sample_count": sample_count,
        "unique_speakers": speaker_count,
        "minimum_unique_speakers": min_speakers,
        "speaker_threshold_met": speaker_count >= min_speakers,
        "split": split,
        "split_source": "explicit_manifest",
    }
    feedback = _feedback_metrics(selected)
    gates = {
        criterion: (
            data_quality["speaker_threshold_met"]
            and coverage[criterion]["rate"] >= 0.80
            and metrics[criterion].get("n", 0) >= 30
            and metrics[criterion].get("mae", 99) is not None
            and metrics[criterion]["mae"] <= 0.5
            and metrics[criterion].get("qwk", -1) is not None
            and metrics[criterion]["qwk"] >= 0.70
        )
        for criterion in CRITERIA[:-1]
    }
    gates["overall_within_half"] = (
        data_quality["speaker_threshold_met"]
        and coverage["overall"]["rate"] >= 0.80
        and metrics["overall"].get("n", 0) >= 30
        and (metrics["overall"].get("within_half") or 0) >= 0.80
    )
    gates["feedback_precision"] = feedback["precision"] is not None and feedback["precision"] >= 0.90
    gates["zero_fabricated_quotes"] = feedback["fabricated_quote_count"] == 0 and feedback["audited_claims"] > 0
    gates["all_pass"] = all(gates.values())
    return {
        "split": split,
        "speaker_disjoint": True,
        "data_quality": data_quality,
        "sample_count": sample_count,
        "metrics": metrics,
        "coverage": coverage,
        "speaker_bootstrap_95_ci": {
            criterion: _cluster_ci(by_speaker[criterion], samples=bootstrap_samples, seed=17 + index)
            for index, criterion in enumerate(CRITERIA)
        },
        "feedback_audit": feedback,
        "slices": slice_report,
        "release_gates": gates,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--split", choices=("train", "validation", "test"), default="test")
    parser.add_argument("--output", type=Path, default=Path("calibration-report.json"))
    parser.add_argument("--min-slice", type=int, default=10)
    parser.add_argument("--min-speakers", type=int, default=30)
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    report = evaluate(
        rows, args.split, args.min_slice, args.min_speakers, args.bootstrap_samples,
    )
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["release_gates"], indent=2))
    raise SystemExit(0 if report["release_gates"]["all_pass"] else 2)


if __name__ == "__main__":
    main()
