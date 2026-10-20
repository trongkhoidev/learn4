# Speaking feedback repair — 2026-10-19

## Failure and cause

A real local practice submission transcribed successfully, but FC, LR, and GRA
all failed with incomplete JSON. Replaying the same FC payload with the previous
900-token Gemini budget returned `MAX_TOKENS`: only 25 response tokens and
67 characters of invalid JSON. The adapter had treated any nonempty text as a
successful completion. Gemini 2.5 thinking consumed most of the shared budget.

Additional real-provider checks exposed the configured Gemini free-tier request
quota and quote/word-ID mismatches around uncertain transcript words. None of
these failures justify assigning a fallback band.

## Changes

- Replace deprecated `google.generativeai` with the validated `google-genai`
  client. Preserve user/model message roles during a repair request and close
  clients on every path. Set a bounded HTTP timeout and control retries locally.
- Give criterion JSON 4096 tokens, limit Gemini 2.5 thinking to 1024, reject
  non-STOP completions, and retry truncation once with a larger bounded budget.
- Supply the criterion JSON schema to Gemini's structured-output API. Constrain
  the requested criterion, at most three evidence spans, and no grammar-error
  objects from the Fluency or Vocabulary raters.
- Honor a provider's explicit quota retry window up to 60 seconds once. Missing,
  invalid, long, or exhausted retry windows produce a distinct rate-limit result
  and useful Vietnamese instructions, rather than a misleading JSON error.
- Mark uncertain words in the payload. Supply exact, uninterrupted candidate
  quotations from reliable spans. Return every reference validation error in one
  repair request, including the exact expected quote. Keep the existing evidence,
  uncertainty, criterion, and half-band validation gates.
- Connect the existing audio pronunciation observation service to practice
  assessment. Provide measured timing/recording observations and a practice
  action. Phoneme errors, pronunciation bands, and overall bands remain absent
  without a validated method.
- Display all four feedback cards and their next actions. Link saved practice
  results from history and support `/speaking/practice?session=<id>`, including
  reload and stored audio playback.
- Do not mount the recorder until questions for the selected Part finish
  loading, avoiding replacement of a recording by an arriving question.

## Verification

From `backend/`: `./.venv/bin/python -m pytest -q` and
`./.venv/bin/ruff check app tests scripts`.

From `frontend/`: `npm run lint`, `npm run build`, and
`PLAYWRIGHT_BROWSERS_PATH=/private/tmp/lexilearn-playwright-browsers npx playwright test tests/speaking.spec.js`.

Regression coverage includes truncated completions, role preservation, quota
windows, client cleanup, all-reference repair diagnostics, safe quotation
candidates, pronunciation observations without fabricated bands, four feedback
cards/actions, and reopening/reloading an actual persisted test result.

Final checks: **129 backend tests passed**, Ruff passed, frontend ESLint passed,
Vite production build passed, and **7 Speaking browser tests passed** in 21.4 s.
Earlier browser attempts experienced host resource contention while a real
Whisper replay was running; the final suite passed with native inference stopped.
The test suite was not weakened to bypass those failures.

Live Gemini returned valid non-null bands for all three language criteria on a
clear reference transcript. This establishes that the provider integration and
validation path work; it does not establish agreement with IELTS examiners.
The learner's original local recording and pre-repair database were preserved.

The original local submission was subsequently repaired using its preserved ASR
transcript, timestamps, and uncertainty spans, without manually correcting any
learner words. Live Groq `openai/gpt-oss-120b` produced validated FC 6.5, LR 6.0,
and GRA 5.0, with feedback and next actions for all four criteria. Pronunciation
and overall bands stay null. The result was validated and saved to the same
practice session, so it can be reopened through the new saved-result link.

The local test server now uses Groq because the configured Gemini account kept
returning quota errors after its suggested retry window. The Groq models endpoint
confirmed `openai/gpt-oss-120b` and `openai/gpt-oss-20b` are available; the previous
configured Llama model returned `model_not_found`. `.env.example` now agrees with
the existing model defaults in `Settings`. The active test process uses
`LLM_PROVIDER=groq`, those two model overrides, and `TIER_PRACTICE=70b,70b,70b`.
Credentials in `.env` were not changed.
