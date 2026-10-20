# Kế hoạch hoàn thiện IELTS Speaking + Whisper

Ngày rà soát: 2026-09-28

## 1. Kết luận kỹ thuật

Sản phẩm đã có luồng luyện Speaking chạy được, nhưng chưa được phép gọi là
"chấm IELTS chính xác" cho tới khi hoàn thành calibration với dữ liệu thật và
giám khảo. Whisper là mô hình nhận dạng lời nói; confidence/timestamp của
Whisper không phải điểm phát âm. Trải nghiệm có thể học từ luyennoi.com, còn
scoring phải bám bốn descriptor công khai của IELTS và công khai độ tin cậy.

Nguồn chuẩn:

- IELTS Speaking có ba phần, kéo dài 11–14 phút; Part 2 có một phút chuẩn bị và
  nói tối đa hai phút:
  https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-speaking
- Bốn tiêu chí: Fluency and Coherence, Lexical Resource, Grammatical Range and
  Accuracy, Pronunciation:
  https://ielts.org/cdn/Guides/ielts-speaking-key-assessment-criteria.pdf
- Public band descriptors:
  https://takeielts.britishcouncil.org/sites/default/files/ielts_speaking_band_descriptors.pdf
- Faster Whisper hỗ trợ fixed language, word timestamps, VAD và
  condition_on_previous_text=False:
  https://github.com/SYSTRAN/faster-whisper/blob/master/README.md
- Forced alignment cần transcript, từ điển phát âm và acoustic model:
  https://montreal-forced-aligner.readthedocs.io/en/v3.3.4/user_guide/workflows/alignment.html

## 2. Trạng thái sau đợt rà soát

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| Topic → Part → câu hỏi thật | Đã nối | UI gửi đúng question_id và nội dung backend dùng để chấm |
| Ghi âm → nghe lại → nộp | Đã có | Có giới hạn thời lượng, trạng thái đang chấm |
| Kiểm tra upload | Đã có nền | MIME, file rỗng, dung lượng, decode và duration |
| Whisper profile tiếng Anh | Đã có | mono 16 kHz, language=en, VAD, word timestamps |
| ASR uncertainty | Đã có | missing metrics, uncertain spans, hallucination risk, second pass |
| Không bịa band khi thiếu mẫu | Đã có | cant_hear, insufficient_sample, off_topic, failed |
| Typed result contract | Đã có | Status, confidence basis, metadata, bốn tiêu chí |
| Feedback theo descriptor | Đã có nền | Holistic; bỏ luật trừ điểm/đếm từ không chính thức |
| Pronunciation audio evidence | Một phần | Prosody + energy + intelligibility + adapter; chưa chọn/bật phone alignment/GOP |
| Mock test đúng quy trình IELTS | Đã có nền | Turn tuần tự ba Part, Part 2 chuẩn bị 60 giây/nói tối đa 120 giây, tổng hợp cuối bài |
| Calibration với examiner | Chưa có | Blocker để tuyên bố độ chính xác band |
| Queue production | Đã có cho một worker | DB-backed durable job, retry, restart recovery, polling; multi-host cần queue/claim lock riêng |
| Retention/readiness | Đã có | Xóa audio theo hạn, dọn job orphan, preload và `/ready` |
| Quan sát vận hành | Một phần | Có metadata/version/readiness; thiếu WER, reject rate và drift dashboard |

## 3. Pipeline đích

    Browser MediaRecorder
      -> validate MIME/bytes/duration
      -> FFmpeg PCM mono 16 kHz
      -> object storage + durable job queue
      -> Faster Whisper large-v3-turbo
           -> transcript/segments/words
           -> ASR confidence + missing metrics
           -> uncertain spans + hallucination checks
           -> conditional second decode and agreement
      -> evidence gate
           -> cant_hear / insufficient_sample / needs_review / scoreable
      -> pronunciation aligner (WhisperX hoặc MFA prototype)
           -> word/phone alignment, OOV, alignment confidence
           -> GOP/segmental + stress/rhythm/intonation features
      -> descriptor raters (FC/LR/GRA/Pronunciation)
      -> deterministic validation + half-band rounding
      -> result + confidence + model/rubric/calibration version

