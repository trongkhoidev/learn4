# Kế hoạch MVP Speaking — tương đương luyennoi.com

> Đi kèm `RESEARCH_LUYENNOI_SPEAKING.md` (thuật toán gốc) và `PLAN_TECH_LOGIC_COST.md` (chi phí).
> Đây là tài liệu **MVP số 1** của LexiLearn — Speaking. Đã hiệu chỉnh theo kết quả verify code thật.

---

## 0. Đặt kỳ vọng đúng

| Lớp | Nằm ở đâu | Ta có gì | Độ chính xác |
|---|---|---|---|
| **A. Aggregation/scoring** (merge, penalty, overall, lọc lỗi) | Client JS `test-score.js` | Source thật | **~99-100%** (port từng dòng) |
| **B. Acoustic features** (`pronun.score`, `fluency.score`) | Server luyennoi, closed | Không có source | **Chỉ xấp xỉ tốt** bằng calibration, vì ASR khác nhau (faster-whisper turbo int8 vs ASR luyennoi) |

→ Mục tiêu thực tế tầng (B): band ra ổn định, đúng thứ hạng tương đối, **sai số ≤ 0.5 band** — không phải "nộp cùng 1 audio ra đúng y hệt con số".

---

## 1. Pipeline

```text
audio ──► audio_processor (FFmpeg 16kHz mono, nén Opus) ──► R2
                │
                ▼
        stt_service.transcribe()
        faster-whisper large-v3-turbo (int8), beam_size=1, word_timestamps=True
                │
                ├─ transcript, words[{word,start,end,probability}]
                ├─ segments[{avg_logprob, no_speech_prob, compression_ratio}]
                │
        ┌───────┴────────┐
        ▼                ▼
  acoustic.py        3× llm_service (song song, tiering)
  (mục 2)             1) fluency (+relation)  2) grammar  3) vocab
        │                │
        └───────┬────────┘
                ▼
      scoring_service.user_audio_2_score()   ← port nguyên từ research doc
                ▼
      { overall, pronun, fluency, grammar, vocab, errors[], color_coded_transcript }
```

---

## 2. Acoustic features → band (đã hiệu chỉnh)

### 2.1 Điểm mấu chốt (sửa so với bản nháp trước)

`user_audio_2_score` nhận `pronun.score` và `fluency.score` là **BAND (0-9)**, không phải raw.
`pronun_conf_to_band` / `fluency_score_to_band` chính là hàm chuyển **raw → band** mà luyennoi áp ở server.

```text
pronun:  confidence = exp(avg_logprob)  →  pronun_conf_to_band(confidence)  →  pronun.score
fluency: raw = compute_fluency_acoustic →  fluency_score_to_band(raw)        →  fluency.score
```

Bằng chứng: `g()` dùng `pronun.score` trực tiếp làm band (chỉ cap 7), và `D(acoustic, llm)` có nhánh `acoustic>=8` chỉ hợp lệ khi acoustic là band 0-9.

### 2.2 `pronun.score` — confidence từ `avg_logprob`

```python
confidence = max(0.0, min(1.0, math.exp(avg_logprob)))   # avg_logprob = mean các segment
band = pronun_conf_to_band(confidence)
```

- `avg_logprob` là log-softmax trung bình → `exp()` đưa về [0,1] có ý nghĩa xác suất.
- **Cảnh báo calibration**: whisper-family logprob bị *overconfident* (thường cluster ~0.85–1.0), nên confidence thô có thể lệch xa range `0.483..0.85` của `he()`. Bắt buộc fit lại `low/high` trên dữ liệu thật (mục 4).

### 2.3 `fluency.score` — disfluency score từ speech rate + pause

```python
def compute_fluency_acoustic(words, total_duration_s):
    n_words = len(words)
    speech_rate_wpm = n_words / total_duration_s * 60
    pauses = [w[i].start - w[i-1].end for gap > 0.3s]
    pause_ratio = sum(pauses) / total_duration_s
    long_pauses  = count(p > 1.0s)
    rate_penalty  = abs(wpm - 130) / 130
    raw = 1.0 + rate_penalty*2 + pause_ratio*3 + long_pauses*0.15
    return round(raw, 3)               # "càng thấp càng tốt" — khớp chiều de()
band = fluency_score_to_band(raw)
```

- Căn cứ: tốc độ bản ngữ 110–150 wpm (lý tưởng ~130); pause > 0.3s là ngắt, > 1s là ngắt dài.
- Hệ số `2 / 3 / 0.15` là placeholder — calibrate ở mục 4.

### 2.4 `noise`

```python
avg_no_speech = mean(segments.no_speech_prob)
if avg_no_speech > 0.6 or len(transcript.split()) == 0:
    noise = "cant_hear"
```

---

