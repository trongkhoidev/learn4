
# Tài liệu phát triển — Nền tảng luyện 4 kỹ năng cho giáo viên

> Phiên bản: 2.0
> Định hướng: **chỉ giáo viên sử dụng** để giao bài cho lớp của mình — **không dùng để kinh doanh**.
> Phạm vi: **Reading · Listening · Speaking · Writing + Quản lý lớp & nộp bài**. Không có login/billing/token.

---

## Mục lục

0. [Phạm vi &amp; nguyên tắc](#0-phạm-vi--nguyên-tắc)
1. [Mô hình truy cập (không login/billing)](#1-mô-hình-truy-cập)
2. [Reading &amp; Listening — nhập đề từ file](#2-reading--listening)
3. [Speaking — clone luyennoi.com](#3-speaking)
4. [Writing — đẩy đề + chấm AI](#4-writing)
5. [Quản lý lớp &amp; nộp bài (giáo viên + học viên)](#5-quản-lý-lớp--nộp-bài)
6. [Data model](#6-data-model)
7. [Công nghệ &amp; chi phí](#7-công-nghệ--chi-phí)
8. [Giao diện đề xuất từng phần](#8-giao-diện-đề-xuất-từng-phần)

---

# 0. Phạm vi & nguyên tắc

| Nguyên tắc                                              | Mô tả                                                                                                                           |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Chỉ dùng AI cho**Speaking** và **Writing** | Reading/Listening không dùng model nào                                                                                         |
| Reading/Listening                                         | Nhập đề từ file hoặc bộ đề có sẵn, hiển thị để học viên đọc/nghe và nhập đáp án                            |
| Định dạng đáp án                                    | **Mặc định là text** — trắc nghiệm, TRUE/FALSE, điền từ đều nhập dưới dạng text                             |
| Số câu hỏi                                             | Giáo viên**chỉ chọn số lượng câu hỏi N**, học viên sẽ thấy N ô nhập đáp án tương ứng                   |
| Speaking                                                  | Clone**toàn bộ** tính năng + logic + output của luyennoi.com                                                           |
| Writing                                                   | Giáo viên đẩy nội dung đề; học viên gõ vào textbox**hoặc** paste ảnh chụp (OCR) **hoặc** làm ra giấy |
| Không login/billing                                      | Học viên vào bằng link lớp, nhập tên; không cần tài khoản, không tính phí                                           |

---

# 1. Mô hình truy cập

Vì không cần kinh doanh, bỏ hết phần auth phức tạp. Giữ một lớp định danh tối thiểu:

```text
Giáo viên  ──►  /teacher (mã giáo viên đơn giản, cấu hình trong .env)
                 ├─ tạo lớp → sinh link mời  /join?code=ABC123
                 ├─ tạo đề (Reading/Listening/Speaking/Writing)
                 └─ giao bài + xem kết quả

Học viên   ──►  mở link lớp → nhập tên (không cần tài khoản)
                 ├─ xem danh sách bài tập
                 └─ làm bài + nộp + xem kết quả (nếu được công bố)
```

- **Giáo viên**: truy cập bằng 1 mã bí mật đơn giản (`TEACHER_ACCESS_CODE` trong `.env`) hoặc Google OAuth có sẵn nếu muốn. Mặc định: mã bí mật.
- **Học viên**: không tài khoản. Mỗi lớp có `share_code`; học viên mở link, nhập tên, làm bài. Kết quả lưu theo `(assignment_id, student_name)`.
- **Không có** `UserTokenWallet`, `BillingPlan`, `SubscriptionRequest`, admin dashboard, guest trial.

---

# 2. Reading & Listening

**Không dùng AI.** Đề được đẩy lên, học viên xem và nhập đáp án (text).

## 2.1 Cách tạo đề (giáo viên)

Giáo viên tạo một **bài tập** thuộc kỹ năng Reading hoặc Listening với 2 cách đưa nội dung đề:

1. **Đẩy file** (PDF / ảnh chụp đề): hệ thống lưu file, hiển thị cho học viên xem (không cần parse).
2. **Dán text / chọn từ bộ đề có sẵn**: nội dung hiển thị dạng văn bản, tự format (xuống dòng, đánh số câu).

Sau khi có nội dung đề, giáo viên chỉ cần:

- **Nhập số lượng câu hỏi N** (vd: 40).
- (Tùy chọn) nhập **đáp án mẫu** `N` dòng để chấm tự động; nếu bỏ trống thì giáo viên chấm tay.
- (Listening) upload **file audio** để học viên nghe.

## 2.2 Làm bài (học viên)

Học viên mở bài tập → thấy đề (ảnh/text/audio) → thấy **N ô nhập đáp án** tương ứng với số câu giáo viên đã chọn → điền → nộp.

```text
┌─ Listening: Test 12 ───────────────────────────────┐
│ ▶ [======●=======] 02:34 / 08:00    (audio player) │
│ Đề (ảnh chụp / text):                              │
│  Section 1 …  Section 2 …  Section 3 …             │
├────────────────────────────────────────────────────┤
│ Đáp án:                                           │
│  1. [____________]  2. [____________]  3. [______] │
│  … (tự sinh đúng N ô theo số câu)                  │
│                                       [ Nộp bài ]  │
└────────────────────────────────────────────────────┘
```

## 2.3 Chấm điểm

- Có đáp án mẫu → chấm tự động: chuẩn hóa (lowercase, bỏ dấu câu, trim), so khớp từng ô. Trả ngay.
- Không có đáp án → để trạng thái "chờ chấm", giáo viên nhập điểm tay.
- Điểm hiển thị dạng `X/N` và (tùy chọn) quy đổi band theo bảng 40 câu → 9.0.

## 2.4 API

```text
POST   /api/v1/assignments                    # tạo bài tập (skill=reading|listening)
        body: { class_id, skill, title, question_count, content_text?, content_file?, answer_key?[], audio_file?(listening) }
GET    /api/v1/assignments/{id}               # học viên xem đề (không kèm answer_key)
POST   /api/v1/assignments/{id}/submit        # nộp { student_name, answers: ["A","TRUE","modern",...] }
GET    /api/v1/assignments/{id}/submissions   # giáo viên xem bài nộp + chấm tay
```

---

# 3. Speaking

Clone **toàn bộ** logic, cách hoạt động và format output của luyennoi.com (đã giải mã từ JS bundle của họ). Đây là phần quan trọng nhất.

## 3.1 Pipeline (1 call STT + 3 call LLM song song)

```text
audio ──► Groq Whisper (verbose_json)
           ├─ transcript + words[{word,start,end}]
           ├─ segments[{avg_logprob, no_speech_prob, compression_ratio}]
           │
           ├─(acoustic)──► fluency_acoustic (speech rate, pause ratio)
           │               pronunciation band (confidence → band, KHÔNG phoneme)
           │               noise = "cant_hear" nếu no_speech_prob cao / quá ngắn
           │
           └─(transcript)──► 3x Groq Llama-3.3 PARALLEL:
                             1) fluency → "relation:… / reason:… / evidence:… / Band: X.X"
                             2) grammar → "Band: X.X" + dòng "- \"sai\" -> \"đúng\" : giải thích"
                             3) vocab   → "Band: X.X"
                    │
                    └──► deterministic aggregation (backend) → 4 band + overall
```

## 3.2 Output (giống luyennoi)

```jsonc
{
  "transcript": "I went to the beach yesterday...",
  "noise": null,                      // null | "cant_hear"
  "is_relevant": true,                // parse từ fluency "relation"
  "pronun":  { "score": 6.5 },
  "fluency": { "score": 6.5 },        // merge acoustic + LLM
  "grammar": { "score": 6.0, "errors": [{ "error": "go", "correct": "went", "explain": "past tense" }] },
  "vocab":   { "score": 6.5 },
  "overall": 6.5,                     // floor(mean*2)/2
  "color_coded_transcript": [{ "word": "beach", "color": "green", "score": 87 }],
  "fluency_features": { "words_per_minute": 118, "pause_ratio": 0.12 }
}
```

## 3.3 Thuật toán chấm (port từ `test-score.js` của luyennoi)

1. **Parse band**: regex `Band:\s*(\d+(\.\d+)?)` trên mỗi text LLM (grammar, vocab, fluency).
2. **Merge fluency** (hàm `D` của luyennoi): `llm≤5 → llm`; ngược lại `(acoustic+llm)/2`, `<7.5` thì cap 7, cuối cap tại `llm`.
3. **Penalty (theo thứ tự)**: `relation: unrelated` → tất cả 0; trả lời quá ngắn → −1 mỗi band; `noise=="cant_hear"` → pronun 0; bất kỳ band nào trong {fluency,grammar,vocab} `<6` → cap pronun 7.
4. **Overall** = `floor(mean(band > 0) × 2) / 2`.

## 3.4 Band pronunciation (không cần phoneme)

- Chuẩn hóa `avg_logprob` (≈ −1.5..0) → confidence ∈ [0,1].
- Map band: `3 + (conf − low)/(high − low) × 6` (khởi tạo `low=0.483, high=0.85`, hiệu chỉnh trên mẫu thật).
- Color-code từ: xanh ≥0.8 / vàng ≥0.6 / đỏ <0.6.

## 3.5 Band fluency (acoustic)

- `speech_rate = số từ / thời gian nói`, `pause_ratio = thời gian ngắt / tổng` (từ word timestamps).
- Map band 4–9 rồi merge với LLM band ở 3.3.

## 3.6 Prompt 3 call LLM (Groq `llama-3.3-70b-versatile`)

**Fluency** (gồm phát hiện lạc đề):

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

**Grammar**:

```
You are an IELTS examiner assessing Grammatical Range & Accuracy.
Answer: {transcript}
List every grammar error as: - "sai" -> "đúng" : giải thích ngắn (tiếng Việt)
Then output exactly: Band : X.X
```

**Vocab**:

```
You are an IELTS examiner assessing Lexical Resource.
Answer: {transcript}
Output exactly: Band : X.X
```

## 3.7 Đối chiếu dự án hiện tại

- **Xóa**: `gatekeeper_service.py`, `azure_service.py`, `deepgram_service.py`.
- **Mới**: `services/groq_stt_service.py`.
- **Viết lại**: `llm_service.py` (3 call marker-style), `scoring_service.py` (thuật toán 3.3), `assessment_service.py` (orchestration), `models/assessment.py`/`audio.py`.
- **Frontend**: sửa `FeedbackPanel`, `ReasoningCards`; bỏ `AzureDashboard`, `ModelAnswer`.
- **Tái dùng**: `audio_preprocessor`, `blob_service` (upload audio), `AudioRecorder`, `WaveformVisualizer`, `useMediaRecorder`.

---

# 4. Writing

Dùng LLM chấm theo 4 tiêu chí IELTS. Tham khảo **Cambridge Write & Improve** (viết → chấm → góp ý → sửa → chấm lại).

## 4.1 Cách tạo đề (giáo viên)

Giáo viên tạo bài tập Writing: nhập/đẩy nội dung đề (Task 1 hoặc Task 2), kèm yêu cầu số từ. Học viên có 3 cách:

1. **Gõ vào textbox** (editor, đếm từ trực tiếp).
2. **Paste ảnh chụp** bài viết tay → hệ thống OCR → text → chấm AI.
3. **Chỉ xem đề, làm ra giấy** (không nộp online).

## 4.2 Luồng

```text
Đề Writing ─► học viên gõ / paste ảnh / làm giấy
   │
   ├─ textbox ──► text
   └─ ảnh chụp ─► Groq OCR (qwen/qwen3.6-27b) ─► text
            │
            └──► Groq Llama-3.3 (chấm 4 tiêu chí, JSON) ─► điểm + feedback + lỗi
```

## 4.3 Tiêu chí chấm

|     | Task 1                       | Task 2                       |
| --- | ---------------------------- | ---------------------------- |
| TC1 | Task Achievement             | Task Response                |
| TC2 | Coherence & Cohesion         | Coherence & Cohesion         |
| TC3 | Lexical Resource             | Lexical Resource             |
| TC4 | Grammatical Range & Accuracy | Grammatical Range & Accuracy |

## 4.4 Output

```jsonc
{
  "word_count": 245,
  "task_type": "task2",
  "overall": 6.5,
  "task_response":      { "score": 6.5, "feedback": "...", "strengths": [...], "weaknesses": [...] },
  "coherence_cohesion": { "score": 6.0, "feedback": "...", "linkers_used": [...], "suggestions": [...] },
  "lexical_resource":   { "score": 6.5, "feedback": "...", "advanced_words": [...], "repetitions": [...] },
  "grammatical_accuracy": { "score": 6.0, "feedback": "..." },
  "errors": [ { "original": "He go to school", "corrected": "He goes to school", "type": "subject-verb agreement", "explain": "..." } ],
  "improved_sample": "..."
}
```

## 4.5 Prompt chấm (Groq, JSON mode)

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

Gọi với `response_format={"type":"json_object"}` (Llama-3.3 hỗ trợ).

## 4.6 OCR ảnh chụp (Groq vision)

Model `qwen/qwen3.6-27b`, nhận ảnh dạng base64/URL, trả text:

```
Model: qwen/qwen3.6-27b
Message: [ {type: text, text: "Transcribe the handwritten English essay in this image exactly, preserving paragraphs and punctuation."},
           {type: image_url, image_url: {url: "data:image/jpeg;base64,..."}} ]
```

- Lưu ý: ảnh ≤ 20MB, tối đa 5 ảnh/request. Nếu bài viết dài nhiều ảnh → OCR từng ảnh rồi ghép text.

## 4.7 Websites tham khảo

- **Cambridge Write & Improve** (`writeandimprove.com`): chấm tự động theo CEFR, cho feedback, "sửa và chấm lại". → clone luồng này.
- **writing9.com / ieltsliz.com**: kho đề Task 1/2 + bài mẫu → tham khảo cấu trúc đề và bài mẫu.

---

# 5. Quản lý lớp & nộp bài

## 5.1 Giáo viên

```text
Tạo lớp → sinh link mời → học viên vào bằng tên
   ├─ Tạo bài tập (Reading/Listening/Speaking/Writing)
   ├─ Giao cho lớp
   ├─ Xem bảng kết quả (điểm từng học viên)
   ├─ Chấm tay (khi không có đáp án / điểm AI chưa hài lòng)
   └─ Nghe lại ghi âm Speaking / đọc bài Writing / xem đáp án Reading
```

## 5.2 Học viên

```text
Mở link lớp → nhập tên
   ├─ Xem danh sách bài tập
   ├─ Làm bài (theo giao diện từng kỹ năng ở mục 8)
   ├─ Nộp bài
   └─ Xem lại lịch sử + kết quả của mình
```

## 5.3 API

```text
# Lớp
POST   /api/v1/classes                      # tạo lớp
GET    /api/v1/classes/{id}                 # chi tiết + link mời
GET    /api/v1/join?code=...                # học viên nhập tên để vào lớp

# Bài tập (chung 4 kỹ năng)
POST   /api/v1/assignments                  # tạo bài tập (skill, đề, question_count, audio…)
GET    /api/v1/classes/{id}/assignments     # danh sách bài tập trong lớp
GET    /api/v1/assignments/{id}             # học viên xem đề

# Nộp bài & kết quả
POST   /api/v1/assignments/{id}/submit      # nộp (đáp án / audio / essay / ảnh)
GET    /api/v1/assignments/{id}/submissions # giáo viên xem toàn bộ bài nộp
GET    /api/v1/submissions/{id}             # chi tiết 1 bài nộp (kết quả, feedback)
GET    /api/v1/classes/{id}/roster?name=... # học viên xem lịch sử của mình
```

---

# 6. Data model

```text
classes
  id (uuid), name, share_code (unique), teacher_note, created_at

assignments
  id (uuid), class_id (fk), skill (enum: reading|listening|speaking|writing),
  title, question_count (int),           -- đếm số câu → sinh N ô đáp án
  content_text (text|null),              -- đề dạng text (dán/soạn)
  content_file_url (text|null),          -- đề dạng file ảnh/PDF
  audio_url (text|null),                 -- listening
  answer_key (jsonb|null),               -- ["A","TRUE","modern",...] để chấm tự động
  deadline (timestamp|null), created_at

submissions
  id (uuid), assignment_id (fk), student_name,
  answers (jsonb|null),                  -- reading/listening: ["A","TRUE",...]
  audio_url (text|null),                 -- speaking
  transcript (text|null),                -- speaking
  result (jsonb|null),                   -- kết quả chấm (speaking/writing JSON)
  essay_text (text|null),                -- writing (textbox/OCR)
  image_url (text|null),                 -- writing (ảnh chụp)
  score (float|null),                    -- điểm tổng (reading/listening) hoặc overall
  status (enum: pending|graded), submitted_at
```

Lưu ý: giữ bảng hiện có `Question`/`Topic`/`ExamSet` làm **bộ đề có sẵn** cho Speaking (Forecast). Bỏ các bảng `UserTokenWallet`, `BillingPlan`, `SubscriptionRequest`, `TokenAllocation`, `GuestTrial` nếu không cần.

---

# 7. Công nghệ & chi phí

| Thành phần       | Lựa chọn                                           | Chi phí            |
| ------------------ | ---------------------------------------------------- | ------------------- |
| Frontend           | React + Vite + Tailwind (giữ nguyên)               | 0                   |
| Backend            | FastAPI (giữ nguyên)                               | 0 (host tùy chọn) |
| DB                 | PostgreSQL (Neon/Supabase free) hoặc giữ Azure SQL | free tier           |
| Storage            | Cloudflare R2 (audio + file đề + ảnh)             | free 10GB           |
| STT                | Groq`whisper-large-v3-turbo`                       | $0.04/giờ audio    |
| LLM                | Groq`llama-3.3-70b-versatile`                      | rẻ, nhanh          |
| OCR (Writing ảnh) | Groq`qwen/qwen3.6-27b` (vision)                    | theo token          |

**Chỉ Speaking + Writing tốn AI.** Reading/Listening hoàn toàn free. So với pipeline cũ (Azure Speech $1.40/giờ + Deepgram + reasoner LLM), chi phí giảm ~90%.

## Tối ưu thêm

- 3 call LLM Speaking chạy song song → chỉ đợi call chậm nhất.
- Cache transcript + kết quả chấm vào DB, không chấm lại khi chỉ xem.
- Chấm không đồng bộ (background task) nếu lớp đông nộp cùng lúc.

---

# 8. Giao diện đề xuất từng phần

## 8.1 Giáo viên — Tạo lớp & giao bài

```
┌─ Lớp: IELTS 7.0 (link: …/join?code=ABC123) ─────────────┐
│ [+ Bài tập mới]                                          │
│  Loại: [Reading ▾] [Listening ▾] [Speaking ▾] [Writing ▾]│
├──────────────────────────────────────────────────────────┤
│ Bài tập:                                                 │
│  #1 Listening Test 12   · 40 câu  · audio ✓  [Xem]      │
│  #2 Speaking Forecast P1  · Part 1/2/3     [Xem]        │
│  #3 Writing Task 2      · đề "Some people…"  [Xem]      │
└──────────────────────────────────────────────────────────┘
```

## 8.2 Giáo viên — Tạo đề Reading/Listening

```
┌─ Tạo bài tập Listening ─────────────────┐
│ Tiêu đề: [Test 12                  ]    │
│ Số câu hỏi: [40]                        │
│ Nội dung đề:  ○ Đẩy file  ○ Dán text    │
│   [ Chọn file PDF/ảnh ]                 │
│ Audio: [ Upload mp3 ] (chỉ Listening)   │
│ Đáp án (tùy chọn, để chấm tự động):     │
│   [40 dòng: A / TRUE / modern …]        │
│            [ Lưu ]                      │
└─────────────────────────────────────────┘
```

## 8.3 Giáo viên — Tạo đề Speaking / Writing

```
┌─ Tạo bài tập Speaking ─────────────────┐
│ Tiêu đề: [Forecast P1 - P3        ]    │
│ Part 1: [topic + câu hỏi]              │
│ Part 2: [cue card + bullets]           │
│ Part 3: [câu hỏi follow-up]            │
│        [ Lưu ]                         │
└────────────────────────────────────────┘
┌─ Tạo bài tập Writing ──────────────────┐
│ Tiêu đề: [Task 2 - Some people…   ]    │
│ Task: [Task 1 ▾ / Task 2 ▾]           │
│ Đề: [ textarea ]                       │
│ Số từ tối thiểu: [250]                 │
│        [ Lưu ]                         │
└────────────────────────────────────────┘
```

## 8.4 Học viên — Làm bài Reading/Listening

```
┌─ Listening: Test 12 ───────────────────────────────┐
│ ▶ [=========●=======] 02:34 / 08:00               │
│ [ ảnh đề / văn bản đề hiển thị đầy đủ ]           │
├────────────────────────────────────────────────────┤
│ 1. [_______]  2. [_______]  3. [_______]  … 40.   │
│                                    [ Nộp bài ]     │
└────────────────────────────────────────────────────┘
```

## 8.5 Học viên — Làm bài Speaking (clone luyennoi)

```
Part 1 · Topic: Hometown
"What is your hometown like?"
        🎙 [Bắt đầu]
─────────────────────────────
00:13  🔴 Đang ghi…  ~~~~/\/\/\~~~~  [Dừng]
─────────────────────────────
Kết quả:
  Pronun 6.5 · Fluency 6.5 · Vocab 6.0 · Grammar 6.5
  Overall 6.5
  Transcript (từ tô xanh/vàng/đỏ)
  Grammar: ❌ "go" → ✓ "went" (past tense)
  Vocab: gợi ý từ nâng cao · Fluency: 118 wpm · pause 12%
```

## 8.6 Học viên — Làm bài Writing

```
┌─ Writing Task 2 ──────────────────────────────────┐
│ Đề: "Some people think…"          Từ: 245 / 250   │
│ [ editor / textarea viết bài ]                    │
│  Hoặc: [ 📎 Paste ảnh chụp bài viết tay ]         │
│  Hoặc: làm ra giấy (không nộp online)             │
├───────────────────────────────────────────────────┤
│                    [ Chấm bài ]                   │
│ Overall 6.5 · TR 6.5 · CC 6.0 · LR 6.5 · GRA 6.0 │
│ Lỗi (highlight trong bài) + improved_sample       │
└───────────────────────────────────────────────────┘
```

## 8.7 Học viên — Lịch sử & kết quả

```
┌─ Kết quả của tôi (Minh Anh) ──────────────────────┐
│ 20/8 Speaking P2   Overall 6.5   [Xem]            │
│ 19/8 Writing T2    Overall 6.0   [Xem]            │
│ 18/8 Listening     Score 30/40    [Xem]           │
└───────────────────────────────────────────────────┘
```

---

## Lộ trình triển khai

1. **Speaking core** (giá trị cao nhất): `groq_stt_service` + `llm_service` + `scoring_service` + `assessment_service` + frontend feedback.
2. **Writing**: `writing_service` (prompt + JSON) + OCR (`qwen3.6-27b`) + UI (textbox + paste ảnh).
3. **Reading/Listening**: model + nộp đáp án N ô + UI nhập đề (giáo viên) + UI làm bài (học viên).
4. **Lớp & nộp bài**: `classes`/`assignments`/`submissions` + link mời + bảng điểm + lịch sử.
5. **Hiệu chỉnh**: calibration pronunciation/fluency, test thật, tối ưu prompt.
