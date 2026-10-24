# Verification report — Learn4 Pronunciation Engine (P0–P8)

Date: 2026-10-21 · Review fixes applied: 2026-10-22 · Branch: `main` · Base commit: `0c27c9a219d1a1a8f726ae381c47f8cf52f6d5f4`
Plan: `docs/plans/pronunciation-engine-implementation-plan.md`
Phone-model decision note: `docs/research/pronunciation-phone-model-decision-note.md`

## 1. What this report claims — and what it does not

**Implemented and verified today (offline, deterministic):** the false-score
regression fix (P0), the pronunciation engine seam and fail-closed policy
(P1), deterministic PCM/prosody/GOP/alignment cores with versioned contracts
(P2–P4), the offline dataset/training/evaluation/artifact tooling (P5), the
typed-evidence UI integration (P6), the shadow read-mode wiring and readiness
probe (P7).

**Not claimed:** a working examiner-calibrated Pronunciation band. There is
**no verified examiner dataset and no released calibration artifact**. In this
state the production result is deliberately `Pronunciation band = null` and
`Overall = null` for non-mock flows. That is the correct output of a
fail-closed system, not a defect; P6 data collection remains **data-blocked**
until consented examiner-labelled audio exists.

## 2. Before / after

|Behaviour|Before (base commit)|After|
|---|---|---|
|Real-provider Pronunciation band|Derived from `asr_confidence` via `pronun_conf_to_band`, defaulted to `6.0` when confidence missing/0|`insufficient_evidence`, `band=null`, band source unavailable |
|Mock-session Overall|`None` only when no cached turn bands; turn-mean/pronun rated values could surface|Turn bands accepted only with a trusted `band_source` (`examiner_calibrated_artifact`); no mean, no default `6.5`|
|Legacy persisted bands|Any band survived regardless of how it was produced|Bands whose source is not trusted are invalidated on read (`_legacy_pronunciation_criterion`); stored speaking-v3 Overall drops when Pronunciation loses its band|
|Stored v3 results from the pre-engine era|Passed through with the fake Pronunciation/Overall intact|Re-validated on read: untrusted Pronunciation band and Overall removed|
|Phone-level feedback|None (regex/prosody heuristics only)|Candidate `phoneme_evidence` (GOP, frozen posteriors, real aligned intervals) with `status=candidate`, `confidence=None` — never a score|
|UI Pronunciation panel|ASR intended/heard suggestions rendered as pronunciation errors|Typed candidate evidence with “Cần nghe lại” badges and bounded replay; ASR layer kept separate|
|Engine modes|N/A|`pronunciation_mode` = `disabled` (default) / `shadow` / `enabled`; all fail closed|
|Enabled mode runtime path|Placeholder — refused every band even with a valid artifact|Applies the exported ordinal baseline (bias + standardised coefficients → `predicted_band` on learned `band_values`), emits `examiner_calibrated_artifact` only from a gate-passed artifact|

## 3. Invariants audited (plan §3)

- `band=null` / `band_source="unavailable_no_validated_pronunciation_model"`
  until an artifact passes the release gate — regression-tested
  (`test_pronunciation_p0_regression.py`).
- **stored speaking-v3 results are re-validated on read**: any Pronunciation
  band persisted without a trusted `band_source` (including the pre-engine
  ASR-confidence era) is stripped and its stored `Overall` becomes `null`
  with `status` downgraded to `partial`; trusted sources survive intact.
- Phones/candidates never carry probability-shaped confidence before
  calibration (contract validator rejects them).
- Phone evidence timing only comes from a **real forced-alignment phone
  layer**: without declared phone alignment the engine abstains with
  `real_phone_alignment_unavailable` instead of slicing word spans evenly.
- `status=scored` iff every criterion is scored; Overall only from the backend
  when all four criteria qualify (existing suite kept green).
- Whisper training/ASR confidence never feeds pronunciation.
- Fail-closed at every missing dependency: phone model, lexicon, alignment
  binary, artifact, audio decode (`audio_unreadable` gate → abstention).
- No secrets/PII/raw audio in Git, tests or logs: dataset manifests reference
  audio by SHA-256 with private-storage paths only; the validator rejects
  expiry and duplicates; feature tables are numeric vectors.

## 4. File map

New (backend):

- `app/modules/speaking/pronunciation/`: `policy.py`, `contracts.py`,
  `audio_features.py`, `prosody.py`, `gop.py`, `phone_model.py`,
  `lexicon.py`, `feature_vector.py`, `calibration.py`, `engine.py`,
  `alignment.py` (rewritten), `service.py` (compatibility facade).
- `scripts/pronunciation/`: `README.md`, `manifest.schema.json`,
  `validate_manifest.py`, `extract_features.py`, `train_baseline.py`,
  `evaluate.py`, `export_artifact.py`, `inspect_artifact.py`.
- Docs: `docs/research/pronunciation-phone-model-decision-note.md`, this report.

New (tests, backend): `tests/test_pronunciation_p0_regression.py`,
`tests/test_pronunciation_contract.py`, `tests/test_pronunciation_engine.py`,
`tests/test_pronunciation_alignment.py`, `tests/test_pronunciation_artifact.py`,
`tests/test_pronunciation_dataset.py`, `tests/test_pronunciation_readiness.py`,
`tests/test_pronunciation_metrics.py`.

