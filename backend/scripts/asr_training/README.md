# Speaking ASR data contract

This directory contains the manifest rules and evaluation tooling for a future
consented corpus. It contains no learner recordings or examiner labels. The
existing generated audio fixtures test pipeline behavior only; they are not an
accuracy benchmark.

## Annotation policy

- Annotate what is audible, not what the speaker likely intended. Preserve
  grammar errors, fillers, repetitions, false starts, self-corrections, and
  incomplete phrases. Keep the audio language in the reference transcript.
- Keep `reference_verbatim` separate from optional `reference_corrected_for_coaching`.
  A trainer export contains only the audio path and verbatim transcript; it must
  never contain corrected text, bands, model predictions, or test labels.
- When a span cannot be heard, do not guess. Mark its start/end in
  `human_unclear_spans`, record the annotation decision, and either mask the
  span in a trainer that supports loss masks or exclude the sample from ASR
  training. Do not teach Whisper to emit `[unclear]` by default.
- Keep ASR labels separate from assessment labels. If band ratings are collected,
  at least two qualified examiners rate independently without seeing model output;
  adjudicate material disagreements and record examiner IDs and rubric version.
- Require a consent ID and retention deadline. Do not ingest recordings from
  product users or third-party services without documented rights for the
  exact research/training use.
- Assign split before chunking. A speaker and all sessions from that speaker
  belong to one split. Remove exact and near-duplicate audio across splits.
  Keep a separate unseen-topic slice where feasible. Augment train only.

`manifest.schema.json` defines one JSON object per JSONL row. The validator checks
speaker/session leakage, consent fields, dates, and unique sample IDs. To make a
safe trainer input, run:

```sh
python scripts/asr_training/prepare_manifest.py manifest.jsonl --train-inputs train-inputs.jsonl
```

The output has exactly `sample_id`, `audio_path`, and `text`; it contains train
rows only and uses `reference_verbatim`. The validator never opens audio files.

## Evaluation

Use `evaluate_asr.py` only on a frozen held-out manifest with predictions from a
named baseline/checkpoint. It reports raw and normalized WER, CER, edit counts,
content-word deletions, preservation of annotated errors/fillers/repetitions/
false starts, silence hallucination, timestamp error when aligned word timings
are supplied, slice reports, and speaker-cluster bootstrap intervals. The report
must include sample and unique-speaker counts for each slice. Empty or sparse
slices remain visible.

No checkpoint may replace the baseline from WER alone. Review verbatim error
preservation, silence hallucination, slice coverage, latency/RTF, and costs under
the separately frozen release gates in the Speaking accuracy plan.

Generate comparable predictions from every configured engine, then evaluate each
output independently:

```sh
python scripts/asr_training/run_provider_benchmark.py manifest.jsonl \
  --output-dir benchmark-output \
  --providers selfhost,deepgram,elevenlabs
python scripts/asr_training/evaluate_asr.py benchmark-output/deepgram.jsonl
```

Run all providers on the exact same frozen test split. Provider failures remain
as empty predictions and are visible in WER; the runner never silently falls
back to a different engine.

## LoRA fine-tuning

Examiner bands are never Whisper targets. Fine-tune Whisper only with short
audio clips and human-verbatim transcripts; use the separate calibration tools
for examiner criterion ratings. Each training clip must be at most 30 seconds,
and all clips from one speaker remain in the same split.

On an isolated CUDA machine:

```sh
pip install -r requirements-training.txt
python scripts/asr_training/train_whisper_lora.py manifest.jsonl \
  --output artifacts/whisper-ielts-lora
```

The trainer refuses fewer than 100 train clips or 20 validation clips by
default, missing audio, expired consent, split leakage, and clips over Whisper's
30-second window. It saves both the LoRA adapter and a merged Transformers
checkpoint. Convert the merged checkpoint to CTranslate2, benchmark it on the
frozen test split with `evaluate_asr.py`, and promote it only when it improves
WER and preserves real grammar errors, fillers, repetitions, and false starts.
