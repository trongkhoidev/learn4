etvi

# Kế hoạch triển khai dự án — LexiLearn (Nền tảng luyện 4 kỹ năng cho giáo viên)

> Phiên bản: 2.0 — đi kèm `PLAN_TECH_LOGIC_COST.md`, `PLAN_SPEAKING_MVP.md`, `RESEARCH_LUYENNOI_SPEAKING.md`, `LexiLearn_Teacher_Platform_Spec.md`
> Phạm vi: Reading · Listening · Speaking · Writing + Quản lý lớp & nộp bài.
> **MVP đầu tiên: Speaking** (xem `PLAN_SPEAKING_MVP.md`).
> Định hướng: dùng nội bộ (~100 user), không kinh doanh, tối ưu chi phí tối đa.

---

## 1. Tổng quan & phạm vi

- **Mục tiêu**: nền tảng giáo viên giao bài cho lớp; học viên vào bằng link + tên, không tài khoản.
- **Không có**: login/billing/token, admin dashboard, guest trial.
- **AI chỉ dùng cho Speaking & Writing**; Reading/Listening là CRUD thuần (chấm text).
- **Ngân sách tối đa**: **≤ 4 triệu VND/tháng (~$160)** cho 100 user; dự kiến thực tế ~2–3.6 triệu VND/tháng nhờ tiering model + guardrail.

### Quyết định công nghệ đã chốt (tóm tắt)

| Quyết định        | Lựa chọn                                                                                     |
| -------------------- | ---------------------------------------------------------------------------------------------- |
| STT Speaking         | **Self-host `faster-whisper-large-v3-turbo` (int8)** trên VPS; Groq API làm fallback |
| LLM Speaking         | **Tiering**: `exam` = 70b/70b/8b · `practice` = 70b/8b/8b · `budget` = all-8b    |
| LLM Writing          | `llama-3.3-70b-versatile` (JSON mode, 1 call)                                                |
| OCR (ảnh viết tay) | Groq`qwen/qwen3.6-27b` (tùy chọn, model name trong `.env`)                               |
| Backend              | FastAPI (monolith) + worker chấm nền                                                         |
| Frontend             | React + Vite + Tailwind                                                                        |
| DB                   | PostgreSQL (chạy trong VPS)                                                                   |
| Storage              | Cloudflare R2 (audio + file đề + ảnh)                                                       |
| Server               | Hetzner CX32 (4 vCPU / 8GB) — chạy app + Postgres + STT worker                               |

---

## 2. Nguyên tắc triển khai

1. **Monolith backend** — không microservice, không message queue riêng (in-memory queue là đủ cho 100 user).
2. **Chấm không đồng bộ** — Speaking/Writing chạy background task, trả `pending` rồi `graded`.
3. **Cache kết quả chấm** vào DB — không chấm lại khi chỉ xem.
4. **Model AI để trong `.env`** — đổi model/fallback không cần sửa code.
5. **Guardrail ngân sách** — theo dõi tổng chi Groq, tự hạ tier/dừng khi chạm cap (mục 7.4 trong `PLAN_TECH_LOGIC_COST.md`).
6. **Mọi thứ chạy được bằng `docker compose up`** — một lệnh deploy.

---

## 3. Kiến trúc tổng thể

```text
                          ┌───────────────────────────────────────────────┐
                          │           VPS (Hetzner CX32, 4vCPU/8GB)       │
                          │                                               │
  Browser ── HTTPS ──────►│  nginx (static React + reverse proxy)         │
  (teacher /join)         │        │                                      │
                          │        ▼                                      │
                          │  FastAPI (app) ──► PostgreSQL (Docker)        │
                          │     │  ├─ CRUD classes/assignments/submissions│
                          │     │  ├─ chấm text Reading/Listening         │
                          │     │  └─ orchestrate Speaking/Writing        │
                          │     │                                         │
                          │     ├─► STT worker (faster-whisper turbo)     │
                          │     └─► Groq API (LLM 70b + OCR, fallback STT)│
                          └───────────────┬───────────────────────────────┘
                                          │
                                          ▼
                              Cloudflare R2 (audio + file đề + ảnh)
```

