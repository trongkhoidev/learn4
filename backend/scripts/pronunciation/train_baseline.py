"""Fit the baseline examiner-calibrated band model (plan §P6 baseline).

Deliberately simple and explainable: ridge-regularised linear score on frozen
features, converted to a half-band via ordinal threshold cuts. Speaker
disjointness is enforced before anything is fitted. Deep end-to-end models are
out of scope for this baseline (plan §P6) — introduce one only if baseline
metrics and data prove it necessary.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from app.modules.speaking.pronunciation.policy import FEATURE_VERSION

from .validate_manifest import validate_manifest


def numeric_design(rows: list[dict]) -> tuple[np.ndarray, list[str]]:
    """Deterministic feature matrix over keys numeric in *every* usable row.

    A feature key survives only when it is numeric in each row; keys that are
    partially missing are excluded entirely rather than imputing 0, because 0
    would silently mean "worst possible value" (plan §P4). Missing features
    must translate into abstention downstream, never into a fake score.
    """
    candidates: set[str] = set()
    for row in rows:
        candidates.update(row.get("features") or {})
    usable = []
    for key in sorted(candidates):
        numeric_everywhere = all(
            isinstance((row.get("features") or {}).get(key), (int, float))
            and not isinstance((row.get("features") or {}).get(key), bool)
            for row in rows
        )
        if numeric_everywhere:
            usable.append(key)
    if not usable:
        raise ValueError("no_numeric_feature_keys")
    matrix = np.asarray(
        [[float(row["features"][key]) for key in usable] for row in rows],
        dtype=np.float64,
    )
    return matrix, usable


def _standardise(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = matrix.mean(axis=0)
    scale = matrix.std(axis=0)
    scale[scale == 0.0] = 1.0  # constant columns carry no signal
    return (matrix - mean) / scale, mean, scale


def _thresholds_between_classes(scores: np.ndarray, labels: np.ndarray,
                                ) -> tuple[list[float], list[float]]:
    """Ordinal cuts + the actual band values between them (learned classes)."""
    classes = sorted({float(label) for label in labels})
    if len(classes) < 2:
        raise ValueError("not_enough_band_classes")
    means = [float(np.mean(scores[labels == band])) for band in classes]
    cuts = [(means[index] + means[index + 1]) / 2.0
            for index in range(len(means) - 1)]
    monotone = all(cuts[i] < cuts[i + 1] for i in range(len(cuts) - 1))
    if not monotone:  # non-separable labels: refuse, do not ship a broken model
        raise ValueError("ordinal_thresholds_not_monotone")
    return [round(cut, 6) for cut in cuts], classes


def fit_ordinal(rows: list[dict], *, lambda_: float = 1.0) -> dict:
    """Ridge linear score + ordinal half-band thresholds. Fully deterministic."""
    labels = np.asarray([float(row["label"]) for row in rows], dtype=np.float64)
    raw, keys = numeric_design(rows)
    standardised, mean, scale = _standardise(raw)
    design = np.column_stack([np.ones(len(rows)), standardised])
    penalty = np.diag([0.0] + [lambda_] * len(keys))  # bias is not penalised
    normal = design.T @ design + penalty
    solution = np.linalg.solve(normal, design.T @ labels)
    scores = design @ solution
    thresholds, band_values = _thresholds_between_classes(scores, labels)
    return {
        "model_class": "ordinal_regression",
        "feature_version": FEATURE_VERSION,
        "regularization": lambda_,
        "feature_keys": keys,
        # The class values the model actually learned: predict() maps the cut
        # index onto these, never onto a hard-coded half-band ladder.
        "band_values": band_values,
        "standardization": {
            "mean": [round(float(v), 8) for v in mean],
            "scale": [round(float(v), 8) for v in scale],
        },
        "bias": round(float(solution[0]), 8),
        "coefficients": {key: round(float(value), 8)
                         for key, value in zip(keys, solution[1:])},
        "thresholds": thresholds,
        "training": {
            "samples": len(rows),
            "speakers": len({row["speaker"] for row in rows}),
            "datasets": sorted({row.get("dataset_id") or "" for row in rows} - {""}),
            "label_source": "examiner_average_or_adjudicated",
        },
    }


def enforce_speaker_disjoint_rows(rows: list[dict],
                                  manifest: dict | None = None) -> list[str]:
    """Fail loudly on split leakage before fitting (or reuse the manifest gate)."""
    if manifest is not None:
        return validate_manifest(manifest)
    seen: dict[str, str] = {}
    violations: list[str] = []
    for row in rows:
        prior = seen.get(row["speaker"], row["split"])
        if prior != row["split"]:
            violations.append(
                f"speaker_leakage:{row['speaker']}:train_and_{row['split']}"
            )
        seen[row["speaker"]] = row["split"]
    return violations


def predict(model: dict, features: dict) -> float | None:
    """Apply the frozen ordinal baseline; None means abstain (never guess)."""
    keys = model["feature_keys"]
    for key in keys:
        value = features.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None
    mean = model["standardization"]["mean"]
    scale = model["standardization"]["scale"]
    standardised = [
        (float(features[key]) - mean[index]) / (scale[index] or 1.0)
        for index, key in enumerate(keys)
    ]
    score = model["bias"] + sum(
        float(coef) * value
        for coef, value in zip(model["coefficients"].values(), standardised)
    )
    cuts = sorted(model["thresholds"])
    index = sum(1 for cut in cuts if score >= cut)
    band_values = model.get("band_values")
    if not band_values or len(band_values) != len(cuts) + 1:
        raise ValueError("model_threshold_band_value_mismatch")
    return float(band_values[min(index, len(band_values) - 1)])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("features", help="feature table JSON (extract_features.py)")
    parser.add_argument("--out", required=True, help="output model JSON")
    parser.add_argument("--lambda", dest="lambda_", type=float, default=1.0)
    args = parser.parse_args(argv)
    try:
        table = json.loads(Path(args.features).read_text(encoding="utf-8"))
        rows = [row for row in table.get("rows") or [] if row.get("split") == "train"]
        violations = enforce_speaker_disjoint_rows(rows)
        if violations:
            for violation in violations:
                print(f"ISSUE {violation}", file=sys.stderr)
            return 1
        model = fit_ordinal(rows, lambda_=args.lambda_)
        Path(args.out).write_text(json.dumps(model, sort_keys=True), encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote model -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
