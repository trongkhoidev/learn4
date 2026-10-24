"""Math and gate tests for the band evaluation (plan §P6).

Targets the reviewer findings: learned-band mapping, QWK normalisation, CI
enforcement and slice gates.
"""

import pytest

from scripts.pronunciation.evaluate import (
    BIAS_GATE,
    COVERAGE_GATE,
    QWK_GATE,
    core_metrics,
    evaluate,
    qwk,
    release_gate,
    slice_metrics,
    speaker_bootstrap_ci,
)
from scripts.pronunciation.train_baseline import fit_ordinal, predict


# --- QWK ----------------------------------------------------------------------

def test_qwk_perfect_agreement_is_one():
    assert qwk([5.0, 6.0, 7.0], [5.0, 6.0, 7.0]) == pytest.approx(1.0)


def test_qwk_perfect_reversal_is_minus_one():
    # Two samples with swapped labels must be -1.0, not 0.0.
    assert qwk([7.0, 5.0], [5.0, 7.0]) == pytest.approx(-1.0)


def test_qwk_random_agreement_is_zero():
    # Classic 2x2 case: predictions independent of labels -> 0.
    predictions = [5.0, 5.0, 7.0, 7.0]
    labels = [5.0, 7.0, 5.0, 7.0]
    assert qwk(predictions, labels) == pytest.approx(0.0, abs=1e-9)


# --- learned band mapping (blocker V1 regression) -----------------------------

