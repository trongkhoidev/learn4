"""Export the inference artifact after the release gate has actually passed.

This is the hard fail-closed boundary into production: an artifact can only be
exported when the evaluation report carries ``passed_release_gate``. The
exporter refuses to write anything otherwise, then round-trips the result
through the runtime loader (``app/.../calibration.py``) so a bad artifact can
never reach the engine.
"""

import argparse
import json
import sys
from pathlib import Path

from app.modules.speaking.pronunciation.calibration import (
    SCHEMA_VERSION,
    checksum_text,
    load_calibration_artifact,
)
from app.modules.speaking.pronunciation.policy import ENGINE_VERSION

from .evaluate import release_gate


def build_artifact(model: dict, metrics: dict,
                   calibration_version: str,
                   *, artifact_id: str, feature_rows: list[dict]) -> dict:
    """Assemble the artifact dict; refuse export on any gate failure.

    The exporter does not trust ``metrics.status``: it re-derives the gate
    decision from the metric fields, and additionally requires the stored
    status to agree with that recomputation (no hand-edited status allowed).
    """
    if not isinstance(metrics.get("mae"), (int, float)) \
            or isinstance(metrics.get("mae"), bool):
        raise ValueError("export_refused_metrics_missing_mae")
    computed_status, failures = release_gate(metrics)
    if computed_status != "passed_release_gate":
        raise ValueError(
            f"export_refused_release_gate_not_passed:{computed_status}:"
            + ";".join(failures)
        )
    if metrics.get("status") != "passed_release_gate":
        raise ValueError("export_refused_status_inconsistent_with_metrics")
    if not calibration_version or calibration_version == "uncalibrated":
        raise ValueError("export_refused_uncalibrated_version")
    if not model.get("coefficients") or not model.get("thresholds"):
        raise ValueError("export_refused_model_incomplete")
    speakers = sorted({str(row["speaker"]) for row in feature_rows})
    training = model.get("training") or {}
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "engine_version": ENGINE_VERSION,
        "feature_version": model.get("feature_version"),
        "calibration_version": calibration_version,
        "model_class": model.get("model_class"),
        "coefficients": model.get("coefficients"),
        "bias": model.get("bias"),
        # Runtime scoring needs the exact standardization the fit used, plus
        # the learned band ladder: predicted bands must match fitted classes.
        "standardization": model.get("standardization"),
        "band_values": model.get("band_values"),
        "thresholds": model.get("thresholds"),
        "training": {
            "dataset_ids": training.get("datasets") or [],
            "samples": metrics.get("n") or training.get("samples"),
            "speakers": len({row["speaker"] for row in feature_rows}),
            "speaker_ids_hash": checksum_text(",".join(speakers)),
            "slices": metrics.get("slices") or {},
        },
        "metrics": {
            "status": metrics.get("status"),
            "mae": metrics.get("mae"),
            "qwk": metrics.get("qwk"),
            "bias": metrics.get("bias"),
            "within_half": metrics.get("within_half"),
            "coverage": metrics.get("coverage"),
            "ci95": metrics.get("ci95"),
        },
    }
    artifact["checksums"] = {"artifact": artifact_checksum(artifact)}
    return artifact


def artifact_checksum(artifact: dict) -> str:
    """Same blanking rule as the runtime loader in calibration.py."""
    body = {**artifact, "checksums": {"artifact": ""}}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True)
    return checksum_text(canonical)


def export(model_path: str, metrics_path: str, out_path: str,
           calibration_version: str, *, artifact_id: str,
           feature_table_path: str | None = None) -> dict:
    model = json.loads(Path(model_path).read_text(encoding="utf-8"))
    metrics = json.loads(Path(metrics_path).read_text(encoding="utf-8"))
    rows: list[dict] = []
    if feature_table_path:
        table = json.loads(Path(feature_table_path).read_text(encoding="utf-8"))
        rows = table.get("rows") or []
    artifact = build_artifact(model, metrics, calibration_version,
                              artifact_id=artifact_id, feature_rows=rows)
    Path(out_path).write_text(json.dumps(artifact, sort_keys=True, indent=2),
                              encoding="utf-8")
    # Round-trip through the runtime loader: nothing ships until it loads clean.
    loaded = load_calibration_artifact(out_path)
    if loaded is None:
        raise ValueError("export_refused_runtime_loader_returned_none")
    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--calibration-version", required=True,
                        help='e.g. "examiner-cal-2026-01"; "uncalibrated" refused')
    parser.add_argument("--artifact-id", default=None)
    parser.add_argument("--feature-table", default=None)
    args = parser.parse_args(argv)
    try:
        artifact_id = args.artifact_id or args.calibration_version
        artifact = export(
            args.model, args.metrics, args.out, args.calibration_version,
            artifact_id=artifact_id, feature_table_path=args.feature_table,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"artifact exported: {artifact['artifact_id']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
