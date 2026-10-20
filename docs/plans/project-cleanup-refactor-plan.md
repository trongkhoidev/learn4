# Kế hoạch cleanup và refactor LexiLearn

Ngày rà soát: 2026-10-18. Trạng thái: kế hoạch bàn giao, chưa thực hiện refactor.

## 1. Thứ tự thực hiện

1. AI triển khai đọc kế hoạch này và [prompt bàn giao](../prompts/refactor-handoff.md),
   refactor ứng dụng hiện tại, giữ hành vi, kiểm chứng và xuất báo cáo bàn giao.
2. Đối chiếu code sau refactor với [danh mục page/role](../design/role-page-inventory.md).
3. Dùng Stitch thiết kế theo [brief](../design/stitch-redesign-brief.md): Speaking trước,
   sau đó Teacher, Student và các trang Admin dự kiến.
4. Triển khai UI từ thiết kế đã review trong một đợt riêng, kiểm tra tương tác và dữ liệu thật.

Không trộn đổi kiến trúc, đổi scoring và đổi giao diện trong cùng bước. Kế hoạch không yêu cầu
người dùng chọn phương án giữa chừng; AI xử lý lựa chọn thường lệ theo các mặc định bên dưới.

## 2. Phạm vi và nguồn sự thật

- Ứng dụng chính: `backend/` FastAPI/SQLAlchemy và `frontend/` React/Vite/JavaScript.
- Giữ hai thư mục cấp cao này để các đường dẫn Docker/CLI ít biến động. Kiến trúc đích là
  **modular monolith**, tổ chức theo tính năng trong từng ứng dụng.
- Giữ PostgreSQL production, SQLite tests, storage, các biến môi trường và durable Speaking jobs.
- Giữ npm và `package-lock.json`; chưa chuyển Next.js, pnpm, TypeScript, microservices hoặc Redis.
- Giữ toàn bộ route, HTTP method, form field, response contract và dữ liệu lịch sử đang dùng.
  Mọi đề xuất thay đổi hành vi đưa sang backlog, không lẫn vào refactor.
- `DESIGN.md` là nguồn định hướng sản phẩm/design: Admin, Teacher, Student; không attendance.
  Code hiện chưa có Admin/RBAC đầy đủ. Refactor chỉ tạo điều kiện tổ chức page theo role,
  không tự thêm auth, tài khoản, billing, phân quyền Admin hoặc các endpoint mới.
- Nội dung chấm Speaking lấy **code và tests hiện tại** làm baseline. Kế hoạch Speaking cũ là
  bối cảnh, không phải lệnh quay lại phiên bản cũ.

Git root hiện là `/Users/admin/repos`, không phải thư mục dự án này. Mọi thao tác Git phải
giới hạn path của LexiLearn; không stage/restore/reset file của dự án anh em.
Working tree có nhiều thay đổi và file chưa tracked từ trước: chúng là dữ liệu đầu vào cần giữ.

## 3. Hiện trạng cần giải quyết

| Quan sát đã kiểm tra | Tác động | Hướng xử lý |
|---|---|---|
| `learn4/` bên trong là gitlink và có `.git` riêng; `luyennoi-clone/` chứa ứng dụng Next.js tham chiếu | Dễ refactor nhầm sản phẩm, làm mất lịch sử | Giữ nguyên, đánh dấu reference-only; loại khỏi các tool của ứng dụng chính |
| `Layout.jsx` khoảng 236 dòng, nhánh role theo pathname và markup Teacher cũ phía sau early return | Navigation/role dễ chồng chéo | Tách shell Teacher/Student/Speaking, nested routes rõ |
| `SpeakingPractice.jsx` khoảng 459 dòng; mock có polling/timer/state riêng | Khó thay UI, lỗi lifecycle | Tách controller hooks, state reducer, audio và presentation |
| `api/client.js` gom mọi domain | Mọi tính năng phụ thuộc một module lớn | Transport HTTP chung, client từng feature |
| Backend phân tầng ngang routers/models/schemas/services; route còn xử lý audio/DB/background | Quy trình nghiệp vụ rải nhiều nơi | Gom feature và đưa use case vào implementation module |
| `assessment_service.py` khoảng 500 dòng; `llm_service.py` trộn provider transport và Speaking rubric | Đổi model/prompt dễ ảnh hưởng nhau | Tách assessment, contract, rater và provider adapters theo seam thực |
| `queue.py` chứa Speaking durable worker và background helper cho Writing | Khó thấy owner/lifecycle | Speaking jobs ở module Speaking; helper nền nhỏ dùng chung nếu vẫn cần |
| Có hai bộ Topic/Question models: generic và Speaking riêng | Dễ xóa nhầm bảng đang có dữ liệu | Kiểm tra caller/DB, bảo toàn table names; không tự merge schema |
| Khởi động có `create_all` và `ALTER TABLE` inline | Import/lifecycle/migration gắn nhau | Tách bootstrap để đọc rõ; giữ nguyên hiệu ứng hiện tại, ghi backlog migration riêng |
| Debug scripts/audio/log, `.pytest_cache`, E2E artifacts cùng source | Dễ lẫn test dữ liệu thật, build rác | Inventory + di chuyển đúng nhóm hoặc ignore; không xóa không kiểm tra |
| Python requirements dùng khoảng version; Docker frontend có `npm ci || npm install` | Build khó tái lập | Ghi runtime/lock policy; bỏ fallback install chỉ sau khi `npm ci` đã được kiểm chứng |

