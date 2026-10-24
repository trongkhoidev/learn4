"""Phone-posterior model seam.

The production adapter is **blocked** (see
``docs/research/pronunciation-phone-model-decision-note.md``): no verified
open-weight model with cached weights, confirmed license and a benchmark run
exists yet. Tests use ``FrozenPhoneModel`` with deterministic arrays, so no
unit test downloads or requires a model.
"""

import json
from pathlib import Path
from typing import Protocol

from app.core.config import settings

MODEL_KIND = "phone-posterior-frames"


class PhoneModelUnavailable(RuntimeError):
    """Raised when the configured phone model cannot be loaded — fail closed."""


class PhonePosteriorModel(Protocol):
    name: str
    version: str
    license: str

    def posterior_frames(self, audio_path: str) -> list[dict]:
        """Return ``list[frame -> dict[phone, probability]]`` for 16 kHz PCM."""
        ...


class FrozenPhoneModel:
    """Deterministic development/test model built from supplied frames."""

    def __init__(self, frames: list[dict], *, name: str = "frozen-phone-model",
                 version: str = "frozen-v0", license: str = "test-fixture",
                 sample_rate: int = 16000, hop_s: float = 0.02):
        self.frames = frames
        self.name = name
        self.version = version
        self.license = license
        self.sample_rate = sample_rate
        self.hop_s = hop_s

    def posterior_frames(self, audio_path: str) -> list[dict]:
        return self.frames

    def frame_time(self, index: int) -> float:
        return index * self.hop_s


class ManifestPhoneModel:
    """Adapter behind an explicit artifact manifest; fails closed when absent.

    Loading real weights requires: package present, manifest with
    schema/revision/checksum/license verified, and a benchmark run recorded.
    Until then this adapter raises ``PhoneModelUnavailable``.
    """

    def __init__(self, manifest_path: str | None = None):
        self.manifest_path = manifest_path or settings.pronunciation_phone_model_manifest
        if not self.manifest_path:
            raise PhoneModelUnavailable("pronunciation_phone_model_manifest_not_configured")
        try:
            self.manifest = json.loads(Path(self.manifest_path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise PhoneModelUnavailable(f"phone_model_manifest_unreadable: {exc}") from exc
        if self.manifest.get("model_kind") != MODEL_KIND:
            raise PhoneModelUnavailable("phone_model_manifest_kind_mismatch")
        for field in ("model_id", "revision", "sha256", "license", "phone_inventory"):
            if not self.manifest.get(field):
                raise PhoneModelUnavailable(f"phone_model_manifest_missing_{field}")
        weights = Path(self.manifest.get("weights_path", ""))
        if not weights.is_file():
            raise PhoneModelUnavailable("phone_model_weights_not_cached_locally")
        try:
            import hashlib

            digest = hashlib.sha256()
            with weights.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
            if digest.hexdigest() != self.manifest["sha256"]:
                raise PhoneModelUnavailable("phone_model_weights_checksum_mismatch")
        except OSError as exc:
            raise PhoneModelUnavailable(f"phone_model_weights_unreadable: {exc}") from exc
        # Real inference needs transformers/torch native deps. Intentionally not
        # imported until the benchmark approves the model (decision note).
        self.name = self.manifest["model_id"]
        self.version = self.manifest["revision"]
        self.license = self.manifest["license"]

    def posterior_frames(self, audio_path: str) -> list[dict]:
        raise PhoneModelUnavailable("phone_model_inference_blocked_pending_benchmark")


def get_phone_model() -> PhonePosteriorModel:
    """Resolve the configured model; raise when unavailable (fail closed)."""
    if settings.pronunciation_phone_model != "manifest":
        raise PhoneModelUnavailable("phone_model_not_configured")
    return ManifestPhoneModel()
