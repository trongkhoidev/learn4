from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_ENV_FILE, extra="ignore")

    teacher_access_code: str = "changeme"
    database_url: str = "sqlite:///./lexilearn.db"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "lexilearn"
    r2_public_url: str = ""

    groq_api_key: str = ""
    groq_stt_model: str = "whisper-large-v3-turbo"
    groq_model_70b: str = "openai/gpt-oss-120b"
    groq_model_8b: str = "gpt-oss-20b"
    groq_writing_model: str = "openai/gpt-oss-120b"
    groq_ocr_model: str = "qwen/qwen3.6-27b"

    google_api_key: str = ""
    llm_provider: str = "groq" # 'groq', 'gemini', or 'mock'
    gemini_model: str = "gemini-3.5-flash-lite"

    deepgram_api_key: str = ""
    deepgram_stt_model: str = "nova-3"
    elevenlabs_api_key: str = ""
    elevenlabs_stt_model: str = "scribe_v2"
    cloudflare_worker_url: str = ""
    cloudflare_worker_token: str = ""
    cloudflare_stt_model: str = "@cf/openai/whisper-large-v3-turbo"

    tier_exam: str = "70b,70b,70b"
    tier_practice: str = "70b,70b,70b"
    tier_budget: str = "8b,8b,8b"

    whisper_model: str = "turbo"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_preload: bool = False
    whisper_cpu_threads: int = Field(default=4, ge=1)
    stt_latency_profile: Literal["fast", "balanced"] = "fast"
    whisper_fast_beam_size: int = Field(default=3, ge=1, le=5)
    stt_provider: Literal[
        "selfhost", "groq", "deepgram", "elevenlabs", "cloudflare", "ensemble", "auto", "mock",
    ] = "selfhost"
    # Ordered tie-break priority for the transcript medoid. Providers without
    # credentials are skipped, so this can be enabled before every key is set.
    stt_ensemble_providers: str = "deepgram,elevenlabs,selfhost"
    stt_ensemble_min_providers: int = Field(default=2, ge=1, le=5)
    stt_local_wait_seconds: float = Field(default=30.0, ge=0, allow_inf_nan=False)
    stt_remote_timeout_seconds: float = Field(default=60.0, gt=0, allow_inf_nan=False)
    audio_process_timeout_seconds: float = Field(default=60.0, gt=0, allow_inf_nan=False)

    audio_retention_days: int = 90
    speaking_job_orphan_hours: int = 24
    max_audio_seconds: int = 600
    max_audio_bytes: int = 25 * 1024 * 1024
    speaking_job_max_attempts: int = 2
    speaking_job_poll_seconds: float = 0.5
    speaking_async_default: bool = False
    scoring_version: str = "ielts-evidence-ensemble-v4"
    stt_profile_version: str = "multi-asr-fast-en-v2"
    calibration_version: str = "uncalibrated"
    speaking_band_calibration_path: str = ""
    # Conservative review gates; these are heuristic triggers, not probabilities.
    speaking_review_hallucination_threshold: float = 0.75
    speaking_review_agreement_threshold: float = 0.65
    pronunciation_aligner: str = "none"  # none | whisperx | mfa
    pronunciation_alignment_device: str = "cpu"
    mfa_dictionary_path: str = ""
    mfa_acoustic_model_path: str = ""
    daily_submit_limit_per_student: int = 40
    monthly_spend_cap_usd: float = 130.0

    storage_dir: str = "./storage"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def tiers(self) -> dict[str, tuple[str, str, str]]:
        def parse(s: str) -> tuple[str, str, str]:
            parts = s.split(",")
            return (parts[0], parts[1], parts[2])

        return {
            "exam": parse(self.tier_exam),
            "practice": parse(self.tier_practice),
            "budget": parse(self.tier_budget),
        }

    @property
    def stt_ensemble_provider_list(self) -> list[str]:
        allowed = {"selfhost", "groq", "deepgram", "elevenlabs", "cloudflare"}
        return list(dict.fromkeys(
            provider.strip().lower()
            for provider in self.stt_ensemble_providers.split(",")
            if provider.strip().lower() in allowed
        ))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
