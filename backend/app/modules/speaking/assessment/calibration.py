"""Optional monotonic band calibration fitted from hidden examiner ratings."""

import json
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


@lru_cache(maxsize=4)
def _load(path: str) -> dict:
    if not path:
        return {}
    try:
        artifact = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if artifact.get("schema_version") != "speaking-band-calibration-v1":
        return {}
    return artifact


def calibrate_band(criterion: str, band: float | None) -> tuple[float | None, dict]:
    """Interpolate a monotonic calibration curve; preserve half-band output."""
    if band is None:
        return None, {"applied": False}
    artifact = _load(settings.speaking_band_calibration_path)
    block = (artifact.get("criteria") or {}).get(criterion) or {}
    knots = block.get("knots") or []
    if len(knots) < 2:
        return band, {"applied": False}
    value = float(band)
    if value <= knots[0]["input"]:
        calibrated = knots[0]["output"]
    elif value >= knots[-1]["input"]:
        calibrated = knots[-1]["output"]
    else:
        calibrated = value
        for left, right in zip(knots, knots[1:]):
            if left["input"] <= value <= right["input"]:
                width = right["input"] - left["input"]
                fraction = (value - left["input"]) / width if width else 0.0
                calibrated = left["output"] + fraction * (right["output"] - left["output"])
                break
    calibrated = max(0.0, min(9.0, round(float(calibrated) * 2) / 2))
    return calibrated, {
        "applied": True,
        "version": artifact.get("version"),
        "raw_band": value,
        "training_samples": block.get("samples"),
        "training_speakers": block.get("speakers"),
    }
