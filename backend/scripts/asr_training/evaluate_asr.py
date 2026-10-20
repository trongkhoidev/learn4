"""Evaluate frozen ASR predictions with speaker-clustered confidence intervals."""

import argparse
import json
import math
import random
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

CONTENT_STOPWORDS = {
    "a", "an", "the", "i", "you", "he", "she", "it", "we", "they", "me", "my",
    "your", "his", "her", "our", "their", "is", "am", "are", "was", "were", "be",
    "been", "being", "do", "does", "did", "to", "of", "in", "on", "at", "for",
    "and", "or", "but", "as", "if", "so", "that", "this", "these", "those", "with",
    "from", "by", "about", "have", "has", "had", "not", "no",
}
CONTRACTIONS = {
    "i'm": "i am", "you're": "you are", "we're": "we are", "they're": "they are",
    "he's": "he is", "she's": "she is", "it's": "it is", "i've": "i have",
    "we've": "we have", "they've": "they have", "don't": "do not", "doesn't": "does not",
    "didn't": "did not", "can't": "cannot", "won't": "will not", "isn't": "is not",
    "aren't": "are not", "wasn't": "was not", "weren't": "were not",
}
PRESERVATION_CATEGORIES = ("grammar_errors", "fillers", "repetitions", "false_starts")


def tokenize(text: str, *, normalized: bool = False) -> list[str]:
    value = unicodedata.normalize("NFKC", (text or "").lower()).replace("’", "'")
    tokens = re.findall(r"[a-z0-9']+", value)
    if normalized:
        expanded = []
        for token in tokens:
            expanded.extend(CONTRACTIONS.get(token, token).split())
        return expanded
    return tokens


def align(reference: list[str], hypothesis: list[str]) -> tuple[int, int, int, list[tuple[str, int | None, int | None]]]:
    """Return substitution/deletion/insertion counts and deterministic edit path."""
    rows, cols = len(reference) + 1, len(hypothesis) + 1
    cost = [[0] * cols for _ in range(rows)]
    back = [[None] * cols for _ in range(rows)]
    for i in range(1, rows):
        cost[i][0], back[i][0] = i, "D"
    for j in range(1, cols):
        cost[0][j], back[0][j] = j, "I"
    for i in range(1, rows):
        for j in range(1, cols):
            same = reference[i - 1] == hypothesis[j - 1]
            choices = [
                (cost[i - 1][j - 1] + (0 if same else 1), "E" if same else "S"),
                (cost[i - 1][j] + 1, "D"),
                (cost[i][j - 1] + 1, "I"),
            ]
            cost[i][j], back[i][j] = min(choices, key=lambda item: (item[0], {"E": 0, "S": 1, "D": 2, "I": 3}[item[1]]))
    i, j = len(reference), len(hypothesis)
    path = []
    substitutions = deletions = insertions = 0
    while i or j:
        operation = back[i][j]
        if operation in {"E", "S"}:
            path.append((operation, i - 1, j - 1))
            substitutions += operation == "S"
            i -= 1
            j -= 1
        elif operation == "D":
            path.append((operation, i - 1, None))
            deletions += 1
            i -= 1
        else:
            path.append((operation, None, j - 1))
            insertions += 1
            j -= 1
    path.reverse()
    return substitutions, deletions, insertions, path


def _wer_block(rows: list[dict], *, normalized: bool) -> dict:
    substitutions = deletions = insertions = reference_words = content_deletions = 0
    chars_ref = chars_hyp = chars_edits = 0
    for row in rows:
        reference = tokenize(row.get("reference_verbatim", ""), normalized=normalized)
        hypothesis = tokenize(row.get("prediction", ""), normalized=normalized)
        sub, delete, insert, path = align(reference, hypothesis)
        substitutions += sub
        deletions += delete
        insertions += insert
        reference_words += len(reference)
        content_deletions += sum(
            operation == "D" and reference[index] not in CONTENT_STOPWORDS
            for operation, index, _ in path if index is not None
        )
        reference_chars = " ".join(reference)
        hypothesis_chars = " ".join(hypothesis)
        _, _, char_edits, _ = align(list(reference_chars), list(hypothesis_chars))
        chars_ref += len(reference_chars)
        chars_hyp += len(hypothesis_chars)
        chars_edits += char_edits
    errors = substitutions + deletions + insertions
    return {
        "n": len(rows),
        "reference_words": reference_words,
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
        "content_word_deletions": content_deletions,
        "wer": errors / reference_words if reference_words else None,
        "cer": chars_edits / chars_ref if chars_ref else None,
        "silence_hallucination_rate": None,
    }