Baseline **đã chạy lần này**: backend `pytest -q`: **93 passed** (một cảnh báo Starlette/httpx);
frontend `npm run build`: **pass**. Số test đã tăng so với audit Speaking trước; không dùng lại mốc 82.
Đã thấy 5 test Playwright trong source (navigation, fake mic/partial, failed/history);
lần lập kế hoạch này chưa chạy lại E2E. Không coi các file `test-results` cũ là kết quả hiện tại.

## 4. Cấu trúc đích

Đây là danh mục module có owner, không phải yêu cầu tạo file rỗng cho đủ cây.
Chỉ tách file khi nó gom một trách nhiệm thực hoặc có seam để kiểm thử.

```text
learn4/                         # project root hiện tại
  README.md
  DESIGN.md                     # giữ làm nguồn design hiện tại
  .env.example
  docker-compose.yml
  start.sh                      # entrypoint tương thích
  backend/
    app/
      main.py                   # create app, mount routers, lifecycle wiring
      core/                     # config, access, errors, bootstrap
      db/                       # Base, engine/session, model registration
      integrations/
        audio/                  # FFmpeg validation/normalization
        storage/                # R2/local adapters
        stt/                    # selfhost/Groq/mock adapters + recognition contract
        llm/                    # provider transport/readiness, không rubric IELTS
      modules/
        classes/                # router, schemas, models, use cases
        assignments/            # router, schemas, models, use cases
        submissions/            # submit/review/roster, objective grading
        speaking/
          router.py
          schemas.py            # HTTP DTO và legacy response adapter
          models.py
          practice.py           # Practice use cases
          mock.py               # Mock session/turn use cases
          jobs.py               # durable Speaking jobs, retry/target persistence
          assessment/           # engine, contracts, raters/prompts, rubric, evidence
          pronunciation/        # acoustic/prosody + alignment adapters
        writing/                # Writing assessment + OCR coordination
      operations/               # budget, retention, seed/bootstrap helpers
    tests/                      # mirror feature ownership; fixtures dùng chung
    scripts/
      calibration/
      asr_training/
      diagnostics/              # script chủ động chạy, không pytest discovery
    requirements.txt
    Dockerfile
  frontend/
    src/
      app/                      # entry, routes, providers
      layouts/                  # TeacherLayout, StudentLayout, SpeakingLayout
      features/
        access/                 # teacher code, learner name/context hiện có
        classes/                # pages/components/hooks/api
        assignments/            # builder và student assignment runner
        submissions/            # review, results, scoreboards
        speaking/
          pages/                # Dashboard, Practice, Mock, History
          components/           # recorder, cue card, transcript, criterion feedback
          hooks/                # practice/mock controllers, job polling
          model/                # reducer/state, result presentation adapter
          api/                  # Speaking endpoint client
        writing/                # editor/result hiện có
      shared/
        api/                    # HTTP transport/errors/abort
        ui/                     # Button/Input/Dialog/... không nghiệp vụ
        hooks/                  # chỉ hook thực sự dùng nhiều feature
        lib/                    # format helpers có tên cụ thể
      styles/                   # global styles, design tokens
    tests/                      # browser/user flows
    public/
    package.json
    package-lock.json
  docs/
    architecture/               # current map, dependency rules, route/API inventory
    plans/
    prompts/
    design/
    research/
    verification/               # baseline/final report + file mapping
    archive/                    # tài liệu cũ, có note superseded
  deploy/                       # giữ deployment scripts hiện có
  learn4/                       # reference-only gitlink, giữ nguyên
  luyennoi-clone/               # reference-only, giữ nguyên
```

