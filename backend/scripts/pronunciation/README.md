# Pronunciation offline tooling (plan §P5–P6)

Offline-only tooling for the examiner-labelled pronunciation dataset and the
calibrated band artifact. **Nothing here runs at inference time** and the
runtime engine never imports from `scripts/`. There is **no verified
examiner-calibrated artifact yet**, so the production engine stays
`pronunciation_band=null` and `Overall=null` until the release gate below has
actually passed.

## Data policy

- No raw learner audio or downloads of public corpora (SpeechOcean762,
  L2-ARCTIC) may be committed to this repository. Audio lives in private
  storage: the manifest identifies every session's source by `audio_sha256`
  (the required field); `audio_path` is an optional private-storage pointer
  used by the extraction run and is not part of the dataset identity.
- Licence and provenance must be recorded per dataset **before** download or
  use. Public-corpus scores are never mapped directly to IELTS bands.
- Labels come from two independent examiners identified by distinct
  `rater_id`s; disagreement greater than one band requires adjudication by a
  third, different rater before the session gets a training label.
- Splits are chosen per **speaker** before segmentation; speaker overlap
  across splits is a hard validation failure (leakage).
- Consent is tracked per session with an explicit expiry date; expired
  consent blocks the session from every downstream step.
- The frozen test split is never used to choose features, thresholds, models,
  or calibrators.

## Pipeline

```bash
cd backend

# 1) validate the dataset manifest (leakage/consent/duplicate/licence gates)
./.venv/bin/python -m scripts.pronunciation.validate_manifest path/to/manifest.json

# 2) freeze feature rows from per-session metadata
./.venv/bin/python -m scripts.pronunciation.extract_features path/to/manifest.json \
    --sessions-dir path/to/metadata/ --out features.json

# 3) fit the explainable ordinal baseline (speaker-disjoint train split only)
./.venv/bin/python -m scripts.pronunciation.train_baseline features.json \
    --out model.json --lambda 1.0

# 4) evaluate on the frozen test split; release gate is MAE/QWK/within-half/coverage
./.venv/bin/python -m scripts.pronunciation.evaluate features.json \
    --model model.json --out metrics.json

# 5) export only a release-gate-passed artifact, then re-validate it with the
#    runtime loader (fail closed)
./.venv/bin/python -m scripts.pronunciation.export_artifact \
    --model model.json --metrics metrics.json --out artifact.json \
    --calibration-version examiner-cal-YYYY-MM

# 6) inspect what would actually be loaded by the engine
./.venv/bin/python -m scripts.pronunciation.inspect_artifact artifact.json
```

`manifest.schema.json` documents the manifest structure; `validate_manifest`
enforces the semantic rules beyond structure.

## Release gates (plan §P6)

`MAE ≤ 0.5` (half-band units), `QWK ≥ 0.75`, `|bias| ≤ 0.25`,
`within ±0.5 ≥ 0.8` and `coverage ≥ 0.95`, all measured on the frozen
speaker-disjoint test split **with the pessimistic bound of a 95%
speaker-clustered bootstrap CI** (upper bound for MAE/bias, lower bound for
QWK/within-half/coverage; a missing CI never passes any gate). Slices with at
least five sessions must also satisfy the MAE gate. `metrics.status` becomes
`passed_release_gate` only when every gate passes; `export_artifact`
independently re-derives the gate decision from the metric fields and refuses
anything else. Slice coverage (Vietnamese region/accent, devices, noise,
Parts) must be reported next to the headline metrics.

## Offline tests

`tests/test_pronunciation_dataset.py` and `tests/test_pronunciation_artifact.py`
cover the full pipeline with synthetic metadata only — no network, no audio,
no model downloads. Accuracy/model-integration runs require explicit data
paths and credentials and are therefore never part of the default pytest run.
