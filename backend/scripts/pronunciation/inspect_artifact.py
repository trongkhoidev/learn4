"""Validate an exported inference artifact through the runtime loader.

Reads an artifact JSON and round-trips it through the runtime loader, printing
a redacted summary (no secrets, no PII). Eligibility is derived from the
runtime policy — the inspect tool never trusts the artifact's self-reported
metrics alone.
"""

import argparse
import json
import sys
from pathlib import Path

from app.modules.speaking.pronunciation.calibration import (
    ArtifactInvalid,
    checksum_text,
    load_calibration_artifact,
)


def summarize(path: str) -> dict:
    """Return a validation report given the artifact as path."""
    try:
        json.loads(Path(path).read_text(encoding="utf-8"))  # fast malformed check
    except (OSError, ValueError) as exc:
        return {"path": path, "valid": False, "reason": f"artifact unreadable: {exc}"}
    try:
        artifact = load_calibration_artifact(path)
    except ArtifactInvalid as exc:
        return {"path": path, "valid": False, "reason": str(exc)}
    if artifact is None:
        return {"path": path, "valid": False, "reason": "no_artifact"}
    metrics = artifact.get("metrics") or {}
    return {
        "path": path,
        "valid": True,
        "summarized": {
            "artifact_id": artifact.get("artifact_id"),
            "calibration_version": artifact.get("calibration_version"),
            "feature_version": artifact.get("feature_version"),
            "model_class": artifact.get("model_class"),
            "n_thresholds": len(artifact.get("thresholds") or []),
            "metrics": {key: metrics.get(key) for key in
                        ("status", "mae", "qwk", "bias", "within_half", "coverage")},
            # identity fingerprint lets a human confirm which artifact will load
            "fingerprint": checksum_text(json.dumps(artifact, sort_keys=True,
                                                    separators=(",", ":"))[:2048]),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", help="artifact JSON path")
    args = parser.parse_args(argv)
    try:
        report = summarize(args.artifact)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