**Luồng Speaking (self-host STT):** audio → FFmpeg nén Opus → upload R2 → STT worker (faster-whisper, verbose_json) → 3× Groq LLM song song → scoring (backend) → lưu kết quả → trả về frontend.
**Fallback:** nếu STT worker lỗi/quá tải → gọi Groq `whisper-large-v3-turbo` API.

---

## 4. Cấu trúc thư mục

```text
learn4/
├─ README.md                       # tổng quan + chỉ mục tài liệu + quickstart
├─ PLAN_IMPLEMENTATION.md          # file này
├─ PLAN_TECH_LOGIC_COST.md         # công nghệ + logic + I/O + chi phí
├─ PLAN_SPEAKING_MVP.md            # kế hoạch MVP Speaking (thứ tự triển khai chi tiết)
├─ RESEARCH_LUYENNOI_SPEAKING.md   # thuật toán chấm gốc đã decode từ luyennoi
├─ LexiLearn_Teacher_Platform_Spec.md
├─ backend/
│  ├─ app/
│  │  ├─ main.py                   # FastAPI entry, CORS, mount routers, startup load model
│  │  ├─ config.py                 # đọc .env (pydantic-settings)
│  │  ├─ db.py                     # SQLAlchemy engine/session
│  │  ├─ deps.py                   # dependencies (get_db, verify_teacher)
│  │  ├─ models/                   # SQLAlchemy ORM
│  │  │  ├─ __init__.py
│  │  │  ├─ class_.py              # Class
│  │  │  ├─ assignment.py          # Assignment
│  │  │  ├─ submission.py          # Submission
│  │  │  └─ topic.py               # Question/Topic/ExamSet (bộ đề Forecast)
│  │  ├─ schemas/                  # Pydantic DTO
│  │  │  ├─ class_.py / assignment.py / submission.py / speaking.py / writing.py
│  │  ├─ routers/
│  │  │  ├─ teacher.py             # /api/v1/teacher/* (CRUD lớp, đề, chấm tay)
│  │  │  ├─ classes.py             # /api/v1/classes, /join
│  │  │  ├─ assignments.py         # /api/v1/assignments
│  │  │  └─ submissions.py         # /api/v1/submissions, roster
│  │  ├─ services/
│  │  │  ├─ stt_service.py         # self-host faster-whisper + Groq fallback
│  │  │  ├─ llm_service.py         # 3 call speaking (parallel) + writing JSON mode
│  │  │  ├─ scoring_service.py     # ✅ port luyennoi (parse/merge/penalty/overall/grammar)
│  │  │  ├─ acoustic.py            # ✅ feature acoustic (confidence/disfluency/noise) — cần calibrate
│  │  │  ├─ assessment_service.py  # orchestrate Speaking pipeline
│  │  │  ├─ writing_service.py     # prompt 4 tiêu chí + parse JSON
│  │  │  ├─ ocr_service.py         # Groq vision (ảnh viết tay)
│  │  │  ├─ grading_service.py     # chấm text Reading/Listening (normalize so khớp)
│  │  │  ├─ blob_service.py        # upload/download R2
│  │  │  ├─ audio_processor.py     # FFmpeg: nén, chuẩn hóa sample rate
│  │  │  └─ queue.py               # in-memory background queue
│  │  └─ tests/                    # pytest
│  │     ├─ test_scoring.py        # ✅ unit test scoring (16 test)
│  │     ├─ test_grading.py        # unit test chấm text
│  │     └─ test_api.py            # smoke test các router
│  ├─ requirements.txt / pyproject.toml
│  └─ Dockerfile
├─ frontend/
│  ├─ src/
│  │  ├─ pages/
│  │  │  ├─ Teacher/               # Dashboard, ClassDetail, AssignmentBuilder, Grading
│  │  │  └─ Student/               # Join, AssignmentList, DoAssignment, History
│  │  ├─ components/
│  │  │  ├─ AudioRecorder.tsx
│  │  │  ├─ WaveformVisualizer.tsx
│  │  │  ├─ FeedbackPanel.tsx      # 4 band + overall
│  │  │  ├─ ReasoningCards.tsx     # grammar errors / vocab suggestions
│  │  │  ├─ AnswerGrid.tsx         # N ô đáp án Reading/Listening
│  │  │  ├─ WritingEditor.tsx      # textbox + đếm từ + paste ảnh
│  │  │  └─ ScoreBoard.tsx         # bảng điểm lớp
│  │  ├─ hooks/useMediaRecorder.ts, useJoinSession.ts
│  │  └─ api/client.ts             # fetch wrapper
│  ├─ vite.config.ts / tailwind.config.js / package.json
│  └─ Dockerfile (build → nginx)
├─ docker-compose.yml              # nginx + backend + postgres
├─ .env.example
└─ deploy/                         # script + systemd/crontab backup
   ├─ backup.sh                    # pg_dump + R2 sync
   └─ README.md                    # hướng dẫn deploy VPS
```