## 4. Kế hoạch build Whisper

### P0 — STT đáng tin cậy

1. Khóa input thành PCM mono 16 kHz; giữ file gốc chỉ để nghe lại.
2. Profile chính: language=en, task=transcribe, beam_size=5, temperature=0,
   VAD 300 ms, word timestamps, condition_on_previous_text=False.
3. Chạy pass hai khi confidence thấp, compression bất thường, nhiều word
   uncertainty hoặc repetition run. So sánh hypothesis; không tự chọn câu
   "đẹp hơn" nếu chưa có rule được kiểm chứng.
4. Lưu model ID/checksum, decode profile version, provider, latency,
   real-time factor và missing metrics cùng submission.
5. Nếu provider fallback không trả logprob/word probability, phải hạ confidence;
   không điền mặc định 1.0.

### P1 — pronunciation có bằng chứng âm thanh

1. Prototype WhisperX/wav2vec2 và Montreal Forced Aligner trên cùng golden set.
2. Chọn theo phone-boundary error, failure rate, latency và độ ổn định với giọng
   Anh của người Việt; không chọn chỉ vì dễ tích hợp.
3. Tạo evidence:
   - segmental: phone posterior/GOP, substitution/deletion, vowel/consonant;
   - suprasegmental: lexical stress, sentence stress, chunking, rhythm, pitch,
     pausing;
   - intelligibility: ASR agreement và human-listener transcript agreement.
4. Chỉ hiện "lỗi từ" khi alignment confidence đạt ngưỡng đã calibrate. Nếu ASR
   nghi ngờ, nhãn là asr_uncertain, không phải lỗi phát âm.
5. Không chấm accent gần native; descriptor quan tâm intelligibility, phonological
   range và effort của người nghe.

### P2 — throughput và triển khai

1. Tách worker STT khỏi FastAPI; dùng Redis + RQ/Celery/Arq hoặc queue bền vững.
2. Một model process/worker; giới hạn concurrency theo benchmark RAM và RTF.
   VPS 4 vCPU phải benchmark trước khi hứa latency.
3. Trả 202 pending, frontend poll/SSE; job idempotent và retry có giới hạn.
4. Circuit breaker cho fallback; không so confidence của hai provider như cùng
   một thang đo nếu chưa calibration.
5. Cleanup file tạm trong finally; audio retention và xóa R2 theo policy.

## 5. Calibration để feedback và band có thể tin được

### Bộ dữ liệu

- Tối thiểu 300 người nói, đủ ba part; ưu tiên người Việt ở band 4–8.
- Hai examiner độc lập chấm bốn tiêu chí; bất đồng lớn có examiner thứ ba.
- Chia train/validation/test theo speaker, không theo clip.
- Slice: band, giọng, thiết bị, độ ồn, tốc độ nói, vùng miền, provider và câu hỏi.
- Negative fixtures: im lặng, nhạc/beep, tiếng Việt, đọc thuộc, audio cắt cụt,
  clipping, mic xa, repetition hallucination.

### Release gate nội bộ

| Lớp | Chỉ số đề xuất |
|---|---|
| ASR | WER tổng ≤ 12%, slice giọng Việt ≤ 15%, content-word deletion ≤ 5% |
| Silence/hallucination | false transcript trên silence/noise < 1%; recall reject ≥ 95% |
| Criterion band | MAE với examiner ≤ 0.5; quadratic weighted kappa ≥ 0.70 |
| Overall band | ≥ 80% trong ±0.5; không slice nào lệch trung bình > 0.5 |
| Feedback | ≥ 90% claim lỗi có bằng chứng; 0 fabricated quote trong golden set |
| Reliability | p95 theo SLA đã chọn; job loss = 0 trong retry test |

Đây là gate nội bộ, không phải thông số chính thức của IELTS. Nếu chưa đạt, UI
chỉ được gọi là “diagnostic practice estimate”.

