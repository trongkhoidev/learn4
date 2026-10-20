# Kế hoạch công nghệ, logic hoạt động & chi phí — LexiLearn

> Phiên bản: 2.0 — đi kèm `PLAN_IMPLEMENTATION.md`, `RESEARCH_LUYENNOI_SPEAKING.md`, `LexiLearn_Teacher_Platform_Spec.md`
> Nội dung: tech stack, logic/xử lý/input-output từng kỹ năng, mô hình chi phí với **ngân sách ≤ 4 triệu VND/tháng**.
> Quy ước: 1 USD ≈ 25.000 VND → 4 triệu VND ≈ **$160/tháng**.

---

## 1. Tech stack

| Thành phần | Lựa chọn | Chi phí |
|---|---|---|
| Frontend | React + Vite + Tailwind | $0 |
| Backend | FastAPI (monolith) | $0 |
| DB | PostgreSQL (Docker trong VPS) | $0 |
| Storage | Cloudflare R2 (S3-compatible) | free 10GB, sau $0.015/GB/tháng |
| STT Speaking | **`faster-whisper-large-v3-turbo` (int8) self-host** — fallback Groq | $0 (tốn CPU VPS) |
| LLM Speaking | **Tiering** `llama-3.3-70b-versatile` + `llama-3.1-8b-instant` (xem mục 7) | $0.59/$0.79 (70b) — $0.05/$0.08 (8b) per 1M |
| LLM Writing | `llama-3.3-70b-versatile` (JSON mode, 1 call) | như trên |
| OCR (ảnh viết tay) | Groq `qwen/qwen3.6-27b` (vision, preview) | $0.60 input / $3.00 output per 1M |
| Server | Hetzner CX32 (4 vCPU / 8GB / 80GB) | ~$7.5/tháng |

**Thư viện chính (backend):** `fastapi`, `sqlalchemy`, `psycopg`, `pydantic-settings`, `faster-whisper`, `groq` (SDK), `boto3` (R2), `ffmpeg` (audio), `httpx`, `nltk` (stemmer) hoặc `word2number`.

---

## 2. Kiến trúc AI

```text
Speaking:
  audio ──► FFmpeg (nén Opus 24kbps) ──► R2
                 └─► STT worker (faster-whisper turbo, int8)
                        ├─ transcript + words[{word,start,end}]
                        ├─ segments[{avg_logprob, no_speech_prob, compression_ratio}]
                        │
                        ├─(acoustic)──► fluency.score + pronun.score + noise  (server-side feature)
                        └─(transcript)──► 3× Groq LLM PARALLEL (tiering model):
                                            1) fluency  2) grammar  3) vocab
                                    └──► deterministic aggregation (scoring_service) → 4 band + overall

Writing:
  essay ──┬─ textbox ──► text
          └─ ảnh chụp ─► Groq OCR (qwen3.6-27b) ─► text
                 └──► Groq Llama-3.3-70b (JSON mode) ─► 4 tiêu chí + feedback + lỗi

Reading/Listening: KHÔNG AI — chấm text (normalize + so khớp từng ô).
```

**Chấm không đồng bộ:** `POST /submit` trả `202 pending` ngay, worker xử lý rồi cập nhật `status=graded`; frontend poll `GET /submissions/{id}`.

---

## 3. Reading & Listening (không AI)

### Input — tạo đề (giáo viên)

```jsonc
// POST /api/v1/assignments
{
  "class_id": "uuid",
  "skill": "listening",               // reading | listening
  "title": "Test 12",
  "question_count": 40,               // → sinh 40 ô đáp án
  "content_text": "...",              // (tùy) dán text
  "content_file": "<multipart>",      // (tùy) PDF/ảnh đề
  "audio_file": "<multipart>",        // (listening) file mp3
  "answer_key": ["A","TRUE","modern"] // (tùy) N dòng để chấm tự động
}
```

### Xử lý
1. Lưu `content_file`/`audio_file` lên R2 → ghi `content_file_url`/`audio_url`.
2. `answer_key` có/không quyết định chế độ chấm: **tự động** (có key) hoặc **chờ chấm tay** (không key).