Modified: `assessment/engine.py` (P0 hotfix, P1 optional pronunciation
result), `speaking/schemas.py` (legacy adapter invalidation),
`core/config.py` (flag set below), `core/bootstrap.py` (readiness entry),
frontend `PronunErrorList.jsx`, `SpeakingPractice.jsx`, `speaking.spec.js`.

## 5. Feature-flag state (exact)

`backend/app/core/config.py` — production defaults today:

```
pronunciation_mode = "disabled"            # disabled | shadow | enabled
pronunciation_artifact_path = ""
pronunciation_phone_model = "none"         # none | manifest
pronunciation_phone_model_manifest = ""
pronunciation_lexicon_path = ""            # falls back to rule-based G2P
pronunciation_alignment_timeout_seconds = 180
```

No value changed from default in any environment as part of this change;
rollback is therefore a no-op and the engine is inert in production.

## 6. Commands and results (executed 2026-10-22, after review fixes)

|Command|Result|
|---|---|
|`cd backend && ./.venv/bin/python -m pytest -q`|**266 passed**, 2 deprecation warnings (Python 3.14 stdlib, unrelated)|
|`./.venv/bin/ruff check app tests scripts`|**All checks passed!**|
|`cd frontend && npm ci`|installed (audit notes upstream advisories in transitive deps, unchanged from baseline)|
|`npm run lint`|clean (0 problems)|
|`npm run build`|`✓ built in 2.67s`|
|`npx playwright test`|**9 passed, 1 skipped** (skipped = pre-existing env-gated screenshot capture, `test.skip(!process.env.CAPTURE_REFACTOR_SCREENSHOTS)`)|

Test breakdown: the engine/tooling suites now cover 16 engine tests
(alignment-gated phone evidence, enabled-mode scoring, fail-closed paths),
17 evaluation/gate tests (QWK normalisation incl. perfect reversal = −1.0,
learned-band mapping, CI enforcement, slice gates), plus dataset/manifest
tests for distinct examiner rater IDs, adjudicator independence and optional
`audio_path` (266 total backend). All offline and deterministic; frozen
posterior arrays replace real models in tests; no network access in any test.

## 7. Metrics classification

|Metric type|Status|
|---|---|
|Unit/contract coverage of engine invariants|**Passing** (described above)|
|Pipeline smoke (manifest → validate → extract → train → evaluate → export → inspect)| **Run on synthetic data only**; export correctly refuses `failed_release_gate` metrics|
|Phone/word-level precision/recall/F1 on evaluator-labelled audio|**Not run** — no consented labelled dataset|
|Band metrics (MAE/QWK/bias/within ±0.5/coverage, speaker bootstrap CI)|**Not run** — same reason|
|Slice metrics (VN region/accent, devices, noise, IELTS Parts)|**Not run**|
|Runtime (RTF, P50/P95 latency, peak RAM/CPU, failure rate)|**Not run** — no native model deployed|

## 8. Release gates (plan §P6)

|Gate|State|
|---|---|
|Artifact schema `pronunciation-artifact-v1`, checksum, uncalibrated rejection|**Implemented + tested**; loader fails closed on every tamper vector tried. The artifact now carries `band_values` (learned classes), `bias` and `standardization` for the runtime path|
|Examiner-annotated consented dataset (≥150 speakers, dual examiner with distinct `rater_id`s, adjudicator ≠ both raters)|**Blocked** — data collection has not started|
|Baseline model ≠ above gate (MAE ≤ 0.5, QWK ≥ 0.75, \|bias\| ≤ 0.25, within ±0.5 ≥ 0.8, coverage ≥ 0.95, **pessimistic bound of the 95% speaker-clustered bootstrap CI for every gated metric**; slices with n ≥ 5 must also pass the MAE gate)|**Not run** — blocked by dataset|
|Open-weight phone model (P3 decision note)|Candidate `facebook/wav2vec2-lv-60-espeak-cv-ft` (Apache-2.0) recorded; adapter **blocked** — weights not cached/benchmarked locally; ManifestPhoneModel refuses to claim phones without manifest+checksum|

## 9. Blockers

1. **Examiner dataset (P6)** — consent, two-rater protocol, speaker-disjoint
   splits and annotation tooling need human examiners and learners. No
   substitute exists; not worth fabricating.
2. **Phone model weights** — need an offline benchmark run against a small
   licensed fixture to confirm phone-tag agreement before the manifest gate
   can pass; requires download + explicit opt-in, never in CI.
3. **Runtime split (P8)** — native audio/ML dependencies belong in a separate
   pronunciation worker image; current free-tier hosting is not suitable for
   ML inference, so production rollout stays `disabled`.

## 10. Rollback

Nothing else loads the new modules at import time; the engine is only
reached through `get_engine()` behind `pronunciation_mode` (default
`disabled`). Removing/ignoring all new files above or reverting to base
`0c27c9a` restores the previous behaviour exactly. The heuristic P0 removal
(`pronun_conf_to_band`) has **no** config re-enable path by intent: ASR
confidence → band is a defect, not a feature.

## 11. Follow-up summary

1. Run the phone-model benchmark (dev machine) → enable `shadow` behind config.
2. Start examiner data collection (plan §P5 protocol) → `scripts/pronunciation/`
   pipeline is ready to validate/freeze features when data lands.
3. Only after the release gate passes: `export_artifact` → `enabled` mode can
   produce bands; the UI already supports the four-band + Overall flow.
