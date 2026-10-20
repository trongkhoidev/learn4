import json

import pytest

from app.modules.speaking.assessment import calibration
from scripts.calibration.fit_band_calibration import fit


def _row(index, prediction, human, *, speaker=None):
    return {
        "sample_id": f"s{index}",
        "speaker_id": speaker or f"p{index}",
        "split": "train",
        "prediction": {
            "fluency": {"band": prediction},
            "vocab": {"band": prediction},
            "grammar": {"band": prediction},
        },
        "human_ratings": [
            {"examiner_id": "e1", "prediction_hidden": True,
             "fluency": human, "vocab": human, "grammar": human},
            {"examiner_id": "e2", "prediction_hidden": True,
             "fluency": human, "vocab": human, "grammar": human},
        ],
    }


def test_fitter_produces_monotonic_curves_and_runtime_applies_them(tmp_path, monkeypatch):
    rows = [_row(1, 5.0, 6.0), _row(2, 6.0, 5.5), _row(3, 7.0, 7.5)]
    artifact = fit(rows, min_samples=3, min_speakers=3, version="test-cal")
    knots = artifact["criteria"]["fluency_coherence"]["knots"]
    assert [knot["output"] for knot in knots] == [5.75, 5.75, 7.5]

    path = tmp_path / "calibration.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")
    monkeypatch.setattr(calibration.settings, "speaking_band_calibration_path", str(path))
    calibration._load.cache_clear()
    band, metadata = calibration.calibrate_band("fluency_coherence", 5.5)
    assert band == 6.0
    assert metadata == {
        "applied": True, "version": "test-cal", "raw_band": 5.5,
        "training_samples": 3, "training_speakers": 3,
    }


def test_fitter_rejects_small_or_unblinded_data():
    with pytest.raises(ValueError, match="at least 3 train samples"):
        fit([_row(1, 6.0, 6.0)], min_samples=3, min_speakers=1)
    rows = [_row(i, 6.0, 6.0) for i in range(1, 4)]
    rows[0]["human_ratings"][0]["prediction_hidden"] = False
    with pytest.raises(ValueError, match="examiner saw model prediction"):
        fit(rows, min_samples=3, min_speakers=3)


def test_runtime_preserves_raw_band_without_artifact(monkeypatch):
    monkeypatch.setattr(calibration.settings, "speaking_band_calibration_path", "")
    calibration._load.cache_clear()
    assert calibration.calibrate_band("lexical_resource", 6.5) == (6.5, {"applied": False})
