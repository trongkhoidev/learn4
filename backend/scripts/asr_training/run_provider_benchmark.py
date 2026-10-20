"""Generate frozen ASR predictions for provider-to-provider evaluation."""

import argparse
import json
import time
from pathlib import Path

from app.integrations.audio.processor import probe_audio_duration
from app.integrations.stt.recognition import (
    transcribe_deepgram_cloud,
    transcribe_elevenlabs_cloud,
    transcribe_groq,
    transcribe_selfhost,
)


PROVIDERS = {
    "selfhost": transcribe_selfhost,
    "groq": transcribe_groq,
    "deepgram": transcribe_deepgram_cloud,
    "elevenlabs": transcribe_elevenlabs_cloud,
}


def _read_jsonl(path):
    rows = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_number}: {exc}") from exc
    return rows


def run(manifest_path: Path, output_dir: Path, providers: list[str]):
    rows = _read_jsonl(manifest_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    handles = {provider: (output_dir / f"{provider}.jsonl").open("w") for provider in providers}
    try:
        for row in rows:
            audio_path = Path(row["audio_path"])
            if not audio_path.is_absolute():
                audio_path = manifest_path.parent / audio_path
            keyterms = (row.get("metadata") or {}).get("keyterms") or []
            duration = probe_audio_duration(str(audio_path))
            for provider in providers:
                started = time.perf_counter()
                prediction, error = {}, None
                try:
                    prediction = PROVIDERS[provider](str(audio_path), keyterms=keyterms)
                except Exception as exc:
                    error = f"{type(exc).__name__}: {str(exc)[:300]}"
                output = {
                    **row,
                    "prediction": prediction.get("text", ""),
                    "predicted_words": prediction.get("words", []),
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "audio_duration_s": duration,
                    "provider": provider,
                    "provider_model": prediction.get("model"),
                    "provider_error": error,
                }
                handles[provider].write(json.dumps(output, ensure_ascii=False) + "\n")
                handles[provider].flush()
    finally:
        for handle in handles.values():
            handle.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--providers", default="selfhost,deepgram,elevenlabs")
    args = parser.parse_args()
    providers = list(dict.fromkeys(part.strip() for part in args.providers.split(",") if part.strip()))
    unknown = sorted(set(providers) - set(PROVIDERS))
    if unknown:
        parser.error(f"unknown providers: {', '.join(unknown)}")
    run(args.manifest, args.output_dir, providers)


if __name__ == "__main__":
    main()
