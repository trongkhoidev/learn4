# Prompt bàn giao AI refactor

Sao chép khối bên dưới cho AI có quyền đọc/sửa workspace. AI cần đọc cả file kế hoạch
được tham chiếu; không chỉ dựa trên đoạn prompt tóm tắt.

```text
Bạn là kỹ sư chịu trách nhiệm cleanup và refactor LexiLearn từ đầu đến nghiệm thu.
Workspace dự án: /Users/admin/repos/learn4. Thực hiện công việc, không chỉ đưa đề xuất.

Đọc hướng dẫn AGENTS.md áp dụng tại workspace. Nếu .codegraph tồn tại ở root repository
liên quan thì dùng CodeGraph trước khi tìm code. Đọc README.md, DESIGN.md và:
  docs/plans/project-cleanup-refactor-plan.md
  docs/design/role-page-inventory.md
  docs/design/stitch-redesign-brief.md
Đọc code, callers, schemas, tests mới nhất. Các tài liệu audit Speaking cũ chỉ là bối cảnh;
không dùng chúng để ghi đè tiến bộ code hiện tại.

MỤC TIÊU
- Modular monolith rõ trách nhiệm, source theo tính năng, module có interface nhỏ.
- Giữ backend/ và frontend/ ở root, giữ FastAPI/SQLAlchemy/React/Vite/JavaScript/npm.
- Tách layout từng role, domain API clients, controller/state khỏi UI, Speaking engine khỏi
  provider transport. Cấu trúc cụ thể và move map nằm trong kế hoạch.
- Dọn docs/diagnostics/artifacts theo policy, giữ nguyên dữ liệu và lịch sử.
- Code dễ thay UI bằng thiết kế Stitch ở bước kế tiếp. Chưa redesign UI lần này.

RÀNG BUỘC
1. Git root hiện có thể là thư mục cha /Users/admin/repos. Giới hạn mọi Git operation vào
   dự án này. Có nhiều thay đổi chưa commit và file untracked từ trước: giữ và tích hợp chúng;
   không reset/restore/clean, không stage hoặc sửa file của project anh em.
2. learn4/ lồng bên trong là gitlink có repo riêng, luyennoi-clone/ là code tham chiếu.
   Giữ chúng tại chỗ, đánh dấu reference-only/exclude khỏi app tools; không merge/delete/move.
3. Không xóa database/storage/audio/model cache/.env; không đưa secret/PII vào báo cáo hoặc Git.
   Debug/media thiếu provenance phải giữ an toàn và ghi manifest, không thành test fixture.
4. Không đổi URL/API/form keys/HTTP statuses/localStorage keys/table names/FK/cascade/scoring.
   Contract speaking-v3, legacy result adapter, partial/null, uncertainty và evidence IDs phải giữ.
   Không tự suy pronunciation band từ transcript hoặc ASR confidence. Không mock âm thầm khi
   thiếu credentials production. Không thay durable jobs bằng in-memory queue.
5. DESIGN.md nêu Admin/Teacher/Student, nhưng Admin/RBAC chưa có trong code hiện tại.
   Refactor không tự thêm auth, billing, admin CRUD, attendance hay endpoint mới.
   Role UI không phải cơ chế bảo mật. Teacher code và learner name context giữ như baseline.
6. Không chuyển framework/language/package manager, không thêm microservices, generic CRUD,
   generic event bus hoặc file rỗng cho đủ mô hình phân tầng.
7. Không sửa UI theme/interaction/scoring trong refactor. Bug chặn compatibility phải có
   reproduction, test và ghi riêng; tính năng mới đưa sang backlog.

THỰC THI
R0: Inventory file/module/imports/routes/OpenAPI/data paths. Ghi git diff paths ban đầu.
    Chạy baseline pytest, build và Playwright bằng DB/storage test biệt lập + provider mock.
    Không đọc secrets để đưa vào log. Ghi failures có sẵn trước khi sửa.
R1: Cleanup an toàn, docs map và reference-only manifest.
R2: Backend theo feature, transaction/session/lifecycle rõ, Base/ORM register duy nhất;
    tách Speaking orchestration, raters/contracts/rubric, STT/LLM/audio/storage adapters;
    job processing/retry/restart vẫn hoạt động cho Practice/Mock/assignment.
R3: Frontend app/routes/layouts/features/shared; feature APIs dùng transport chung;
    Practice/Mock reducer/controllers, recorder/polling/timers cleanup đúng.
    Giữ import entry, deep links, browser back và giao diện hiện có.
R4: Tooling/excludes/lint hợp lý, dev/docker paths, README. Không blanket-ignore lỗi thật,
    không format cả repo, không tạo lockfile thứ hai. Chạy checks sau mỗi nhóm thay đổi.
R5: Chốt move map, bỏ shim tạm khi hết caller, full regression và báo cáo bàn giao.

KIỂM CHỨNG
- Backend full pytest; relevant tests trong từng phase.
- npm ci, npm run build, frontend lint và backend ruff theo config đã thêm.
- Playwright: Teacher/Student navigation/access, Speaking fake mic -> record -> playback ->
  submit -> pending -> partial/scored/failed -> history; Part 2 timer, mock session, null band.
- Không thay assertion nghiệp vụ hoặc skip/delete test để xanh. Không gọi test mock là accuracy.
- So sánh OpenAPI/contract + ORM metadata + data compatibility; không lộ answer key cho student.
- Check source paths, scripts/calibration/asr_training, health/ready, job retry/recovery,
  media serving qua Vite/nginx, temporary files/tracks/object URLs cleanup.
- docker compose config --quiet và isolated Docker build/smoke khi môi trường hỗ trợ.
- Nếu không có typechecker thì báo N/A, không nhận build là typecheck.

ĐẦU RA
Tạo docs/verification/refactor-handoff-report.md theo mẫu trong kế hoạch: cấu trúc cuối,
file mapping, commands/results, API/DB compatibility, screenshots, invariants Speaking,
design data gaps và limitations. Cập nhật docs/architecture với route/API/module map thực tế.
Không cần hỏi lại về lựa chọn kỹ thuật thường lệ. Tiếp tục đủ R0–R5; chỉ dừng phần thực sự
thiếu credential/hạ tầng hoặc có nguy cơ mất dữ liệu, hoàn tất phần không phụ thuộc.
Không commit/push/deploy hoặc chạy training chỉ vì refactor hoàn thành.

Sau khi xong, bàn giao lại để dùng Stitch thiết kế toàn bộ page theo role,
ưu tiên Speaking Practice/Mock/feedback/teacher review. Không tự thay thiết kế đó bằng UI
do bạn đoán và không tuyên bố đã dùng Stitch nếu chưa có project/screen artifacts thật.
```
