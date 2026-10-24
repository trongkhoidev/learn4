# Prompt bàn giao AI xây Learn4 Pronunciation Engine

Sao chép nguyên khối dưới đây cho AI có quyền đọc và sửa repository. Tài liệu kế hoạch được tham
chiếu là nguồn chi tiết; prompt này quy định thứ tự thực thi và completion criteria.

```text
Bạn là senior speech/ML engineer và software architect chịu trách nhiệm triển khai Learn4
Pronunciation Engine từ audit đến code, tests và verification report.

Workspace: /Users/admin/repos/learn4

Đây là yêu cầu thực thi. Hãy đọc code mới nhất, sửa code, chạy kiểm chứng và hoàn thành mọi phần
không phụ thuộc dữ liệu/credential bên ngoài. Không dừng ở việc đề xuất hoặc viết thêm một kế hoạch.

ĐỌC TRƯỚC KHI SỬA

1. Đọc AGENTS.md áp dụng trong workspace. Nếu root có `.codegraph/`, dùng CodeGraph trước khi
   grep hoặc đọc file để hiểu symbol/call path.
2. Đọc đầy đủ:
   - docs/plans/pronunciation-engine-implementation-plan.md
   - docs/architecture/architecture-drivers.md
   - docs/architecture/current-system.md
   - docs/research/ielts-speaking-asr-primary-sources.md
   - docs/research/deepgram-elevenlabs-ielts-speaking-evaluation.md
   - backend/scripts/calibration/README.md
   - backend/scripts/asr_training/README.md
3. Đọc implementation, callers, schemas và tests mới nhất của:
   - backend/app/modules/speaking/assessment/
   - backend/app/modules/speaking/pronunciation/
   - backend/app/integrations/audio/, integrations/stt/
   - backend/app/modules/speaking/jobs.py
   - frontend/src/features/speaking/
4. Ghi branch, HEAD và `git status --short`. Bảo toàn thay đổi có sẵn của người khác. Không dùng
   reset/restore/clean/force push và không sửa file ngoài phạm vi khi không cần thiết.

MỤC TIÊU

- Loại bỏ mọi Pronunciation band được suy từ ASR confidence, transcript, alignment-only hoặc
  giá trị mặc định.
- Tạo một pronunciation module sâu: interface nhỏ, implementation che giấu audio normalization,
  lexicon/G2P, alignment, phone posterior/GOP, prosody, feature vector, artifact và policy.
- Trả evidence có timestamp/provenance; phân biệt candidate, validated automated evidence và
  human review.
- Giữ Pronunciation `band=null` và Overall `null` đến khi có artifact examiner-calibrated hợp lệ.
- Hoàn thành contract, deterministic core, adapters, offline dataset/training/evaluation tooling,
  UI evidence, shadow wiring, tests và report. Không bịa data hoặc metric để bật scoring.

BẤT BIẾN

1. ASR confidence/disagreement chỉ xác định vùng cần nghe lại. Nó không phải pronunciation score.
2. Forced alignment chỉ tạo vị trí word/phone. Alignment không tự chứng minh phát âm đúng/sai.
3. Whisper training phục vụ transcript nguyên văn; examiner bands không bao giờ là Whisper target.
4. Accent không phải lỗi. Chỉ tạo claim khi phonological evidence liên quan intelligibility hoặc
   rubric, có audio span và vượt policy đã validation.
5. `status=scored` iff band hợp lệ và artifact/model/calibration đủ điều kiện. Mọi trường hợp khác
   trả nullable result với reason rõ.
6. Overall IELTS diagnostic chỉ do backend trả khi đủ bốn criterion `scored`. Frontend không tự
   tính Overall từ ba criterion.
7. Practice và single-turn feedback có thể coaching theo evidence; IELTS Pronunciation band cần
   sample/session đủ coverage theo artifact policy.
8. Production thiếu model/artifact/provider phải fail closed hoặc abstain. Không mock, fallback
   heuristic, default 6.0/6.5 hoặc generic feedback được trình bày như evidence thật.
9. Giữ backward compatibility additive cho `speaking-v3`, routes, form fields và persisted results.
   Legacy adapter làm mất hiệu lực band có source không đáng tin, không mutate dữ liệu lịch sử.
10. Secret, raw learner audio và PII không vào Git, test fixture, log hoặc report.

THỨ TỰ THỰC THI

P0 — Baseline và false-score hotfix

- Chạy baseline backend tests, frontend lint/build và relevant Playwright nếu môi trường cho phép.
- Viết regression test real-provider path: nhiều mức ASR confidence nhưng không có calibrated
  pronunciation artifact phải luôn cho Pronunciation `band=null`, status non-scored, Overall null.
- Sửa `grade_speaking`, `grade_mock_session`, `pronun_conf_to_band` callers, quality result,
  legacy adapter và frontend ScoreGrid theo P0 trong kế hoạch.
- Mock session không được lấy mean fake hoặc default 6.5. Mọi band cũ từ
  `llm_only_pending_alignment`, `asr_confidence` hoặc source không được validation phải nullable.
- Chạy relevant tests rồi full backend/frontend checks.

P0 hoàn tất khi test đỏ trước fix, xanh sau fix, UI không còn nhãn Overall IELTS cho trung bình ba
tiêu chí, và production/provider mock đều giữ invariant nullable.

P1 — Contract và engine seam

- Tạo typed request/result/evidence/provenance models với validators: half-band, status-band,
  timestamp bounds, word/phone references, confidence semantics và version requirements.
- Tạo `PronunciationEngine` interface và disabled/shadow/enabled policy. Default là disabled.
- `service.py` chỉ còn compatibility facade; assessment engine gọi một interface.
- Dependency injection cho aligner, phone model, feature extractor và artifact loader. Tests dùng
  fakes/frozen arrays, không download model hoặc gọi mạng.
- Config có mode, paths, versions, checksum, timeout và gates; thiếu config dẫn tới abstention.

P2 — PCM, lexicon và alignment

- Tái sử dụng audio processor, luôn tạo private temp PCM mono 16 kHz và cleanup trong `finally`.
- Giữ mapping timestamp về audio gốc.
- Tạo lexicon/G2P adapter có pronunciation variants, optional phones, stress marks và OOV status.
  Proper noun unresolved phải abstain ở phone claim liên quan.
- Hoàn thiện MFA adapter theo CLI/version thực đã pin. Parser trả normalized alignment contract.
- WhisperX chỉ khai báo capability thực; nếu chỉ có word/char alignment thì `phonemes=[]`.
- Test duration bounds, OOV, variants, missing binary/model, timeout và malformed output.

P3 — Phone posterior và GOP deterministic core

- Trước khi chọn model, ghi một decision note ngắn so sánh tối thiểu hai open-weight phone models:
  license, phone inventory, revision pinning, target CPU/RAM và benchmark requirement.
- Implement phone model adapter có explicit artifact manifest; runtime unit tests không tải model.
- Implement phone inventory mapping và deterministic GOP/log-likelihood-ratio từ frozen posterior
  arrays. Xử lý variants, optional phones, substitution/deletion/insertion và duration sanity.
- Trước calibration chỉ xuất `score_unscaled`, `status=candidate`, không probability/band/error chắc.
- Mọi evidence có ID, word/phone, start/end, kind, model/feature version và explanation phù hợp.

Nếu không có model weights/cache hoặc license chưa được xác nhận, hoàn tất interface, manifest,
deterministic GOP core, fake adapter và tooling; đánh dấu real adapter blocked. Không chọn một model
ngẫu nhiên rồi nhận là production-ready.

P4 — Prosody features

- Implement versioned F0, energy, voiced coverage, duration, pause, rhythm, pitch range/slope,
  terminal movement và lexical-stress contrast khi có target.
- Normalize pitch theo speaker/utterance; thiếu feature là null/missing, không phải điểm 0.
- Silence/noise/clipping/short audio phải hạ evidence quality hoặc abstain, không tạo lỗi.
- Tách interpretation cho Fluency và Pronunciation; word-duration dispersion không được gọi là stress.
- Native/heavy dependency đặt trong pronunciation-specific requirement/image profile; không làm
  remote-only API image tải model pronunciation.

P5 — Dataset, training, evaluation và artifact tooling

- Tạo `backend/scripts/pronunciation/` gồm README, manifest schema, validator, feature extraction,
  train baseline, evaluate, artifact export/inspect. Không thêm raw corpus.
- Schema bắt consent/license, speaker/session split, audio checksum, labels, examiner IDs,
  prediction-hidden flag, adjudication, metadata slice và retention.
- Bắt leakage speaker/session, duplicate/near-duplicate metadata, expired consent, missing ratings,
  examiner nhìn prediction và incompatible feature/model versions.
- Public corpus adapters chỉ chuẩn bị manifest cho SpeechOcean762/L2-ARCTIC sau khi user tự đặt data
  ở local path. Ghi rõ public corpus không trực tiếp cung cấp IELTS band.
- Baseline band model phải đơn giản/giải thích được. Frozen test không dùng fit threshold/calibrator.
- Evaluate phone precision/recall/F1, claim precision, unsupported rate, band MAE/QWK/bias/
  within-half/coverage, slice metrics và speaker-bootstrap CI.
- Artifact fail closed với schema/version/checksum/compatibility mismatch.

Không có examiner dataset thật thì tests dùng synthetic metadata/frozen numeric features để kiểm
pipeline, không dùng chúng làm accuracy evidence. Giữ mode disabled/shadow và ghi P6 data-blocked.

P6 — Tích hợp result/UI

- Mở rộng additive `CriterionAssessment` theo output contract trong kế hoạch.
- `PronunErrorList` hiển thị candidate khác validated evidence, có audio replay bounded segment,
  text + icon ngoài màu và không biến `heard → intended` ASR suggestion thành phone error.
- ScoreGrid có các state: language-only, pronunciation pending, fully scored. Overall chỉ dùng
  server value. AssessmentQualityCard phản ánh scope thật.
- Teacher/human confirmation nếu chưa có backend workflow thì tạo typed event/use-case nhỏ và
  persistence chỉ khi phù hợp schema/migration conventions; nếu ngoài scope, hoàn tất UI contract
  và ghi gap, không dựng fake RBAC.
- Add frontend unit/Playwright coverage cho unavailable, candidate, scored fixture, replay,
  mobile/keyboard và error state.

P7 — Shadow/runtime wiring

- Dùng feature flag `disabled|shadow|enabled`; production default disabled đến release gate.
- Shadow result được persist/telemetry theo privacy policy nhưng không thay result người học.
- Model inference thuộc worker/container profile hỗ trợ native deps; API remote-only không preload.
- Job retry idempotent, audio lấy từ private object storage, temp cleanup, timeout/concurrency cap.
- Add health/readiness chỉ báo capability thật; missing artifact không làm toàn API giả ready.
- Viết benchmark command cho cold/warm latency, RTF, peak RAM/CPU và failure rate.

P8 — Verification report

- Tạo `docs/verification/pronunciation-engine-report.md` gồm:
  - before/after behavior;
  - file/module map và interface;
  - tests/commands với output thực;
  - artifact/model/license status;
  - metrics nào là synthetic, public corpus hoặc examiner test;
  - release gates pass/fail/not-run;
  - data/infrastructure blockers;
  - risks, rollback và exact feature-flag state.
- Cập nhật README/docs links cần thiết.
- Không ghi “hoàn thiện”, “examiner-grade” hoặc “chính xác” khi P6 release gate chưa chạy trên
  examiner-rated frozen test set.

TEST VÀ KIỂM CHỨNG

Chạy ít nhất:

  cd /Users/admin/repos/learn4/backend
  ./.venv/bin/python -m pytest -q
  ./.venv/bin/ruff check app tests scripts

  cd /Users/admin/repos/learn4/frontend
  npm ci
  npm run lint
  npm run build
  npx playwright test

Thêm focused commands cho pronunciation dataset/artifact/model integration vào report. Tests mặc
định offline và deterministic. Model integration tests tách marker, dùng explicit local cache và
skip với lý do khi artifact không có; không download âm thầm trong CI.

Không xóa/skip/weaken test để xanh. Nếu baseline có lỗi, ghi lại, xác định lỗi có sẵn hay do patch,
sửa mọi regression do thay đổi này. Dùng generated/licensed fixtures; không dùng audio learner thật.

PHẠM VI QUYẾT ĐỊNH

- Giữ modular monolith. Tạo seam cho model/alignment/artifact vì đã có nhiều adapter hoặc mode thật;
  không tạo microservice/event bus/repository abstraction chung.
- Có thể thêm dependency open-source sau khi kiểm tra license, native build và target deployment;
  pin riêng trong pronunciation profile. Không thêm Azure Speech Pronunciation Assessment.
- Có thể sửa contract additive, migrations an toàn, UI và tests cần thiết. Không deploy production,
  rotate secret, chạy training tốn phí, tải corpus lớn hoặc bật enabled mode khi thiếu dữ liệu.
- Không hỏi lựa chọn kỹ thuật thường lệ. Chọn mặc định an toàn theo kế hoạch, tiếp tục toàn bộ phần
  độc lập. Chỉ ghi blocked cho phần thật sự cần audio/examiner/artifact/credential bên ngoài.

DEFINITION OF DONE

1. False Pronunciation scoring và client-side fake overall bị loại bỏ, có regression tests.
2. Pronunciation engine contract/seam, deterministic evidence core, versioned features, artifact
   loader/policy và offline tooling được implement/test, không chỉ scaffold rỗng.
3. UI trình bày đúng nullable/candidate/scored states và evidence replay.
4. Shadow/runtime wiring fail closed, idempotent và không phụ thuộc local persistent disk.
5. Full available checks pass; verification report trung thực.
6. Nếu chưa có examiner dataset, production vẫn `band=null`/Overall null và report ghi P6 blocked.
   Đây là kết quả đúng, không phải lý do để thay bằng heuristic.
```

