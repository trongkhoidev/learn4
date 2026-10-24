"""Evaluate the calibrated band model on the frozen test split.

Metrics follow plan §P6: MAE, QWK, bias, within ±0.5, coverage (abstentions
stay in the denominator), slice metrics, and a 95% bootstrap CI clustered by
speaker. Nothing here invents a score for an abstaining row.
"""

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

MAE_GATE = 0.5          # mean absolute error in half-band units
QWK_GATE = 0.75         # quadratic weighted kappa (plan §P6)
WITHIN_HALF_GATE = 0.8  # share of sessions within ±0.5 band
COVERAGE_GATE = 0.95    # share of labelled sessions actually predicted
BIAS_GATE = 0.25        # |bias| in half-band units; CI bound must also pass
SLICE_MIN_N = 5         # slices below this n are reported, not gated

STEP = 0.5  # half-band step


def qwk(predictions: list[float], labels: list[float]) -> float:
    """Quadratic weighted kappa on half-band values.

    QWK = 1 - (observed disagreement) / (expected disagreement), where the
    observed term is the mean per-item squared error and the expected term is
    the chance-agreement expectation over the margin product / ``n**2``.
    Missing either normalisation inflates weak artifacts through the gate.
    """
    n = len(predictions)
    if n == 0 or len(labels) != n:
        return 0.0
    observed = STEP * sum(
        (prediction - label) ** 2
        for prediction, label in zip(predictions, labels)
    ) / n
    pred_dist = Counter(predictions)
    label_dist = Counter(labels)
    expected = STEP * sum(
        count_p * count_l * (predicted - label) ** 2
        for predicted, count_p in pred_dist.items()
        for label, count_l in label_dist.items()
    ) / (n * n)
    if expected == 0.0:  # single band after rounding: undefined, abstain
        return 0.0
    return 1.0 - observed / expected


def core_metrics(rows: list[dict], predictions: list[float | None]) -> dict:
    """Abstentions (``None`` predictions) never leave the denominator."""
    pairs = [
        (float(p), float(row["label"]))
        for row, prediction in zip(rows, predictions)
        if (p := prediction) is not None
    ]
    if not pairs:
        return {"mae": None, "qwk": None, "bias": None, "within_half": None,
                "coverage": 0.0, "n": len(rows)}
    return {
        "mae": sum(abs(p - label) for p, label in pairs) / len(pairs),
        "qwk": qwk([p for p, _ in pairs], [label for _, label in pairs]),
        "bias": sum(p - label for p, label in pairs) / len(pairs),
        "within_half": sum(1 for p, label in pairs if abs(p - label) <= STEP)
        / len(pairs),
        "coverage": len(pairs) / len(rows) if rows else 0.0,
        "n": len(rows),
    }


def slice_metrics(rows: list[dict], predictions: list[float | None]) -> dict:
    """MAE/coverage per recorded slice (region/device/noise/part)."""
    combos: dict[str, list[tuple[float | None, float]]] = {}
    for row, prediction in zip(rows, predictions):
        slicing = row.get("slice") or {}
        parts = sorted(str(slicing.get(key)) or "unknown"
                       for key in ("region", "device", "noise", "part"))
        combos.setdefault("|".join(parts), []).append(
            (prediction, float(row["label"]))
        )
    result: dict[str, dict] = {}
    for name in sorted(combos):
        pairs = combos[name]
        usable = [(p, label) for p, label in pairs if p is not None]
        result[name] = {
            "n": len(pairs),
            "mae": (sum(abs(p - label) for p, label in usable) / len(usable))
            if usable else None,
            "coverage": len(usable) / len(pairs) if pairs else 0.0,
        }
    return result


def _metric_stat(rows: list[dict], predictions: list[float | None]) -> float:
    """MAE of the current sample (the bootstrap statistic)."""
    usable = [(float(p), float(row["label"]))
              for row, prediction in zip(rows, predictions)
              if (p := prediction) is not None]
    if not usable:
        return float("nan")
    return sum(abs(p - label) for p, label in usable) / len(usable)


def _qwk_stat(rows: list[dict], predictions: list[float | None]) -> float:
    pairs = [
        (float(p), float(row["label"])) for row, prediction in zip(rows, predictions)
        if (p := prediction) is not None
    ]
    if not pairs:
        return float("nan")
    return qwk([p for p, _ in pairs], [label for _, label in pairs])


def _summable_stats(rows: list[dict], predictions: list[float | None],
                    field: str) -> float:
    """Point statistic for bias / within_half / coverage."""
    usable = [
        (float(p), float(row["label"]))
        for row, prediction in zip(rows, predictions)
        if (p := prediction) is not None
    ]
    if not usable:
        return float("nan")
    if field == "bias":
        return sum(p - label for p, label in usable) / len(usable)
    if field == "within_half":
        return sum(1 for p, label in usable if abs(p - label) <= STEP) / len(usable)
    return len(usable) / max(1, len(rows))