Không cần `domain/application/infrastructure` lồng thêm trong mọi feature.
Không tạo generic repository, event bus, workflow engine hoặc base CRUD chỉ để đổi tên thư mục.
Module sâu có interface nhỏ, implementation gom được quy trình; ưu tiên locality khi bảo trì.

## 5. Quy tắc dependencies và ownership

Backend: HTTP router → use case module → models/integrations. FastAPI-specific lỗi/UploadFile
được xử lý ở HTTP interface; quy tắc parse/validation chung chỉ tách khi thực sự trùng.
Một transaction có owner rõ; worker mở session riêng, không giữ request session sau request.
`Base` chỉ định nghĩa một lần; đăng ký toàn bộ ORM model trước bootstrap. Giữ string relationships,
FK, cascade và table names để tránh duplicate metadata khi đổi import.

`submissions` gọi Speaking/Writing qua interface công khai, không để Speaking import ngược
router submissions. Speaking jobs có thể cập nhật các target hiện có bằng adapter/wiring rõ,
không thêm dispatcher tổng quát nếu chỉ một quy trình cần. LLM transport không import rubric.
Seam cho STT và storage có adapters thật đang tồn tại; inject vào assessment để test không gọi mạng.

Frontend: `app` ráp routes/layout; page gọi controller hook và ghép UI; controller gọi feature API.
`shared` không import `features`; feature không import page/private state của feature khác.
Role shell nhận context qua interface nhỏ, không copy toàn bộ `Layout.jsx` ba lần.
Không dùng pathname substring như cơ chế security. Teacher code/name trong localStorage là mô hình
truy cập hiện có, không được mô tả là RBAC an toàn hay thêm nút role switch giả quyền truy cập.

State UI tách khỏi data/server status. Recorder sở hữu mic stream; polling sở hữu AbortController,
deadline/retry và cleanup; reducer sở hữu transition của Practice/Mock. Timer dùng thời điểm đích
để tránh drift; không đổi thời lượng hiện có. TTS dừng khi bắt đầu thu, không lọt vào bản ghi.
Giữ blob khi rerender; revoke object URL và stop tracks khi kết thúc; không upload audio hai lần.

Assessment contract `speaking-v3`, partial/null, uncertainty, word IDs, legacy adapter và metadata
phải giữ nguyên theo code baseline. Không sửa scoring hoặc quay lại confidence→pronunciation.
Transcript nguyên bản và dữ liệu human correction (nếu có) tách nguồn; không rewrite evidence.

## 6. Bản đồ di chuyển bắt buộc