---

## 5. Data model

```text
classes
  id (uuid pk), name, share_code (unique), teacher_note, created_at

assignments
  id (uuid pk), class_id (fk), skill (reading|listening|speaking|writing),
  title, question_count (int),
  content_text (text|null), content_file_url (text|null),
  audio_url (text|null),               -- listening
  answer_key (jsonb|null),             -- ["A","TRUE","modern",...]
  speaking_parts (jsonb|null),         -- {part1, part2, part3}
  writing_task_type (task1|task2|null),
  deadline (timestamp|null), created_at

submissions
  id (uuid pk), assignment_id (fk), student_name,
  answers (jsonb|null),                -- reading/listening
  audio_url (text|null), transcript (text|null),   -- speaking
  essay_text (text|null), image_url (text|null),   -- writing
  result (jsonb|null),                 -- kết quả chấm (speaking/writing JSON)
  score (float|null),                  -- tổng / overall
  status (pending|graded), submitted_at

topics / questions / exam_sets        -- bộ đề Forecast Speaking (giữ từ thiết kế cũ)
```

- Giữ bảng `Question/Topic/ExamSet` làm kho đề Speaking.
- Bỏ hết: `UserTokenWallet`, `BillingPlan`, `SubscriptionRequest`, `TokenAllocation`, `GuestTrial`.

---

## 6. API endpoints

```text
# Lớp (giáo viên)
POST   /api/v1/classes                          # tạo lớp → sinh share_code
GET    /api/v1/classes/{id}                     # chi tiết + link mời
GET    /api/v1/join?code=...                    # học viên xác nhận tên vào lớp

# Bài tập
POST   /api/v1/assignments                      # tạo đề 4 kỹ năng
GET    /api/v1/classes/{id}/assignments         # danh sách bài tập
GET    /api/v1/assignments/{id}                 # học viên xem đề (KHÔNG kèm answer_key)

# Nộp & kết quả
POST   /api/v1/assignments/{id}/submit          # nộp (answers/audio/essay/ảnh) → 202 pending
GET    /api/v1/assignments/{id}/submissions     # giáo viên xem toàn bộ bài nộp
PATCH  /api/v1/submissions/{id}                 # giáo viên chấm tay / sửa điểm
GET    /api/v1/submissions/{id}                 # chi tiết (kết quả + feedback)
GET    /api/v1/classes/{id}/roster?name=...     # học viên xem lịch sử của mình
```

Quy ước: tất cả route dưới `/api/v1/`; giảng viên gửi header `X-Teacher-Code: {TEACHER_ACCESS_CODE}`.

---

## 7. Lộ trình triển khai

> **MVP = Speaking.** Giai đoạn 0 + 1 làm trước; thứ tự chi tiết bên trong giai đoạn 1
> (scoring → stt → calibration → llm → assessment → frontend) nằm ở `PLAN_SPEAKING_MVP.md` mục 6.

