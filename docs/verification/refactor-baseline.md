# Refactor baseline snapshot

Captured before R1 changes on 2026-10-18. This records path names only; it contains no file
contents. The nested `learn4/` gitlink and `luyennoi-clone/` reference tree were kept in place.
No broad Git cleanup, staging, reset or restore operation was run.

## Baseline verification

- Backend: `cd backend && ./.venv/bin/python -m pytest -q` — **93 passed**, with one existing
  Starlette/httpx deprecation warning.
- Frontend: `cd frontend && npm run build` — **pass**.
- Playwright: the initial environment lacked the Chromium browser. The first launch attempt was
  blocked by macOS browser sandbox permissions before assertions ran. Chromium was installed under
  a temporary path; final isolated Playwright runs were later completed with host browser
  permissions (see the handoff report).
- The initial pytest count included two test-named diagnostic functions in root `test_debug*.py`
  files. Those scripts were moved to manual diagnostics and excluded from pytest discovery; the
  final 91 count is the real `backend/tests/` suite.
- Baseline API and ORM metadata snapshots were captured separately and compared after the refactor.
  Local DB/media hashes and directory metadata are recorded in `preserved-artifacts.md`.

## Initial Git path status

The following is the captured path-only status under the project path. It includes pre-existing
modified and untracked work and is retained as a reference for review.

```text
 M .env.example
 M README.md
 M backend/app/config.py
 M backend/app/main.py
 M backend/app/models/__init__.py
 M backend/app/models/class_.py
 M backend/app/models/speaking.py
 M backend/app/routers/assignments.py
 M backend/app/routers/classes.py
 M backend/app/routers/speaking.py
 M backend/app/routers/submissions.py
 M backend/app/schemas/class_.py
 M backend/app/schemas/speaking.py
 M backend/app/services/acoustic.py
 M backend/app/services/assessment_service.py
 M backend/app/services/audio_processor.py
 M backend/app/services/blob_service.py
 M backend/app/services/llm_service.py
 M backend/app/services/queue.py
 M backend/app/services/scoring_service.py
 M backend/app/services/stt_service.py
 M backend/tests/conftest.py
 M backend/tests/test_scoring.py
 M docker-compose.yml
 M frontend/playwright.config.js
 M frontend/src/App.jsx
 M frontend/src/api/client.js
 M frontend/src/components/Layout.jsx
 M frontend/src/components/speaking/AudioRecorderPro.jsx
 M frontend/src/components/speaking/GrammarErrorList.jsx
 M frontend/src/components/speaking/ScoreGrid.jsx
 M frontend/src/components/speaking/WordHighlighter.jsx
 M frontend/src/index.css
 M frontend/src/pages/Speaking/SpeakingDashboard.jsx
 M frontend/src/pages/Speaking/SpeakingHistory.jsx
 M frontend/src/pages/Speaking/SpeakingMockTest.jsx
 M frontend/src/pages/Speaking/SpeakingPractice.jsx
 M frontend/src/pages/Teacher/ClassDetail.jsx
 M frontend/src/pages/Teacher/Dashboard.jsx
 M frontend/tailwind.config.js
 M frontend/tests/speaking.spec.js
 M learn4
?? DESIGN.md
?? SPEAKING_ACCURACY_TRAINING_PLAN.md
?? SPEAKING_WHISPER_PRODUCTION_PLAN.md
?? backend/app/services/alignment_service.py
?? backend/app/services/pronunciation_service.py
?? backend/app/services/rater_contract.py
?? backend/app/services/retention_service.py
?? backend/app/services/rubric.py
?? backend/curl_out.txt
?? backend/scripts/asr_training/README.md
?? backend/scripts/asr_training/evaluate_asr.py
?? backend/scripts/asr_training/manifest.schema.json
?? backend/scripts/asr_training/prepare_manifest.py
?? backend/scripts/calibration/README.md
?? backend/scripts/calibration/evaluate.py
?? backend/scripts/make_calibration_fixtures.py
?? backend/test.m4a
?? backend/test.webm
?? backend/test_debug.py
?? backend/test_debug2.py
?? backend/test_parse.py
?? backend/tests/fixtures/audio/manifest.json
?? backend/tests/fixtures/audio/noise_only_2s.wav
?? backend/tests/fixtures/audio/repeated_beeps_3s.wav
?? backend/tests/fixtures/audio/silence_2s.wav
?? backend/tests/fixtures/audio/speech_like_mixed_4s.wav
?? backend/tests/fixtures/audio/tone_440_2s.wav
?? backend/tests/fixtures/audio/tone_with_gap_3s.wav
?? backend/tests/fixtures/audio/truncated_tone_0_3s.wav
?? backend/tests/test_asr_training.py
?? backend/tests/test_calibration_evaluate.py
?? backend/tests/test_classes_assignments.py
?? backend/tests/test_prompts.py
?? backend/tests/test_pronunciation.py
?? backend/tests/test_scoring_calibration.py
?? backend/tests/test_speaking_contract.py
?? backend/tests/test_speaking_sessions.py
?? backend/tests/test_stt_confidence.py
?? backend/tests/test_submissions.py
?? docs/design/role-page-inventory.md
?? docs/design/stitch-redesign-brief.md
?? docs/plans/project-cleanup-refactor-plan.md
?? docs/prompts/refactor-handoff.md
?? docs/research/ielts-speaking-asr-primary-sources.md
?? frontend/src/components/speaking/FeedbackFocusCard.jsx
?? frontend/src/components/speaking/PronunErrorList.jsx
?? frontend/src/components/speaking/SpeakButton.jsx
?? frontend/src/components/speaking/SpeakingShell.jsx
?? frontend/src/components/speaking/VoiceSetupModal.jsx
?? frontend/src/hooks/useSpeech.js
```