### Output — học viên làm bài
- `GET /assignments/{id}` trả đề (KHÔNG kèm `answer_key`) + `question_count` → frontend sinh N ô.
- Học viên điền text vào N ô → `POST /submit` với `{ student_name, answers: [...] }`.

### Chấm điểm (grading_service)
```text
chuẩn hóa cả key lẫn đáp án: lower, bỏ dấu câu/space thừa, trim
so khớp từng vị trí i: answers[i] == answer_key[i] → đúng/sai
score = số đúng; hiển thị X/N (và tùy chọn quy đổi band theo bảng 40 câu → 9.0)
```
- Không có `answer_key` → `status=pending`, giáo viên nhập điểm tay (`PATCH /submissions/{id}`).

---

## 4. Speaking (self-host STT + tiering LLM song song)

> **Thuật toán chấm chính xác** (port từ `test-score.js` của luyennoi) nằm trong `RESEARCH_LUYENNOI_SPEAKING.md`. Dưới đây là tóm tắt + điểm khác biệt so với spec gốc.

### Input — nộp bài
```jsonc
// POST /assignments/{id}/submit  (multipart hoặc json)
{ "student_name": "Minh Anh", "audio_file": "<audio webm/mp3>" }
```

### Bước 1 — Audio preprocessing (`audio_processor`)
- FFmpeg: chuẩn hoá 16kHz mono, nén **Opus 24kbps** → upload R2 → `audio_url`.
- Giới hạn `MAX_AUDIO_SECONDS` (600s).

### Bước 2 — STT + acoustic (`stt_service`, self-host)
- `faster-whisper` model `turbo` (int8, CPU, beam_size=1), load một lần khi boot.
- Trả `verbose_json`:
  ```jsonc
  {
    "text": "I went to the beach yesterday...",
    "words":   [{ "word":"I", "start":0.0, "end":0.2, "probability":0.98 }, ...],
    "segments":[{ "avg_logprob":-0.4, "no_speech_prob":0.03, "compression_ratio":1.2 }]
  }
  ```
- Từ verbose_json tính acoustic features (server-side, như luyennoi):
  - `pronun.score` = confidence từ `avg_logprob` (chuẩn hóa → [0,1], cần calibration).
  - `fluency.score` = 1 giá trị từ speech rate + pause (càng thấp càng tốt, range ~1..6, cần calibration).
  - `noise` = `"cant_hear"` nếu `no_speech_prob` cao / quá ngắn.
  - `color_coded_transcript` từ `words[].probability`.
- **Fallback**: `STT_PROVIDER=auto` và queue quá tải → Groq `whisper-large-v3-turbo`.

### Bước 3 — 3 call LLM song song (`llm_service`, tiering model)

**Prompt 1 — Fluency (kèm phát hiện lạc đề):**
```
You are an IELTS examiner assessing Fluency & Coherence.
Question: {question}
Answer: {transcript}
Return exactly (no extra text):
relation : related|weakly-related|unrelated
reason : <1 câu tiếng Việt, chỉ ghi khi unrelated>
evidence : <trích dẫn ngắn>
Band : X.X
```

**Prompt 2 — Grammar:**
```
You are an IELTS examiner assessing Grammatical Range & Accuracy.
Answer: {transcript}
List every grammar error as: - "sai" -> "đúng" : giải thích ngắn (tiếng Việt)
Then output exactly: Band : X.X
```

**Prompt 3 — Vocab:**
```
You are an IELTS examiner assessing Lexical Resource.
Answer: {transcript}
Output exactly: Band : X.X
```

**Tiering model (xem mục 7):**

| Call | Tier `exam` (thi thử) | Tier `practice` (luyện tập) | Tier `budget` |
|---|---|---|---|
| Fluency | 70b | 70b | 8b |
| Grammar | 70b | 8b | 8b |
| Vocab | 8b | 8b | 8b |