| Giai đoạn                           | Nội dung                                                                                                                                                                                                                              | Tiêu chí hoàn thành                                                                      | Ước lượng |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------------- |
| **0. Khung**                    | Scaffold backend+frontend, docker-compose, config/env, DB models, blob_service, audio_processor                                                                                                                                        | `docker compose up` OK; healthcheck; migrate DB                                            | 1–2 ngày    |
| **1. Speaking core (MVP)**      | `scoring_service` (✅ đã code + 16 test), `stt_service` (self-host + fallback), calibration, `llm_service` (3 call song song + tiering), `assessment_service`, guardrail ngân sách, `FeedbackPanel` + `ReasoningCards` | unit test scoring khớp code gốc luyennoi; chấm 1 audio thật; calibration trên ≥15 mẫu | 5–6 ngày    |
| **2. Writing**                  | `writing_service` (JSON mode) + `ocr_service` + `WritingEditor` (textbox/đếm từ/paste ảnh)                                                                                                                                   | chấm 1 essay thật, JSON đúng schema                                                      | 2–3 ngày    |
| **3. Reading/Listening**        | chấm text`grading_service` + UI tạo đề (file/text/audio) + `AnswerGrid` N ô                                                                                                                                                   | tạo đề → nộp → chấm X/N tự động                                                    | 2–3 ngày    |
| **4. Lớp & nộp bài**         | router classes/join/submissions, link mời,`ScoreBoard`, lịch sử, chấm tay                                                                                                                                                        | flow GV→HS→nộp→kết quả end-to-end                                                      | 2–3 ngày    |
| **5. Hiệu chỉnh & hardening** | calibration pronun/fluency, test thật 10+ mẫu, backup, retention, monitoring                                                                                                                                                         | band ổn định; deploy VPS go-live                                                          | 2–3 ngày    |

**Tổng ước lượng ~2–3 tuần** (1 dev). Thứ tự ưu tiên theo giá trị: Speaking trước (phần phức tạp và giá trị cao nhất).

---

## 8. Môi trường & cấu hình (`.env`)

```env
# App
TEACHER_ACCESS_CODE=changeme
DATABASE_URL=postgresql+psycopg://lexi:lexi@postgres:5432/lexilearn
CORS_ORIGINS=http://localhost:5173,https://your-domain.com

# Storage (R2 — S3-compatible)
R2_ENDPOINT_URL=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET=lexilearn
R2_PUBLIC_URL=...            # CDN/public bucket URL

# AI — Groq (LLM + OCR + STT fallback)
GROQ_API_KEY=...
GROQ_STT_MODEL=whisper-large-v3-turbo        # fallback STT
GROQ_MODEL_70B=llama-3.3-70b-versatile
GROQ_MODEL_8B=llama-3.1-8b-instant
GROQ_WRITING_MODEL=llama-3.3-70b-versatile
GROQ_OCR_MODEL=qwen/qwen3.6-27b

# Speaking tiering (fluency/grammar/vocab)
TIER_EXAM=70b,70b,8b                         # thi thử / mock test
TIER_PRACTICE=70b,8b,8b                      # luyện tập thường (mặc định)
TIER_BUDGET=8b,8b,8b                         # ôn nhanh / tiết kiệm tối đa

# STT self-host
WHISPER_MODEL=turbo                          # faster-whisper large-v3-turbo (int8)
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
STT_PROVIDER=selfhost                        # selfhost | groq | auto

# Retention & guardrail ngân sách
AUDIO_RETENTION_DAYS=90                      # xoá audio sau 90 ngày
MAX_AUDIO_SECONDS=600
DAILY_SUBMIT_LIMIT_PER_STUDENT=40            # chặn nộp vượt (≈40 phút nói/ngày)
MONTHLY_SPEND_CAP_USD=130                    # cap tổng chi Groq/tháng (~3.25M VND)
# hành vi khi chạm cap: 80% cảnh báo → 90% exam→practice → 95% practice→budget → 100% dừng
```

---

## 9. Deployment