Quy trình: freeze golden set → tune trên train → chọn threshold trên validation →
test đúng một lần → fit calibration riêng từng criterion → examiner sign-off →
canary 5% và theo dõi drift.

## 6. Full flow kiểu luyennoi.com nhưng đúng IELTS hơn

### Practice

1. Chọn topic/Part và hiện đúng một câu; TTS chỉ đọc câu hỏi.
2. Part 2 có cue card, một phút chuẩn bị, tự dừng ở hai phút.
3. Ghi âm, nghe lại, ghi lại hoặc nộp.
4. Hiện upload → transcription → assessment → completed.
5. Kết quả: score grid, transcript, vùng ASR không chắc, grammar grounded,
   feedback bốn tiêu chí và một action cụ thể.
6. Cho luyện lại cùng câu và so sánh cùng model/rubric version.

### Mock test

1. Part 1 hỏi tuần tự nhiều câu, không gom nhiều câu vào một recording.
2. Part 2: cue card → chuẩn bị 60 giây → nói 1–2 phút → follow-up.
3. Part 3 nối topic Part 2, câu hỏi tăng dần độ trừu tượng.
4. Chỉ tổng hợp sau toàn test; không gọi trung bình ba response đơn giản là điểm
   IELTS chính thức.
5. Lưu mock session cha và nhiều turn con để replay/audit.

## 7. Backlog theo thứ tự

### Sprint A — contract và reliability (đã hoàn thành phần lớn)

- Typed result/evidence status.
- Fixed Whisper profile, VAD, second pass, uncertain spans.
- File validation, cleanup, deadline/storage bug fixes.
- Descriptor prompts, confidence basis.
- Backend tests, frontend build, navigation E2E.

### Sprint B — mock session đúng chuẩn (đã hoàn thành phần lõi)

- [x] Thêm speaking sessions/turns, trạng thái và model versions.
- [x] State machine ba part, timer chuẩn và lưu từng turn.
- [x] Durable queue, retry/recovery và polling.
- [ ] Idempotency key/resume UI và browser E2E có fake microphone cho submit → result → history.

### Sprint C — pronunciation engine

- PoC WhisperX/MFA.
- Phone/stress feature schema và evidence UI.
- Golden set + công cụ examiner double-rating.
- Calibration, bias report, threshold, human-review lane.

### Sprint D — production hardening

- Load/soak/failure tests, autoscaling, retry/dead-letter.
- Metrics, alert, cost/latency budgets.
- [x] Retention audio, orphan cleanup và readiness.
- [ ] Consent, xóa theo yêu cầu, access control và audit log.
- Canary, versioned rollback, periodic drift review.

## 8. Definition of Done

Feature chỉ hoàn tất khi:

- Practice và Mock state machine chạy qua browser E2E;
- audio thật chạy self-host Whisper trên môi trường gần production;
- mọi feedback claim truy ngược được về transcript/audio evidence;
- không có band khi audio/mẫu không đủ;
- golden-set gates đạt và có examiner sign-off;
- model/rubric/calibration version được lưu với từng kết quả;
- retry không mất bài, retention/delete được kiểm chứng;
- UI ghi rõ đây là chẩn đoán luyện tập, không phải IELTS chính thức.

## 9. Benchmark cục bộ 2026-09-28

Môi trường: Apple M1 Pro, 16 GB RAM, faster-whisper 1.2.1, model Turbo,
CPU int8, audio tiếng Anh 5.42 giây.

| Lượt | Latency | Real-time factor | ASR confidence |
|---|---:|---:|---:|
| Cold/model load | 8.97 giây | 1.66 | 0.958 |
| Warm 1 | 4.03 giây | 0.74 | 0.960 |
| Warm 2 | 4.30 giây | 0.79 | 0.960 |

Silence 2 giây và white noise 2 giây đều trả transcript rỗng, confidence 0.20,
hallucination risk 0.80. Kết quả này xác nhận regression path hoạt động trên máy
dev; không thay thế benchmark VPS với audio IELTS dài và nhiều concurrency.