| Nguồn | Đích/owner |
|---|---|
| `app/config.py`, `deps.py` | `core/config.py`, `core/access.py` |
| `app/db.py` | `db/base.py`, `db/session.py`, exports tương thích trong giai đoạn chuyển |
| `routers/classes.py`, `schemas/class_.py`, `models/class_.py` | `modules/classes/` |
| `routers/assignments.py`, schemas/model assignment | `modules/assignments/` |
| `routers/submissions.py`, schemas/model submission, `grading_service.py` | `modules/submissions/`, objective grading cùng owner |
| `routers/speaking.py`, schemas/model speaking | `modules/speaking/` |
| `assessment_service.py` | Speaking assessment engine + Writing interface vào module Writing |
| `llm_service.py` | `integrations/llm/` cho transport; `speaking/assessment/` cho payload/rater |
| `rater_contract.py`, `rubric.py`, `scoring_service.py` | `speaking/assessment/`; giữ compatibility functions nếu có caller |
| `acoustic.py`, `pronunciation_service.py`, `alignment_service.py` | `speaking/pronunciation/` |
| `stt_service.py` | `integrations/stt/` |
| `audio_processor.py`, `blob_service.py` | `integrations/audio/`, `integrations/storage/` |
| `queue.py` | Speaking jobs và helper Writing nếu còn caller, không bỏ retry/recovery |
| `budget_guard.py`, `retention_service.py`, `seed.py` | `operations/` + lifecycle wiring |
| `ocr_service.py`, `writing_service.py` | Writing orchestration; OCR transport có thể là integration nếu dùng chung thật |
| `models/topic.py` generic | Giữ table/model đến khi chứng minh không có caller/dữ liệu; tài liệu hóa legacy owner |
| `App.jsx`, `main.jsx` | `app/`; giữ import entry Vite hoặc sửa `index.html` đồng bộ |
| `components/Layout.jsx`, `SpeakingShell.jsx` | `layouts/`, navigation config theo role/context |
| Teacher/Student pages | classes/assignments/submissions/access theo nghiệp vụ, không nhân bản theo role |
| Speaking pages/components, `useSpeech.js` | `features/speaking/`, TTS là hook cùng owner |
| `AudioRecorder.jsx` và `AudioRecorderPro.jsx` | Audit consumers; một core thu âm chỉ khi hành vi tương thích, giữ UI adapters |
| `FeedbackPanel`, `ReasoningCards`, `ScoreBoard`, Writing UI | Feature owner tương ứng; xóa chỉ khi không caller và không behavior khác |
| `components/ui/*` | `shared/ui/` |
| `api/client.js`, `lib/constants.js`, `index.css` | HTTP chung + client feature; constants theo owner; styles/tokens |

AI phải xuất mapping từng file thực tế; bảng này không thay thế inventory caller/import.

## 7. Chính sách cleanup

- Trước di chuyển: liệt kê tracked/untracked/ignored, imports, scripts, runtime paths và checksums
  của các file nhạy với di chuyển. Không đưa nội dung `.env`/keys vào báo cáo.
- Hai cây tham chiếu giữ tại chỗ; ghi README rõ ứng dụng chính và exclude khỏi lint/test/build.
  Không xóa, merge hay chuyển gitlink trong đợt refactor này.
- Debug `.py`: xem nội dung trước. Nếu còn hữu ích và không chứa credential/PII, chuyển
  `backend/scripts/diagnostics/`, đổi tên khỏi `test_*`, sửa paths. Test thực chuyển `backend/tests/`.
- `test.m4a`, `test.webm`, `curl_out.txt`: không mở/phát tán dữ liệu cá nhân chỉ để cleanup.
  Phân loại nguồn và quyền; mặc định giữ nguyên nội dung, đặt ngoài discovery/build, ghi manifest.
  Không đưa raw learner audio hoặc curl có token vào Git. Sample thiếu provenance không thành fixture.
- Cache/build/test results: đưa vào ignore và Docker ignore. Nếu đã tracked, ghi rõ và chỉ untrack
  các artifact đã xác nhận được tái tạo, giữ file local; giới hạn path, không `git rm` diện rộng.
- Root docs cũ chuyển vào `docs/` theo chủ đề khi đã lập map; giữ file entry ngắn có relative link
  tại đường dẫn cũ để không làm hỏng prompt/bookmark. Ghi current/superseded, không sửa lịch sử audit.
- Giữ root `README.md`, `DESIGN.md` và entrypoints. Không tự di chuyển DB/storage/model cache,
  reset DB, drop tables, chạy retention trên dữ liệu thật hoặc cài lại `.venv` để “clean”.

## 8. Các phase và tiêu chí nghiệm thu

| Phase | Thực hiện | Bằng chứng trước chuyển phase |
|---|---|---|
| R0 baseline | Đọc code mới nhất, inventory route/API/models/storage, chụp git diff paths, tests/build/E2E | Báo baseline, failures có sẵn, snapshot contracts không chứa secrets |
| R1 vệ sinh | Excludes, diagnostics/docs ownership, manifest reference-only | Không mất source/audio/DB, không đổi app behavior |
| R2 backend | Di chuyển theo feature nhỏ, tách provider/rater, wiring/imports/jobs | pytest relevant mỗi nhóm, full suite sau phase; OpenAPI tương thích |
| R3 frontend | Routes/shell/API feature, controller/recorder/polling tách UI | build + E2E; deep link/back/refresh và localStorage keys hoạt động |
| R4 tools | Lint scope riêng app, runtime/dependency guidance, Docker/dev path checks | Lint pass trong scope đã chốt, reproducible npm install/build, Compose config hợp lệ |
| R5 bàn giao | Xóa shim tạm khi không caller; final map, regression report, design gaps | Đủ checklist dưới đây, prompt cho giai đoạn Stitch dùng được |