def _preservation(rows: list[dict]) -> dict:
    counts = {category: {"n": 0, "preserved": 0} for category in PRESERVATION_CATEGORIES}
    for row in rows:
        hypothesis = tokenize(row.get("prediction", ""))
        for category, spans in (row.get("preservation_tags") or {}).items():
            if category not in counts:
                continue
            for span in spans or []:
                tokens = tokenize(span)
                if not tokens:
                    continue
                counts[category]["n"] += 1
                # Span match keeps the annotation's repetition count and order.
                preserved = any(hypothesis[i:i + len(tokens)] == tokens
                                for i in range(len(hypothesis) - len(tokens) + 1))
                counts[category]["preserved"] += int(preserved)
    return {
        key: {
            **value,
            "rate": value["preserved"] / value["n"] if value["n"] else None,
        }
        for key, value in counts.items()
    }


def _silence_hallucination(rows: list[dict]) -> dict:
    silent = [row for row in rows if row.get("has_speech") is False]
    hallucinated = sum(bool(tokenize(row.get("prediction", ""))) for row in silent)
    return {
        "n": len(silent),
        "hallucinated": hallucinated,
        "rate": hallucinated / len(silent) if silent else None,
    }


def _timestamp_error(rows: list[dict]) -> dict:
    absolute_errors = []
    for row in rows:
        reference_words = row.get("reference_words") or []
        predicted_words = row.get("predicted_words") or []
        reference = [tokenize(word.get("word", ""))[0] if tokenize(word.get("word", "")) else "" for word in reference_words]
        predicted = [tokenize(word.get("word", ""))[0] if tokenize(word.get("word", "")) else "" for word in predicted_words]
        _, _, _, path = align(reference, predicted)
        for operation, ref_index, hyp_index in path:
            if operation != "E" or ref_index is None or hyp_index is None:
                continue
            left, right = reference_words[ref_index], predicted_words[hyp_index]
            for field in ("start", "end"):
                try:
                    absolute_errors.append(abs(float(left[field]) - float(right[field])))
                except (KeyError, TypeError, ValueError):
                    continue
    return {
        "matched_boundaries": len(absolute_errors),
        "mean_absolute_error_seconds": sum(absolute_errors) / len(absolute_errors) if absolute_errors else None,
        "p95_absolute_error_seconds": sorted(absolute_errors)[math.ceil(0.95 * len(absolute_errors)) - 1] if absolute_errors else None,
    }


def _runtime_metrics(rows: list[dict]) -> dict:
    latency = sorted(float(row["latency_ms"]) for row in rows if row.get("latency_ms") is not None)
    audio_durations = [float(row["audio_duration_s"]) for row in rows if row.get("audio_duration_s") is not None and float(row["audio_duration_s"]) > 0]
    costs = [float(row["cost_usd"]) for row in rows if row.get("cost_usd") is not None]
    rtfs = [float(row["latency_ms"]) / 1000 / float(row["audio_duration_s"])
            for row in rows
            if row.get("latency_ms") is not None and row.get("audio_duration_s") is not None
            and float(row["audio_duration_s"]) > 0]

    def percentile(values, fraction):
        if not values:
            return None
        return values[math.ceil(fraction * len(values)) - 1]

    return {
        "latency_ms": {
            "n": len(latency),
            "p50": percentile(latency, 0.50),
            "p95": percentile(latency, 0.95),
        },
        "audio_duration_seconds": sum(audio_durations),
        "real_time_factor": {"n": len(rtfs), "p50": percentile(sorted(rtfs), 0.50), "p95": percentile(sorted(rtfs), 0.95)},
        "cost_usd": {"n": len(costs), "total": sum(costs) if costs else None},
    }


def _sample_metrics(rows: list[dict]) -> dict:
    raw = _wer_block(rows, normalized=False)
    normalized = _wer_block(rows, normalized=True)
    return {
        "sample_count": len(rows),
        "speaker_count": len({row["speaker_id"] for row in rows}),
        "wer_raw": raw,
        "wer_normalized": normalized,
        "preservation": _preservation(rows),
        "silence": _silence_hallucination(rows),
        "timestamp_error": _timestamp_error(rows),
        "runtime": _runtime_metrics(rows),
    }


def _cluster_ci(rows: list[dict], *, normalized: bool, bootstrap_samples: int, seed: int) -> dict:
    clusters = defaultdict(list)
    for row in rows:
        clusters[row["speaker_id"]].append(row)
    speaker_ids = list(clusters)
    if len(speaker_ids) < 2 or bootstrap_samples <= 0:
        return {"speaker_count": len(speaker_ids), "samples": bootstrap_samples, "wer_95_ci": None}
    rng = random.Random(seed)
    values = []
    for _ in range(bootstrap_samples):
        sampled = [row for speaker_id in rng.choices(speaker_ids, k=len(speaker_ids)) for row in clusters[speaker_id]]
        value = _wer_block(sampled, normalized=normalized)["wer"]
        if value is not None:
            values.append(value)
    values.sort()
    if not values:
        interval = None
    else:
        interval = [values[math.floor(0.025 * (len(values) - 1))], values[math.ceil(0.975 * (len(values) - 1))]]
    return {"speaker_count": len(speaker_ids), "samples": bootstrap_samples, "wer_95_ci": interval}