> Fluency luôn 70b ở practice/exam vì đây là call quyết định **lạc đề** (zero toàn bộ điểm).

### Bước 4 — Aggregation (`scoring_service`)

Port nguyên từ `test-score.js` (xem `RESEARCH_LUYENNOI_SPEAKING.md`). Tóm tắt:

1. **Parse band**: `Band:\s*(\d+(\.\d+)?)` trên mỗi text LLM.
2. **Merge fluency** (`D`): `llm≤5 → llm`; else `round((acoustic+llm)/2)` (round **số nguyên**), `<7.5` cap 7, cuối `min(r, llm)` trừ ngoại lệ `llm≥7 && acoustic≥8`.
3. **Penalty (đúng thứ tự)**: cap pronun ≤7 nếu bất kỳ band {fluency,grammar,vocab} `<6` → trả lời quá ngắn (−1 mỗi band; ngưỡng **Part 2 ≤100 từ**, khác **≤20 từ**) → `cant_hear` zero pronun.
4. **Overall** = `floor(mean(band>0) × 2) / 2`.
5. **Lọc lỗi grammar 4 tầng** (parse `->`, dedup, bỏ dấu phẩy/lặp từ/"không tự nhiên", chỉ giữ lỗi có trong bài) — xem mục 4 của research doc.

### Output (lưu vào `submissions.result`)

```jsonc
{
  "transcript": "I went to the beach yesterday...",
  "noise": null,                       // null | "cant_hear"
  "is_relevant": true,                 // parse từ fluency "relation"
  "pronun":  { "score": 6.5 },
  "fluency": { "score": 6.5, "features": { "words_per_minute": 118, "pause_ratio": 0.12 } },
  "grammar": { "score": 6.0, "errors": [{ "error":"go", "correct":"went", "explain":"past tense" }] },
  "vocab":   { "score": 6.5 },
  "overall": 6.5,
  "color_coded_transcript": [{ "word":"beach", "color":"green", "score":87 }]
}
```

---

## 5. Writing (LLM JSON mode + OCR tùy chọn)

### Input — tạo đề
```jsonc
{ "skill":"writing", "writing_task_type":"task2", "content_text":"Some people think...", "title":"Task 2 - ..." }
```

### Input — nộp bài (3 cách)
```text
1. textbox: essay_text (đếm từ trực tiếp)
2. paste ảnh chụp: image_file → Groq OCR → essay_text
3. làm ra giấy (không nộp online)
```

### Xử lý
1. Nếu ảnh → `ocr_service`: `qwen/qwen3.6-27b` nhận base64, prompt *"Transcribe the handwritten English essay exactly, preserving paragraphs and punctuation."* → ghép text (≤5 ảnh/request, mỗi ảnh ≤20MB).
2. `writing_service` gọi `llama-3.3-70b-versatile` với `response_format={"type":"json_object"}`.

**Prompt chấm:**
```
System: You are a senior IELTS Writing examiner. Be strict and unbiased.
Return ONLY valid JSON, no markdown.

User:
Task type: {task1|task2}
Prompt: {question}
Essay: {essay}

Evaluate on 4 IELTS criteria (score 0-9, 0.5 increments):
{
  "task_response":      {"score": float, "feedback": "Vietnamese", "strengths": [str], "weaknesses": [str]},
  "coherence_cohesion": {"score": float, "feedback": "Vietnamese", "linkers_used": [str], "suggestions": [str]},
  "lexical_resource":   {"score": float, "feedback": "Vietnamese", "advanced_words": [str], "repetitions": [str]},
  "grammatical_accuracy":{"score": float, "feedback": "Vietnamese"},
  "errors": [{"original": str, "corrected": str, "type": str, "explain": "Vietnamese"}],
  "improved_sample": "English, ~1 band higher, natural"
}
Rules: word_count < 150 (task1) / < 250 (task2) → penalize task_response; feedback tiếng Việt; improved_sample tiếng Anh.
```

### Output