def _rows(speakers: int = 6) -> list[dict]:
    """Three actual classes 5.0/6.0/7.0 correlated with one feature."""
    rows = []
    for index in range(speakers * 3):
        speaker = f"sp{index % speakers}"
        features = {"pitch_range_st": float(index)}
        label = 5.0 + (index // speakers)
        rows.append({
            "session_id": f"s{index}", "speaker": speaker,
            "dataset_id": "learn4-pilot-1",
            "split": "test" if index % speakers == 0 else "train",
            "features": features, "label": label,
        })
    return rows


def test_fit_and_predict_map_onto_learned_classes_not_the_default_ladder():
    rows = [r for r in _rows() if r["split"] != "test"]
    model = fit_ordinal(rows)
    assert model["band_values"] == [5.0, 6.0, 7.0]
    # probe points inside each learned class must read back that class,
    # never 0 / 4.0 / 4.5 from the old hard-coded ladder.
    feature_probe = {"pitch_range_st": rows[0]["features"]["pitch_range_st"] + 0.01}
    assert predict(model, feature_probe) == 5.0
    middle = rows[len(rows) // 3]["features"]["pitch_range_st"] + 0.01
    assert predict(model, {"pitch_range_st": middle}) == 6.0
    top = rows[2 * (len(rows) // 3)]["features"]["pitch_range_st"] + 0.01
    assert predict(model, {"pitch_range_st": top}) == 7.0


def test_predict_uses_threshold_cuts_of_a_hand_model():
    model = {
        "feature_keys": ["pitch_range_st"],
        "standardization": {"mean": [0.0], "scale": [1.0]},
        "bias": 0.0,
        "coefficients": {"pitch_range_st": 1.0},
        "thresholds": [0.5, 1.5],
        "band_values": [5.0, 6.0, 7.0],
    }
    assert predict(model, {"pitch_range_st": 0.4}) == 5.0
    assert predict(model, {"pitch_range_st": 0.6}) == 6.0
    assert predict(model, {"pitch_range_st": 1.6}) == 7.0


def test_predict_refuses_model_with_ladder_mismatch():
    model = {
        "feature_keys": ["pitch_range_st"],
        "standardization": {"mean": [0.0], "scale": [1.0]},
        "bias": 0.0,
        "coefficients": {"pitch_range_st": 1.0},
        "thresholds": [0.5, 1.5],
        "band_values": [5.0, 6.0],  # length mismatch -> refuse, never guess
    }
    with pytest.raises(ValueError):
        predict(model, {"pitch_range_st": 0.6})


def test_predict_abstains_on_missing_feature():
    model = fit_ordinal(_rows()[:30])
    assert predict(model, {"unrelated": 1.2}) is None


# --- gates --------------------------------------------------------------------

def _passing_metrics() -> dict:
    return {
        "mae": 0.35, "qwk": 0.8, "bias": 0.02, "within_half": 0.85,
        "coverage": 1.0, "n": 40, "slices": {},
        "ci95": {"mae": (0.3, 0.4), "qwk": (0.78, 0.82), "bias": (0.0, 0.05),
                 "within_half": (0.82, 0.88), "coverage": (1.0, 1.0)},
    }


def test_release_gate_passes_clean_metrics_with_ci():
    status, failures = release_gate(_passing_metrics())
    assert (status, failures) == ("passed_release_gate", [])


def test_qwk_gate_follows_plan_075():
    assert QWK_GATE == 0.75
    metrics = _passing_metrics()
    metrics["qwk"] = 0.7  # plan threshold, not 0.7-with-forgiving-formula
    metrics["ci95"]["qwk"] = (0.72, 0.72)
    status, failures = release_gate(metrics)
    assert status == "failed_release_gate"
    assert any("qwk_below_gate" in f for f in failures)


def test_gate_enforces_ci_lower_bound_not_only_point_estimate():
    metrics = _passing_metrics()
    metrics["qwk"] = 0.8  # point passes ...
    metrics["ci95"]["qwk"] = (0.5, 0.9)  # ... but the CI straddles the gate
    status, failures = release_gate(metrics)
    assert status == "failed_release_gate"
    assert any("qwk_ci_bound_below_gate" in f for f in failures)


def test_gate_fails_when_a_ci_is_missing():
    metrics = _passing_metrics()
    metrics["ci95"] = {k: v for k, v in metrics["ci95"].items() if k != "coverage"}
    status, failures = release_gate(metrics)
    assert status == "failed_release_gate"
    assert any("coverage_ci_missing" in f for f in failures)


def test_bias_ci_bound_gates_too():
    metrics = _passing_metrics()
    metrics["bias"] = 0.1
    metrics["ci95"]["bias"] = (0.0, 0.4)  # upper bound over the 0.25 gate
    status, failures = release_gate(metrics)
    assert any("bias_ci_bound_above_gate" in f for f in failures)
    assert status == "failed_release_gate"
    assert abs(BIAS_GATE) == 0.25
    assert COVERAGE_GATE == 0.95


def test_slice_gate_uses_recorded_slices_and_ignores_small_n():
    metrics = _passing_metrics()
    metrics["slices"] = {
        "north|phone|low|Part 1": {"n": 12, "mae": 0.9},
        "south|studio|silent|Part 3": {"n": 3, "mae": 3.0},  # too small to gate
    }
    status, failures = release_gate(metrics)
    assert status == "failed_release_gate"
    assert any("slice_below_gate:north|phone|low|Part 1" in f for f in failures)
    assert not any("Part 3" in f for f in failures)


def test_slice_metrics_key_includes_part_and_region():
    rows = [{"label": 5.0, "slice": {"region": "north", "device": "phone",
                                     "noise": "low", "part": "Part 2"}}]
    out = slice_metrics(rows, [5.0])
    assert list(out) == ["Part 2|low|north|phone"]  # sorted offset keys
    assert out["Part 2|low|north|phone"]["mae"] == 0.0


# --- deterministic CI ---------------------------------------------------------

def test_bootstrap_ci_is_deterministic_and_clustered_by_speaker():
    rows = []
    predictions = []
    for speaker_index, speaker in enumerate(("a", "b", "c", "d")):
        for offset in range(10):
            label = 5.0 + offset * 0.1
            rows.append({"speaker": speaker, "label": label})
            predictions.append(label + (0.2 if speaker_index % 2 else 0.0))
    first = speaker_bootstrap_ci(rows, predictions, iterations=100)
    second = speaker_bootstrap_ci(rows, predictions, iterations=100)
    assert first["ci95"] == second["ci95"]
    mae_low, mae_high = first["ci95"]["mae"]
    point = core_metrics(rows, predictions)["mae"]
    assert mae_low <= point <= mae_high


def test_evaluate_flags_failed_gate_in_status_and_reasons():
    rows = [{"speaker": "a", "label": 5.0, "slice": {}},
            {"speaker": "b", "label": 7.0, "slice": {}}]
    metrics = evaluate(rows, [7.0, 7.0])
    assert metrics["status"] == "failed_release_gate"
    assert metrics["gate_failures"]


def test_coverage_counts_abstentions_in_the_denominator():
    rows = [{"speaker": "a", "label": 5.0}, {"speaker": "b", "label": 5.0}]
    metrics = core_metrics(rows, [None, 5.0])
    assert metrics["coverage"] == 0.5
