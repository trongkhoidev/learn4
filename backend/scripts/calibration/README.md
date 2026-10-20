# Speaking assessment calibration dataset

The evaluator compares criterion estimates with independent examiner labels. It
does not train or fit a model. Use one JSONL row per assessment sample and freeze
the explicit speaker-disjoint `split` before any model tuning.

```json
{
  "sample_id": "sample-001",
  "speaker_id": "speaker-001",
  "session_id": "session-001",
  "split": "test",
  "human_ratings": [
    {"examiner_id":"e1","prediction_hidden":true,"fluency":6.5,"vocab":6.0,"grammar":6.0,"pronun":6.5,"overall":6.5},
    {"examiner_id":"e2","prediction_hidden":true,"fluency":6.0,"vocab":6.5,"grammar":6.0,"pronun":6.5,"overall":6.5}
  ],
  "prediction": {
    "fluency":{"status":"scored","band":6.0},
    "vocab":{"status":"scored","band":6.5},
    "grammar":{"status":"scored","band":6.0},
    "pronun":{"status":"insufficient_evidence","band":null},
    "overall":{"status":"insufficient_evidence","band":null}
  },
  "human_audited_claims": [],
  "metadata": {"device":"android","noise":"quiet","region":"south","accent":"vi"}
}
```

Rules enforced before evaluation:

- Every sample has two distinct examiner IDs for each criterion; each examiner
  records that AI predictions were hidden.
- Material disagreements greater than one band require an adjudicator ID and a
  resolved band. All ratings must use the half-band scale from 0 to 9.
- Speaker and session IDs cannot cross splits. The evaluator reads the frozen
  `split` field; it does not assign splits from a hash.
- Null/abstained predictions remain in coverage and are not silently dropped.
- Feedback precision and fabricated-quote gates require explicit human-audited
  claim records; absent audit data cannot pass those gates.

Run on a frozen test file:

```sh
python scripts/calibration/evaluate.py labels.jsonl --split test --min-speakers 30
```

The report includes MAE, QWK, bias, within-half accuracy, criterion coverage,
95% bootstrap intervals resampled by speaker, sample and speaker counts per
slice, and release gates. The 30-speaker minimum and score thresholds are
internal release gates, not proof of examiner equivalence or IELTS certification.

## Fit a production band calibrator

Examiner ratings tune the assessment layer, not Whisper transcript weights.
After freezing speaker-disjoint train, validation, and test splits, fit only on
the training split:

```sh
python scripts/calibration/fit_band_calibration.py labels.jsonl \
  --output artifacts/speaking-band-calibration.json \
  --version examiner-cal-2026-01 --min-samples 100 --min-speakers 30
python scripts/calibration/evaluate.py labels.jsonl --split test --min-speakers 30
```

Set `SPEAKING_BAND_CALIBRATION_PATH` and `CALIBRATION_VERSION` only after the
frozen test report passes the release gates. The fitter requires two hidden,
distinct examiner ratings per criterion and adjudication for disagreements over
one band. Weighted isotonic regression corrects systematic band bias without
allowing the mapping to reverse band order.