### 9.1 Server (VPS Hetzner CX32 — 4 vCPU / 8GB / 80GB SSD)

```bash
# một lần
apt update && apt install -y docker.io docker-compose-plugin nginx
# copy repo, tạo .env từ .env.example
docker compose up -d --build
```

- **nginx** trên host: chấm HTTPS (Let's Encrypt), serve static frontend, proxy `/api` → backend.
- **Cloudflare (free)** trước domain: cache static + HTTPS + chống DDoS.
- **Postgres + FastAPI + STT worker** chạy chung trong compose.

### 9.2 Storage (Cloudflare R2)

- Bucket `lexilearn`: `audio/{submission_id}.opus`, `assignments/{id}/...`, `writing/{id}.jpg`.
- Audio nén **Opus 24kbps mono** (~0.25MB/phút) bằng FFmpeg ngay khi upload.
- **Retention 90 ngày**: cron/worker xoá audio cũ, giữ vĩnh viễn transcript + kết quả.

### 9.3 Backup & monitoring

- **DB**: `pg_dump` mỗi đêm → R2 (giữ 7 bản gần nhất) — `deploy/backup.sh` + crontab.
- **R2**: object versioning bật cho bucket.
- **Monitoring (free)**: UptimeRobot ping healthcheck; Sentry free tier bắt lỗi backend.

---

## 10. Chiến lược test

| Loại            | Phạm vi                                                                                                                                                  | Công cụ      |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------- |
| Unit             | `scoring_service` (thuật toán 3.3: parse band, merge fluency, penalty, overall) — test đúng từng nhánh; `grading_service` (normalize so khớp) | pytest         |
| Unit frontend    | `AnswerGrid` sinh đúng N ô; đếm từ `WritingEditor`                                                                                              | Vitest         |
| Smoke API        | tạo lớp → tạo đề → nộp → chấm (mock Groq/STT)                                                                                                   | pytest + httpx |
| E2E (thủ công) | 4 kỹ năng end-to-end trên bản deploy thật                                                                                                            | checklist      |

- **Mock Groq/STT trong test** để không tốn API/CPU; riêng giai đoạn 5 chạy **sample thật** để calibration.

---

## 11. Rủi ro & giảm thiểu

| Rủi ro                                                            | Mức  | Giảm thiểu                                                                      |
| ------------------------------------------------------------------ | ----- | --------------------------------------------------------------------------------- |
| `qwen3.6-27b` (OCR) là preview model, có thể bị đổi/ngưng | Trung | model name trong`.env`; fallback: `llama-3.3-70b` vision hoặc Tesseract free |
| Self-host STT chậm khi lớp nộp đồng loạt                     | Trung | in-memory queue +`STT_PROVIDER=auto` failover sang Groq                         |
| Calibration band pronun/fluency lệch do STT self-host (int8)      | Trung | hiệu chỉnh`low/high` trên mẫu thật (giai đoạn 5)                         |
| Chất lượng chấm LLM không ổn định                          | Thấp | prompt chuẩn hoá +`response_format=json_object` + retry 1 lần                |
| Vượt ngân sách 4M khi dùng tăng đột biến                  | Trung | guardrail: cap $130 + auto-hạ tier + limit lượt/ngày                          |
| VPS đầy ổ (audio)                                               | Thấp | audio đẩy R2, retention 90 ngày, báo dung lượng                             |

---

## 12. Checklist trước go-live

- [ ] `.env` thật (đổi `TEACHER_ACCESS_CODE`, R2 keys, Groq key)
- [ ] HTTPS + Cloudflare bật
- [ ] Backup DB chạy đúng lịch (thử restore 1 lần)
- [ ] Retention cron hoạt động
- [ ] STT self-host load model OK khi boot; fallback Groq test được
- [ ] Chấm 4 kỹ năng end-to-end bằng tài khoản thật
- [ ] Calibration band ổn định trên ≥10 mẫu speaking thật
- [ ] Guardrail ngân sách (cap/limit) test được: chạm ngưỡng → hạ tier → dừng
