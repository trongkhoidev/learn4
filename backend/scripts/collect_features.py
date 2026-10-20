"""Thu thập acoustic features từ bộ audio — phục vụ calibration pronun/fluency.

Xuất JSONL gồm: file, text, avg_logprob, total_duration_s, word_count, words[]
(giữ cột ground_truth_band trống để điền band từ luyennoi khi có account).

Usage:
    python scripts/collect_features.py <input_dir> --output features.jsonl
"""

import argparse
import json
from pathlib import Path

AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac", ".opus"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect acoustic features for calibration")
    parser.add_argument("input_dir")
    parser.add_argument("--output", default="features.jsonl")
    parser.add_argument("--model", default="turbo")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    args = parser.parse_args()

    from faster_whisper import WhisperModel

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    out_path = Path(args.output)
    rows = []
    for path in sorted(Path(args.input_dir).iterdir()):
        if path.suffix.lower() not in AUDIO_EXTS:
            continue
        segments, _ = model.transcribe(str(path), beam_size=1, word_timestamps=True)
        seg_list = list(segments)
        words = [
            {"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3), "probability": w.probability}
            for s in seg_list
            for w in (s.words or [])
        ]
        avg_logprob = sum(s.avg_logprob for s in seg_list) / len(seg_list) if seg_list else None
        total_duration = seg_list[-1].end - seg_list[0].start if seg_list else 0.0
        rows.append(
            {
                "file": path.name,
                "text": " ".join(s.text for s in seg_list).strip(),
                "avg_logprob": avg_logprob,
                "total_duration_s": round(total_duration, 3),
                "word_count": len(words),
                "words": words,
                "ground_truth_band": None,
            }
        )

    with out_path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} samples to {out_path}")


if __name__ == "__main__":
    main()