def _slices(rows: list[dict]) -> dict:
    buckets = defaultdict(list)
    for row in rows:
        metadata = row.get("metadata") or {}
        for field, value in {
            "part": row.get("part"),
            "band": metadata.get("band"),
            "device": metadata.get("device"),
            "noise": metadata.get("noise"),
            "region": metadata.get("region"),
            "accent": metadata.get("accent"),
        }.items():
            if value is not None:
                buckets[(field, str(value))].append(row)
    return {
        f"{field}={value}": _sample_metrics(bucket)
        for (field, value), bucket in sorted(buckets.items())
    }


def validate_split_manifest(rows: list[dict]) -> list[str]:
    errors = []
    speakers, sessions, sample_ids = {}, {}, set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"row {index} must be an object")
            continue
        for field in ("sample_id", "speaker_id", "session_id", "split", "reference_verbatim", "prediction"):
            if field not in row or (field in {"sample_id", "speaker_id", "session_id", "split"} and not isinstance(row[field], str)):
                errors.append(f"row {index} missing or invalid {field}")
        if not isinstance(row.get("split"), str) or row.get("split") not in {"train", "validation", "test"}:
            errors.append(f"row {index} has an invalid split")
        sample_id = row.get("sample_id")
        if isinstance(sample_id, str):
            if sample_id in sample_ids:
                errors.append(f"duplicate sample_id {sample_id!r}")
            sample_ids.add(sample_id)
        if "has_speech" in row and not isinstance(row["has_speech"], bool):
            errors.append(f"row {index} has_speech must be boolean")
        for field in ("latency_ms", "audio_duration_s", "cost_usd"):
            if row.get(field) is not None:
                try:
                    numeric = float(row[field])
                    if not math.isfinite(numeric) or numeric < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    errors.append(f"row {index} has invalid {field}")
        if row.get("preservation_tags") is not None and not isinstance(row.get("preservation_tags"), dict):
            errors.append(f"row {index} preservation_tags must be an object")
        for field in ("reference_words", "predicted_words"):
            if row.get(field) is not None and not isinstance(row[field], list):
                errors.append(f"row {index} {field} must be an array")
        for field, registry in (("speaker_id", speakers), ("session_id", sessions)):
            value, split = row.get(field), row.get("split")
            if not isinstance(value, str) or not value or not isinstance(split, str) or not split:
                errors.append(f"row missing {field} or split")
                continue
            previous = registry.setdefault(value, split)
            if previous != split:
                errors.append(f"{field} {value!r} leaks across splits")
        if not isinstance(row.get("reference_verbatim"), str) or not isinstance(row.get("prediction"), str):
            continue
    return errors


def evaluate(rows: list[dict], *, split="test", bootstrap_samples=1000, seed=17) -> dict:
    errors = validate_split_manifest(rows)
    if errors:
        raise ValueError("; ".join(sorted(set(errors))))
    selected = [row for row in rows if row.get("split") == split]
    report = _sample_metrics(selected)
    report.update({
        "split": split,
        "normalization_policy": "NFKC, lowercase, punctuation tokenization; normalized additionally expands listed contractions",
        "bootstrap_by_speaker": {
            "wer_raw": _cluster_ci(selected, normalized=False, bootstrap_samples=bootstrap_samples, seed=seed),
            "wer_normalized": _cluster_ci(selected, normalized=True, bootstrap_samples=bootstrap_samples, seed=seed + 1),
        },
        "slices": _slices(selected),
    })
    vietnamese_rows = [row for row in selected if (row.get("metadata") or {}).get("accent", "").lower() in {"vi", "vietnamese", "vietnamese_english"}]
    raw_wer = report["wer_raw"]["wer"]
    vn_wer = _wer_block(vietnamese_rows, normalized=False)["wer"] if vietnamese_rows else None
    report["proposed_asr_gates"] = {
        "overall_wer_le_12_percent": raw_wer is not None and raw_wer <= 0.12,
        "vietnamese_slice_wer_le_15_percent": vn_wer is not None and vn_wer <= 0.15,
        "vietnamese_slice_wer": vn_wer,
        "gates_are_proposals_not_certification": True,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSONL manifest joined with frozen model predictions")
    parser.add_argument("--split", choices=("train", "validation", "test"), default="test")
    parser.add_argument("--output", type=Path, default=Path("asr-evaluation.json"))
    parser.add_argument("--bootstrap-samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    report = evaluate(rows, split=args.split, bootstrap_samples=args.bootstrap_samples, seed=args.seed)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "split": report["split"],
        "samples": report["sample_count"],
        "speakers": report["speaker_count"],
        "proposed_asr_gates": report["proposed_asr_gates"],
    }, indent=2))


if __name__ == "__main__":
    main()