def speaker_bootstrap_ci(rows: list[dict], predictions: list[float | None], *,
                         seed: int = 20260101, iterations: int = 1000) -> dict:
    """Deterministic 95% CIs clustered by speaker (fixed seed).

    Every gated metric gets a CI, not just MAE: gates take the pessimistic
    bound (upper for lower-is-better, lower for higher-is-better) so that a
    lucky small-sample artifact cannot slip through.
    """
    by_speaker: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        by_speaker.setdefault(str(row["speaker"]), []).append(index)
    usable = any(p is not None for p in predictions)
    if len(by_speaker) < 2 or not usable:
        return {"ci95": {name: (None, None) for name in
                         ("mae", "qwk", "bias", "within_half", "coverage")}}
    speakers = sorted(by_speaker)
    stats = {
        "mae": _metric_stat,
        "qwk": _qwk_stat,
        "bias": lambda r, p: _summable_stats(r, p, "bias"),
        "within_half": lambda r, p: _summable_stats(r, p, "within_half"),
        "coverage": lambda r, p: _summable_stats(r, p, "coverage"),
    }
    rng = random.Random(seed)
    samples: dict[str, list[float]] = {name: [] for name in stats}
    for _ in range(iterations):
        sample: list[int] = []
        for _ in range(len(speakers)):  # resample speakers with replacement
            sample.extend(by_speaker[rng.choice(speakers)])
        sampled_rows = [rows[i] for i in sample]
        sampled_predictions = [predictions[i] for i in sample]
        for name, statistic in stats.items():
            value = statistic(sampled_rows, sampled_predictions)
            if value == value:  # skip NaN samples
                samples[name].append(value)
    result = {}
    for name, values in samples.items():
        if not values:
            result[name] = (None, None)
            continue
        values.sort()
        result[name] = (
            round(values[int(0.025 * len(values))], 4),
            round(values[min(len(values) - 1, int(0.975 * len(values)))], 4),
        )
    return {"ci95": result}


def release_gate(metrics: dict) -> tuple[str, list[str]]:
    """Return (status, failure_reasons); 'passed_release_gate' only when clean.

    Gates take the pessimistic CI bound: upper bound for lower-is-better
    metrics (MAE, |bias|), lower bound for higher-is-better ones (QWK,
    within-half, coverage). A missing CI never passes a gate.
    """
    failures: list[str] = []
    ci = metrics.get("ci95") or {}

    def ci_bound(name: str, *, upper: bool) -> float | None:
        interval = ci.get(name) or ()
        if len(interval) != 2 or interval[0] is None or interval[1] is None:
            return None
        return interval[1] if upper else interval[0]

    # higher-is-better metrics gate on the point value and the CI lower bound;
    # lower-is-better metrics gate on the point value and the CI upper bound.
    checks = {
        "mae": (metrics.get("mae"), ci_bound("mae", upper=True), MAE_GATE,
                "lower_is_better"),
        "qwk": (metrics.get("qwk"), ci_bound("qwk", upper=False), QWK_GATE,
                "higher_is_better"),
        "within_half": (metrics.get("within_half"),
                        ci_bound("within_half", upper=False), WITHIN_HALF_GATE,
                        "higher_is_better"),
        "coverage": (metrics.get("coverage"),
                     ci_bound("coverage", upper=False), COVERAGE_GATE,
                     "higher_is_better"),
    }
    for name, (value, bound, gate, direction) in checks.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            failures.append("metrics_incomplete")
            continue
        if (value < gate if direction == "higher_is_better" else value > gate):
            failures.append(f"{name}_below_gate:{value}({gate})")
        elif bound is None:
            failures.append(f"{name}_ci_missing")
        elif (bound < gate if direction == "higher_is_better" else bound > gate):
            failures.append(f"{name}_ci_bound_below_gate:{bound}({gate})")
    bias_point = metrics.get("bias")
    if not isinstance(bias_point, (int, float)) or isinstance(bias_point, bool):
        failures.append("metrics_incomplete")
    else:
        if abs(bias_point) > BIAS_GATE:
            failures.append(f"bias_above_gate:{bias_point}({BIAS_GATE})")
        else:
            bias_bound = ci_bound("bias", upper=True)
            if bias_bound is None:
                failures.append("bias_ci_missing")
            elif abs(bias_bound) > BIAS_GATE:
                failures.append(f"bias_ci_bound_above_gate:{bias_bound}({BIAS_GATE})")
    for name, slice_stat in sorted((metrics.get("slices") or {}).items()):
        n = slice_stat.get("n") or 0
        mae = slice_stat.get("mae")
        if n >= SLICE_MIN_N and mae is not None and mae > MAE_GATE:
            failures.append(f"slice_below_gate:{name}:{mae}")
    if not failures:
        return "passed_release_gate", []
    return "failed_release_gate", failures


def evaluate(rows: list[dict], predictions: list[float | None]) -> dict:
    metrics = core_metrics(rows, predictions)
    metrics["ci95"] = speaker_bootstrap_ci(rows, predictions)["ci95"]
    metrics["slices"] = slice_metrics(rows, predictions)
    gate_status, gate_failures = release_gate(metrics)
    metrics["status"] = gate_status
    if gate_failures:
        metrics["gate_failures"] = gate_failures
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("features", help="feature table JSON (extract_features.py)")
    parser.add_argument("--model", required=True, help="model JSON (train_baseline.py)")
    parser.add_argument("--out", required=True, help="output metrics JSON")
    args = parser.parse_args(argv)
    try:
        table = json.loads(Path(args.features).read_text(encoding="utf-8"))
        model = json.loads(Path(args.model).read_text(encoding="utf-8"))
        from app.modules.speaking.pronunciation.policy import FEATURE_VERSION

        if model.get("feature_version") != FEATURE_VERSION:
            print("error: model_feature_version_mismatch", file=sys.stderr)
            return 1
        rows = table.get("rows") or []
        test_rows = [row for row in rows if row.get("split") == "test"]
        # model.feature_key incompatibilities surface as abstentions (None):
        predictions = [predict_row(model, row["features"]) for row in test_rows]
        metrics = evaluate(test_rows, predictions)
        Path(args.out).write_text(json.dumps(metrics, sort_keys=True, indent=2),
                                  encoding="utf-8")
        print(f"status: {metrics['status']}")
        print(json.dumps({k: metrics[k] for k in
                          ("mae", "qwk", "bias", "within_half", "coverage")},
                         indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def predict_row(model: dict, features: dict) -> float | None:
    from .train_baseline import predict

    return predict(model, features)


if __name__ == "__main__":
    sys.exit(main())