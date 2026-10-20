from scripts.calibration.evaluate import (
    evaluate, examiner_truth, half_band, metric_block, quadratic_weighted_kappa,
    speaker_split, validate_rows,
)


def test_half_band_and_examiner_truth():
    assert half_band(6.25) == 6.5
    ratings = [{"fluency": 6.0}, {"fluency": 6.5}]
    assert examiner_truth(ratings, "fluency") == 6.5


def test_perfect_metrics():
    pairs = [(5.0, 5.0), (6.5, 6.5), (8.0, 8.0)]
    block = metric_block(pairs)
    assert block["mae"] == 0
    assert block["qwk"] == 1.0
    assert block["within_half"] == 1.0


def test_kappa_degrades_for_reversed_predictions():
    truth = [4.0, 5.0, 6.0, 7.0, 8.0]
    assert quadratic_weighted_kappa(truth, truth) == 1.0
    assert quadratic_weighted_kappa(truth, list(reversed(truth))) < 0.0


def test_speaker_split_is_stable():
    assert speaker_split("speaker-42") == speaker_split("speaker-42")


def _calibration_row(sample, speaker, split="test", pronun=None):
    ratings = [
        {"examiner_id": "e1", "prediction_hidden": True, "fluency": 6.0, "vocab": 6.0,
         "grammar": 6.0, "pronun": 6.0, "overall": 6.0},
        {"examiner_id": "e2", "prediction_hidden": True, "fluency": 6.5, "vocab": 6.5,
         "grammar": 6.0, "pronun": 6.0, "overall": 6.0},
    ]
    return {
        "sample_id": sample,
        "speaker_id": speaker,
        "session_id": f"session-{sample}",
        "split": split,
        "human_ratings": ratings,
        "prediction": {
            "fluency": {"status": "scored", "band": 6.5},
            "vocab": {"status": "scored", "band": 6.0},
            "grammar": {"status": "scored", "band": 6.0},
            "pronun": {"status": "scored", "band": 6.0} if pronun is None else pronun,
            "overall": {"status": "insufficient_evidence", "band": None},
        },
        "human_audited_claims": [{"confirmed_by_audio": True, "fabricated_quote": False}],
        "metadata": {"device": "phone", "noise": "quiet", "region": "south", "accent": "vi"},
    }


def test_evaluator_keeps_abstentions_in_coverage_and_bootstraps_speakers():
    rows = [
        _calibration_row("s1", "p1"),
        _calibration_row("s2", "p2", pronun={"status": "insufficient_evidence", "band": None}),
    ]
    assert validate_rows(rows) == []
    report = evaluate(rows, split="test", min_speakers=2, bootstrap_samples=50)
    assert report["data_quality"]["unique_speakers"] == 2
    assert report["coverage"]["pronun"] == {"eligible": 2, "scored": 1, "abstained": 1, "rate": 0.5}
    assert report["speaker_bootstrap_95_ci"]["fluency"]["mae_95_ci"] is not None
    assert "accent=vi" in report["slices"]
    assert report["release_gates"]["all_pass"] is False


def test_evaluator_rejects_speaker_leakage_and_unblinded_examiners():
    first = _calibration_row("s1", "p1", split="train")
    second = _calibration_row("s2", "p1", split="test")
    second["human_ratings"][0]["prediction_hidden"] = False
    errors = validate_rows([first, second])
    assert any("speaker_id" in error and "leaks across splits" in error for error in errors)
    assert any("prediction_hidden=true" in error for error in errors)