```jsonc
{
  "word_count": 245,
  "task_type": "task2",
  "overall": 6.5,
  "task_response":      { "score": 6.5, "feedback": "...", "strengths": [...], "weaknesses": [...] },
  "coherence_cohesion": { "score": 6.0, "feedback": "...", "linkers_used": [...], "suggestions": [...] },
  "lexical_resource":   { "score": 6.5, "feedback": "...", "advanced_words": [...], "repetitions": [...] },
  "grammatical_accuracy": { "score": 6.0, "feedback": "..." },
  "errors": [ { "original":"He go to school", "corrected":"He goes to school", "type":"subject-verb agreement", "explain":"..." } ],
  "improved_sample": "..."
}
```

- Tiêu chí: Task 1 → `task_response` = Task Achievement; Task 2 → = Task Response.

---

## 6. Quản lý lớp & nộp bài (logic)

- **Giáo viên**: `POST /classes` sinh `share_code` (6 ký tự, unique). Mọi thao tác giáo viên cần header `X-Teacher-Code` khớp `TEACHER_ACCESS_CODE`.
- **Học viên**: mở `GET /join?code=...` → nhập tên → làm bài → kết quả gắn `(assignment_id, student_name)`.
- **Chấm tay**: `PATCH /submissions/{id}` ghi đè `score`/`result` khi giáo viên không hài lòng với điểm AI.
- **Lịch sử**: `GET /classes/{id}/roster?name=...` lọc bài theo tên học viên.

---

## 7. Chi phí & thiết kế tiết kiệm (ngân sách ≤ 4M VND ≈ $160)

### 7.1 Cấu hình tiering LLM Speaking

Đơn giá Groq (đã xác nhận): `llama-3.3-70b-versatile` **$0.59 in / $0.79 out**; `llama-3.1-8b-instant` **$0.05 in / $0.08 out**.

Ước tính token/lượt (~1 phút nói ≈ 130 từ ≈ 180 token transcript; input mỗi call ~300 token):

| Call | Output | 70b / call | 8b / call |
|---|---|---|---|
| Fluency | ~150 | ~$0.00030 | ~$0.000027 |
| Grammar | ~300 | ~$0.00041 | ~$0.000039 |
| Vocab | ~100 | ~$0.00026 | ~$0.000023 |

| Cấu hình (fluency/grammar/vocab) | $/lượt | @ 180k lượt/tháng (60p/người × 100 × 30) |
|---|---|---|
| all-70b | ~$0.00097 | ~$175 |
| **exam** (70b/70b/8b) | ~$0.00073 | ~$132 |
| **practice** (70b/8b/8b) | ~$0.00036 | ~$65 |
| all-8b (budget) | ~$0.00009 | ~$16 |

### 7.2 Ngân sách (100 user, speaking 30–60p/người/ngày)

| Khoản | Loại | Chi phí/tháng |
|---|---|---|
| VPS Hetzner CX32 | Cố định | $7.5 |
| Domain (tùy chọn) | Cố định | $1 |
| Storage R2 (retention 90 ngày) | Biến đổi | ~$3 |
| Writing LLM (5 bài/ngày) + OCR | Biến đổi | ~$2 |
| **Tổng nền** | | **~$13.5** |
| Speaking LLM (tùy tier) | Biến đổi | $16–$132 |

**Kịch bản (100 user):**

| Dùng | Tier | Speaking LLM | Tổng | VND |
|---|---|---|---|---|
| 60p/người | practice | $65 | $78.5 | **~2.0M** ✅ |
| 60p/người | exam | $132 | $145.5 | **~3.6M** ✅ |
| 60p/người | all-70b | $175 | $188.5 | ~4.7M ❌ vượt |
| 30p/người | practice | $32 | $45.5 | ~1.1M ✅ |
| 50 user × 30p | practice | $16 | $29.5 | ~0.7M ✅ |

> **Kết luận:** với tiering, ngân sách 4M dư dả kể cả ở mức 60p/người/ngày. Chỉ cấu hình **all-70b** mới vượt ngân sách — vì vậy mặc định **practice**, chỉ dùng **exam** khi thi thử.