Mỗi nhóm thay đổi phải nhỏ và review được. Có thể dùng commits giới hạn path khi session cho phép;
không coi commit là điều kiện để tiếp tục và không commit thay đổi người khác một cách mù quáng.
Shim chỉ tồn tại để chuyển tiếp; không để hai implementation cũ/mới chạy song song.

### Kiểm chứng bắt buộc cho AI triển khai

- `cd backend && ./.venv/bin/python -m pytest -q`.
- `cd frontend && npm ci && npm run build` trên môi trường phù hợp, không fallback tự sửa lockfile.
- `cd frontend && npx playwright test`: DB/storage tạm, provider mock explicit, không dựa vào server thật
  đang chạy; export env trước khi khởi động webServer. Không nhầm mock pass với độ chính xác AI.
- Thêm `lint` frontend (ESLint React/hooks) và `ruff check` backend nếu chưa có; cấu hình chủ đích,
  giới hạn vào app/tests/scripts được duy trì. Tách sửa lint hiện có khỏi di chuyển file; không blanket-ignore
  lỗi thật chỉ để xanh. Không ép format/rewrite cả repo hoặc bật TypeScript/mypy toàn bộ trong đợt này.
- Typecheck: giữ/check công cụ có sẵn nếu phát hiện; nếu chưa có, ghi N/A cùng lý do. Không tuyên bố
  `vite build` là typecheck. TypeScript migration là backlog riêng.
- So sánh OpenAPI canonical bỏ metadata không ổn định; check methods/paths/required fields/types/status,
  request/response fixtures và private answer key không lộ cho student.
- ORM import metadata một lần; tests DB mới và copy DB cũ được khử nhạy cảm; table/FK unchanged.
- Worker retry/restart/polling; Practice, Mock, assignment Speaking cùng engine; Writing/objective không regress.
- Recorder denial/no mic, re-record, unmount/cleanup, Part 2 timing, failed/partial/history, null band.
- Route/access tests Teacher code đúng/sai, join/name context, legacy URL query/hash, no console errors.
- `docker compose config --quiet` với env test; không in secrets. Build images/start isolated test stack
  nếu Docker có sẵn; health/ready/audio serving kiểm tra thực. Không dùng production volumes.
- Kiểm tra URL audio qua cả Vite/nginx. Hiện proxy chỉ `/api` trong config đã đọc: nếu path `/storage`
  cần sửa, phải có reproduction/test và ghi là compatibility fix riêng, không silently thay contract.

Lỗi có sẵn phải ghi riêng và retry cách hợp lý. Chỉ sửa lỗi liên quan refactor hoặc chặn kiểm chứng;
nêu rõ patch sửa bug. Không xóa test hay đổi assertion nghiệp vụ để hợp kiến trúc mới.

## 9. Bàn giao bắt buộc

AI tạo `docs/verification/refactor-handoff-report.md` với:

1. Cấu trúc cuối, owner và module interfaces dùng cho thiết kế UI.
2. Mapping old → new từng file; file bỏ/giữ/archive và lý do; exclusions reference trees.
3. Route inventory, API compatibility, schema versions và status thực tế.
4. Commands/result trước và sau, failure baseline/phát sinh, Docker/typecheck N/A nếu thiếu môi trường.
5. Screenshots desktop/mobile các luồng hiện có; không coi đây là thiết kế Stitch.
6. Các invariant Speaking đã giữ, tests và limitations còn lại.
7. Khoảng trống API so với các page trong inventory, chia supported/in-app-state/design-only.
8. Không còn code chết/shim/import path cũ ngoài docs lịch sử; liệt kê exception đã chứng minh cần giữ.

Đạt refactor không có nghĩa đã xây Admin hoặc đã chấm IELTS chính xác. Bước kế tiếp là thiết kế
trong Stitch trước khi đổi UI production; không triển khai UI từ bản xuất Stitch nếu chưa map dữ liệu.
