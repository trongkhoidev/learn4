"""Evidence and eligibility policy for pronunciation conclusions.

Invariants enforced here (docs/plans/pronunciation-engine-implementation-plan.md §3):

- E1 (ASR confidence/disagreement) only selects "listen again" regions. It is
  never a pronunciation score.
- E2 (forced alignment) only positions word/phone evidence in time.
- E3 (phone posterior/GOP, prosody) produces candidate observations only.
- E5 (band) requires a calibrated, examiner-rated artifact that passes every
  gate below. Anything else means ``band=None`` / ``status != scored``.
"""

from app.core.config import settings

ENGINE_VERSION = "pronunciation-engine-v1"
FEATURE_VERSION = "pronunciation-features-v1"

# Band sources that a persisted result may keep. Only sources produced by an
# examiner-calibrated artifact through this engine belong here. The engine is
# the single writer of CALIBRATED_BAND_SOURCE and only emits it after the
# loaded artifact passed every release gate (the artifact loader fails closed
# otherwise), so the source string is a fleet-wide marker of a validated
# artifact — no legacy result could legitimately carry it.
CALIBRATED_BAND_SOURCE = "examiner_calibrated_artifact"
TRUSTED_BAND_SOURCES: frozenset[str] = frozenset({CALIBRATED_BAND_SOURCE})

UNTRUSTED_LEGACY_SOURCES = frozenset({
    "asr_confidence",
    "llm_only_pending_alignment",
    "acoustic_confidence_and_prosody_calibration",
    "session_acoustic_and_prosody_calibration",
    "descriptor_judgement_with_acoustic_support",
})

BAND_SOURCE_UNAVAILABLE = "unavailable_no_validated_pronunciation_model"
BAND_SOURCE_UNTRUSTED_REMOVED = "legacy_untrusted_pronunciation_band_removed"
REASON_NO_VALIDATED_ENGINE = (
    "No validated pronunciation-to-band or phoneme-error engine is available."
)

APPROX_G2P_STATUS = "approx_rule_based"
LEXICON_RESOLVED_STATUS = "resolved"
LEXICON_UNRESOLVED_STATUS = "unresolved"


def is_trusted_pronunciation_band_source(source: str | None) -> bool:
    """A band may survive only when its source passed the release gate."""
    return bool(source) and source in TRUSTED_BAND_SOURCES


def mode() -> str:
    value = (settings.pronunciation_mode or "disabled").lower()
    if value not in {"disabled", "shadow", "enabled"}:
        return "disabled"
    return value


def engine_enabled() -> bool:
    return mode() == "enabled"


def band_eligibility(artifact: dict | None) -> tuple[bool, str | None]:
    """Return (eligible, reason) for turning features into a band.

    Fail closed: every missing or mismatched condition has a distinct reason.
    """
    if not artifact:
        return False, "calibration_artifact_missing"
    if artifact.get("schema_version") != "pronunciation-artifact-v1":
        return False, "calibration_artifact_schema_mismatch"
    version = artifact.get("calibration_version")
    if not version or version == "uncalibrated":
        return False, "calibration_artifact_uncalibrated"
    if artifact.get("feature_version") != FEATURE_VERSION:
        return False, "calibration_artifact_feature_version_mismatch"
    if artifact.get("engine_version") != ENGINE_VERSION:
        return False, "calibration_artifact_engine_version_mismatch"
    if not artifact.get("checksums"):
        return False, "calibration_artifact_checksum_missing"
    metrics = artifact.get("metrics") or {}
    if metrics.get("status") != "passed_release_gate":
        return False, "calibration_artifact_release_gate_not_passed"
    return True, None