### 7.3 Quy tắc chọn tier (đề xuất)

| Ngữ cảnh | Tier | Lý do |
|---|---|---|
| Luyện tập Part 1/2/3 thường | `practice` (70b/8b/8b) | Fluency giữ 70b để bắt lạc đề; grammar/vocab 8b đủ dùng |
| Thi thử (FULL TEST / mock) | `exam` (70b/70b/8b) | Cần danh sách lỗi grammar chi tiết, chuẩn hơn |
| Ôn nhanh / trào lưu từ vựng | `budget` (all-8b) | Không cần độ chính xác cao |

### 7.4 Giới hạn & cơ chế chống vượt ngân sách (guardrail)

| Cơ chế | Mặc định | Hoạt động |
|---|---|---|
| `DAILY_SUBMIT_LIMIT_PER_STUDENT` | 40 lượt/ngày | Chặn nộp vượt (≈ 40 phút nói) |
| `MONTHLY_SPEND_CAP_USD` | $130 (~3.25M) | Theo dõi tổng chi Groq theo tháng |
| Cảnh báo | tại 80% cap | Ghi log / email giáo viên |
| Tự hạ tier | tại 90% cap | `exam` → `practice` |
| Tự hạ tier tiếp | tại 95% cap | `practice` → `budget` (all-8b) |
| Dừng chấm AI | tại 100% cap | Xếp hàng chờ tháng sau / giáo viên ghi đè |

### 7.5 Các cách tối ưu khác (đã áp dụng + dự phòng)

| Cách | Hiệu quả | Trạng thái |
|---|---|---|
| **STT self-host** (faster-whisper) thay API $0.04/giờ | −$90–120/tháng | ✅ áp dụng |
| **Tiering model** (8b cho grammar/vocab) | $175 → $65–132 | ✅ áp dụng |
| **Giới hạn & guardrail** (mục 7.4) | chặn vượt ngân sách | ✅ áp dụng |
| Nén Opus + retention 90 ngày | storage ~$3 | ✅ áp dụng |
| Cache kết quả chấm, không chấm lại khi xem | −10–20% | ✅ áp dụng |
| Giới hạn số lỗi grammar hiển thị (top 12) | giảm output token ~50% | ⬜ dự phòng |
| Groq prompt caching (prefix system prompt) | −5–10% input | ⬜ dự phòng |
| Groq Flex/Batch cho chấm lại không cần realtime | −10–30% | ⬜ dự phòng |
| Giảm retention audio 90 → 30 ngày | storage ~$1 | ⬜ dự phòng |
| Hạ luôn fluency về 8b khi khủng hoảng | $65 → $16 | ⬜ dự phòng |

---

## 8. Performance & giới hạn

| Khía cạnh | Đánh giá |
|---|---|
| Tải backend | 100 user, đa phần CRUD — 1 VPS 4 vCPU dư sức |
| STT worker | turbo int8 ~5–8× realtime trên 4 core → 100h/ngày ≈ 15–20 CPU-giờ/ngày, <20% CPU |
| LLM rate limit | 180k lượt/tháng ≈ 18k call/ngày, peak ~1k call/giờ — dưới Groq 1K RPM / 300K TPM |
| Latency chấm | STT ~10–15s/1-phút + 3 LLM song song (~1–2s) → <20s; chạy nền nên không block |
| Storage | 40–45GB audio/tháng → R2, retention 90 ngày ổn định ~135GB |

## 9. Bảo mật & dữ liệu

- Giảng viên: `TEACHER_ACCESS_CODE` (mã bí mật, đặt `.env`); không OAuth trừ khi cần.
- Học viên: không tài khoản; định danh bằng tên + `share_code` của lớp.
- `GET /assignments/{id}` **không trả `answer_key`**.
- R2: bucket riêng, public URL chỉ cho audio/file đề cần hiển thị; không public DB.
- Backup: pg_dump mỗi đêm lên R2 (giữ 7 bản).