## 3. Prompt LLM (giữ format, sửa 2 điểm)

- **`Band:` không có space trước `:`** (regex gốc `Band:\s*` không chấp nhận `Band :`).
- Thêm 1 dòng **band descriptor** ngắn vào system prompt để giảm variance giữa các lần gọi.

```text
Fluency:
  You are an IELTS examiner assessing Fluency & Coherence.
  Question: {question}
  Answer: {transcript}
  Return exactly (no extra text):
  relation : related|weakly-related|unrelated
  reason : <1 câu tiếng Việt, chỉ ghi khi unrelated>
  evidence : <trích dẫn ngắn>
  Band: X.X

Grammar:
  You are an IELTS examiner assessing Grammatical Range & Accuracy.
  Answer: {transcript}
  List every grammar error as: - "sai" -> "đúng" : giải thích ngắn (tiếng Việt)
  Then output exactly: Band: X.X

Vocab:
  You are an IELTS examiner assessing Lexical Resource.
  Answer: {transcript}
  Output exactly: Band: X.X
```

- Định dạng `- "sai" -> "đúng" : ...` giữ **nguyên** vì `parse_grammar_errors` phụ thuộc dấu `->`.
- Model 8B (tier practice/budget): test riêng độ ổn định format trước khi dùng — dễ lệch format hơn 70B.

---

## 4. Calibration (bắt buộc, làm sớm — không để cuối)

### Bước 1 — Thu mẫu đối chứng
1. 15–20 mẫu audio đa dạng (band thấp/trung/cao, lạc đề, quá ngắn, nhiều nhiễu).
2. Nộp chính các mẫu đó lên luyennoi.com thật → lưu band + noise làm ground-truth.
3. Chạy cùng mẫu qua faster-whisper self-host → `avg_logprob`, `words[].probability`, timestamps.

### Bước 2 — Fit hằng số
- Scatter `exp(avg_logprob)` vs band pronun luyennoi → fit `low/high` mới cho `pronun_conf_to_band` (hồi quy tuyến tính đơn giản, `numpy.polyfit`).
- Tương tự cho fluency: `raw` vs band luyennoi → fit hệ số rate/pause/repair.

### Bước 3 — Validate
- Chạy trên mẫu **giữ ra ngoài** (3–5 mẫu test set) → so band với luyennoi.
- Chấp nhận sai số ≤ 0.5 band cho pronun/fluency.

---

## 5. Test harness (phần chắc chắn — đã code xong)

`backend/app/services/scoring_service.py` + `backend/tests/test_scoring.py` — **16 test pass**, cover:
- `merge_fluency` từng nhánh (llm≤5, exception `llm≥7 && acoustic≥8`, cap tại llm, round half-up).
- `parse_band` (kể cả case `Band :` có space → 0, đúng regex gốc).
- off-topic → zero toàn bộ.
- thứ tự penalty: cap pronun → too-short −1 → noise zero.
- `pronun_conf_to_band` / `fluency_score_to_band`.
- pipeline lỗi grammar 4 tầng.
- aggregation (median/agg/agg_pronun/overall_of).

Chạy: `cd backend && python3 -m pytest -q`.

---

## 6. Thứ tự triển khai còn lại

| Bước | Việc | Trạng thái |
|---|---|---|
| 1 | `scoring_service.py` + unit test | ✅ xong |
| 2 | `stt_service.py` (faster-whisper) chạy độc lập, log `avg_logprob`/timestamps | ⬜ tiếp theo |
| 3 | Calibration (mục 4) trên mẫu thật + luyennoi | ⬜ |
| 4 | `llm_service.py` (3 call song song + tiering) | ⬜ |
| 5 | `assessment_service.py` orchestrate + ghép scoring | ⬜ |
| 6 | API router + background queue + `FeedbackPanel`/`ReasoningCards` | ⬜ |

---

## 7. Mức độ "giống luyennoi" đạt được

| Thành phần | Mức độ |
|---|---|
| Merge/penalty/overall | ~99-100% (port từ code thật) |
| Lọc lỗi grammar 4 tầng | ~99% (đã port đủ stemming + number-words) |
| Band pronun/fluency (acoustic) | sai số ≤ 0.5 band sau calibration |
| Prompt LLM | cấu trúc giống, band hợp lý (cùng tiêu chí IELTS) |
| Trải nghiệm học viên (4 band + overall + lỗi + transcript màu) | rất gần |

**Phạm vi MVP Speaking:** chấm 4 tiêu chí + overall + lỗi grammar + color-coded transcript + phát hiện lạc đề + mock test (Part 1/2/3). **Không** làm: phoneme-level (`AUDIO2PHONEMES`, `WORD_PRONUN`), micro-practice (S/ES, ED, tenses), CONVERSATION, TTS.
