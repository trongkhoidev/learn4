# Whisper runtime hardening — 2026-10-19

## Scope

The existing English Speaking pipeline uses faster-whisper, not a newly trained
checkpoint. Keep its English transcription profile, VAD, word timestamps,
uncertainty gates, and conditional second decode. This change improves runtime
reliability. Recognition quality for Vietnamese learners still requires the
held-out corpus described in `backend/scripts/asr_training/README.md`.

## Runtime changes

- Load one model under a process-local lock, including import failures in model
  error reporting. Configure CPU threads explicitly; use one model worker.
- Serialize normalization and both decoding passes per process. The lock covers
  consumption of faster-whisper's lazy segment iterator. Release it on failure.
- Wait at most `STT_LOCAL_WAIT_SECONDS` for local capacity. `selfhost` reports a
  failure when busy; `auto` can fall back to configured Groq. Never substitute mock
  transcripts for provider errors.
- In `auto`, failed startup preload can use configured Groq. In `selfhost`, preload
  failure still fails startup. `/ready` reports model load state and fallback
  availability. With preload disabled, local readiness is configuration readiness
  until a model load is attempted. Remote readiness checks credentials are present;
  it does not validate them with an API request.
- Bound Groq request timeout, disable SDK retries because durable jobs already
  retry, and close the HTTP client even on failure.
- Bound FFmpeg/FFprobe subprocess time. Normalization removes temporary output on
  error/timeout and rejects using the original file as its output.
- Persist `asr_latency_ms` and `asr_fallback_reason` through the typed assessment
  metadata. Latency includes local capacity wait, cold load, normalization,
  decoding, and fallback when used. Failure reasons contain exception class names,
  not provider error bodies or audio text.

## Configuration

Defaults are in `.env.example`:

```dotenv
WHISPER_MODEL=turbo
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_PRELOAD=true
WHISPER_CPU_THREADS=4
STT_PROVIDER=selfhost
STT_LOCAL_WAIT_SECONDS=30
STT_REMOTE_TIMEOUT_SECONDS=60
AUDIO_PROCESS_TIMEOUT_SECONDS=60
```

For cloud fallback, choose `STT_PROVIDER=auto` and configure `GROQ_API_KEY`.
No credentials or running deployment settings were changed by this work.
Invalid provider names, negative wait limits, nonpositive timeouts/thread counts,
and nonfinite timeout values fail configuration validation.

Keep one application process for the current embedded job worker. Locks do not
coordinate multiple processes or hosts; each process loads its own model. The
capacity timeout limits waiting for a local slot, not inference execution time.
Groq's timeout is an HTTP timeout, not a strict total job deadline. A stalled native
decoder still requires process supervision. Multi-host queue claims and production
load/soak tests remain separate work.

## Verification

Run from `backend/`:

```sh
./.venv/bin/python -m pytest -q
./.venv/bin/ruff check app tests scripts
```

Run from `frontend/`:

```sh
npm run lint
npm run build
PLAYWRIGHT_BROWSERS_PATH=/private/tmp/lexilearn-playwright-browsers npx playwright install chromium --only-shell
PLAYWRIGHT_BROWSERS_PATH=/private/tmp/lexilearn-playwright-browsers npx playwright test tests/speaking.spec.js
```

Backend regressions cover concurrent model initialization, lazy decode failure,
lock release, local saturation/fallback, startup/readiness states, client cleanup,
normalization timeout/input preservation, configuration validation, and typed
metadata preservation. Browser tests use mock providers and isolated storage/DB.

Results: **117 backend tests passed**, Ruff passed, frontend ESLint passed,
Vite production build passed, and **7 Speaking browser tests passed** (17.9 s),
including fake microphone recording, submission, partial feedback, and history.
The first browser attempt lacked Chromium; after installation, the sandbox blocked
macOS Mach port creation. Running the same suite with the approved sandbox
escalation passed. Backend tests emit one Starlette TestClient deprecation warning.
No dedicated type checker is configured in the current project.

### Real local model check

Ran the actual `recognition.transcribe` entrypoint with `HF_HUB_OFFLINE=1`,
`STT_PROVIDER=selfhost`, CPU int8, four CPU threads, faster-whisper 1.2.1.
Used the already cached Turbo checkpoint revision
`0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf`.

Speech was generated locally with macOS `say -v Samantha` into a temporary AIFF:

> I enjoy learning English because it helps me communicate with people from different countries.

Both passes returned that exact sentence. Also tested generated two-second PCM
silence and `backend/tests/fixtures/audio/noise_only_2s.wav`. Assertions required
speech WER <= 20% and empty transcripts on both negative samples. No cloud API
was called; generated files were removed with their temporary directory.

| Input | Duration | Latency | RTF | Result |
|---|---:|---:|---:|---|
| Speech, cold load | 4.675 s | 11,235.66 ms | 2.403 | WER 0% on this sentence |
| Speech, warm | 4.675 s | 4,890.85 ms | 1.046 | WER 0% on this sentence |
| Silence | 2 s | 123.46 ms | 0.062 | Empty transcript |
| Noise | 2 s | 110.20 ms | 0.055 | Empty transcript |

Model readiness after these checks: loaded, no load error, ready. These tiny
synthetic checks establish that real inference runs and these negative samples
are rejected. They do not establish learner WER, accent robustness, throughput,
pronunciation accuracy, or examiner-calibrated IELTS bands. Groq timeout/fallback
behavior was tested with fakes, not a live cloud request.

## Primary API references

- [faster-whisper transcription implementation](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py)
- [Groq SDK timeout and retry configuration](https://github.com/groq/groq-python#timeouts)
