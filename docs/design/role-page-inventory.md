# Danh mục page và trạng thái theo role

Ngày lập: 2026-10-18. Dùng để kiểm đủ phạm vi refactor và thiết kế Stitch sau đó.
Nguồn: `frontend/src/App.jsx`, pages hiện tại, backend routers và `DESIGN.md`.

## 1. Cách hiểu phạm vi

- **Có**: route/view đã thấy trong code, không có nghĩa mọi yêu cầu UX đã hoàn chỉnh.
- **Trong page**: modal/tab/state hiện gắn một page; thiết kế riêng trạng thái đó, không tự thêm URL.
- **Dự kiến**: được mô tả trong DESIGN nhưng chưa có route/backend tương ứng; chỉ thiết kế,
  ghi API/data gap, không nối số liệu giả vào sản phẩm thật.
- Speaking là một khu chức năng, không phải role thứ tư. Student dùng để luyện/thi;
  Teacher dùng để giao bài/review; Admin xem vận hành học thuật theo phạm vi được cấp sau này.
- Mô hình hiện tại dùng teacher access code và tên học viên/link lớp; chưa có auth/RBAC Admin.
  Thiết kế quản trị tương lai không tự tạo khả năng truy cập hay bảo vệ dữ liệu.

## 2. Public/context

| ID | Page/view | Hiện trạng | CTA và trạng thái phải thiết kế |
|---|---|---|---|
| P01 | Vào lớp `/join` | Có | Nhập mã/tên, link có sẵn mã, sai mã, lớp không tồn tại, đang xử lý |
| P02 | Nhập mã giáo viên tại `/teacher` | Trong page | Mã đúng/sai, loading; không mô tả như tài khoản/email login |
| P03 | Xác nhận tên người luyện Speaking | Trong dashboard | Thiếu tên, tên hợp lệ, context đã có; không tạo account giả |
| P04 | Not found/network/unavailable | Dự kiến shared states | Trở về khu đang dùng, thử lại; không tự submit lại audio |

Route `/` hiện redirect `/teacher`; không tự thiết kế landing marketing hoặc đổi redirect khi refactor.
`pages/Home.jsx` có file nhưng không nằm trong route map đã đọc; cần audit caller trước khi bỏ.

## 3. Teacher

| ID | Page/view | Route hiện tại hoặc trạng thái | Phạm vi thiết kế |
|---|---|---|---|
| T01 | Tổng quan | `/teacher` — Có | Lớp, bài tập, việc cần chấm; chỉ số có nguồn |
| T02 | Tạo/sửa lớp | Trong page — Có | Tên, level, ghi chú, validation, cancel/save |
| T03 | Workspace lớp | `/teacher/class/:classId` — Có | Bài tập, danh sách/điểm học viên, share link |
| T04 | Tạo bài tập | `/teacher/class/:classId/new` — Có | Chọn skill, nội dung, deadline; preview/approval là gap nếu chưa có |
| T05 | Sửa bài tập | `/teacher/class/:classId/edit/:assignmentId` — Có | State riêng với dữ liệu đã có, lưu lỗi; dùng cùng builder |
| T06 | Builder Reading | Trong T04/T05 | Passage/PDF + dạng câu hỏi + answer key |
| T07 | Builder Listening | Trong T04/T05 | Audio/material + câu hỏi + answer key |
| T08 | Builder Speaking | Trong T04/T05 | Part/cue card/mock mode + hướng dẫn ghi âm |
| T09 | Builder Writing | Trong T04/T05 | Task/prompt/material + yêu cầu bài |
| T10 | Bài nộp và chấm bài | Trong class workspace — Có | Lọc trạng thái/skill, mở bài nộp, feedback/override theo API thực |
| T11 | Review Speaking | Dự kiến workspace chuyên sâu | Audio + transcript + uncertainty + rubric + giáo viên chốt/đề nghị thu lại |
| T12 | Review Writing | Dự kiến workspace chuyên sâu | Essay/prompt + evidence + rubric + giáo viên chốt |
| T13 | Review Reading/Listening | Có nền trong class workspace | Answer/key, auto score, override; disputed/release states là gap nếu chưa hỗ trợ |
| T14 | Hồ sơ học viên theo lớp | Dự kiến | Bài đã nộp, kết quả bốn skill, tiến độ có dữ liệu |
| T15 | Hàng chờ chấm xuyên lớp | Dự kiến | Filter, owner/current status/next action |

Không gắn T11–T15 thành route đang tồn tại. UI “approve/release/request re-record” cần API/lifecycle
thực hiện riêng; endpoint sửa điểm hiện có không tự tương đương quy trình duyệt và audit trail.

## 4. Student

| ID | Page/view | Hiện trạng | Phạm vi thiết kế |
|---|---|---|---|
| U01 | Trang lớp/bài tập | `/student/:classId` — Có | Bài đến hạn, skill, tiếp tục; context lớp/tên |
| U02 | Lịch sử bài nộp trong lớp | `#history` trong U01 — Có | Ngày nộp, trạng thái, điểm nullable, mở kết quả |
| U03 | Hướng dẫn làm bài | `/student/:classId/assignment/:assignmentId` — Có nền | Skill, đề, deadline, bắt đầu |
| U04 | Làm Reading | Trong U03 — Có | Passage, answer navigation, câu còn trống; autosave là gap nếu chưa có |
| U05 | Làm Listening | Trong U03 — Có | Audio controls + câu hỏi; rules playback theo đề |
| U06 | Làm Writing | Trong U03 — Có | Prompt/editor/word count; draft/version là gap nếu chưa có |
| U07 | Làm Speaking theo bài giao | Trong U03 — Có | Prompt, record/playback/re-record/submit, trạng thái chấm |
| U08 | Review trước nộp/xác nhận | Trong page, cần đối chiếu sau refactor | Có thay đổi chưa lưu, thiếu câu, xác nhận hành động |
| U09 | Đã nộp/chờ chấm/đã trả | Trong page — Có nền | Phân biệt AI provisional và giáo viên đã chốt; release policy gap |
| U10 | Kết quả chi tiết từng skill | Trong page — Có nền | Answer/feedback/criterion, nguồn điểm, luyện tiếp |
| U11 | Hồ sơ tiến bộ bốn skill | Dự kiến | Chỉ hiển thị khi có số liệu hợp lệ; không attendance |

## 5. Speaking — ưu tiên thiết kế cao nhất

| ID | Screen/state cần tạo bản thiết kế | Route/source | Nội dung chính |
|---|---|---|---|
| S01 | Speaking home | `/speaking` — Có | Tiếp tục/luyện/thi thử, lần gần nhất, không bịa target/progress |
| S02 | Thư viện topic | `/speaking/practice` — Có | Search/filter Part, topic, loading/empty/error |
| S03 | Topic và chọn Part/câu | `/speaking/practice/:topicId` — Có | Question context, sequence, practice intent |
| S04 | Microphone setup | Modal/state | Permission, input level, test playback, unsupported/denied/no input |
| S05 | Part 1/3 ready | Trong Practice | Một câu hỏi, nghe đề nếu hỗ trợ, hướng dẫn ngắn, record |
| S06 | Part 2 preparation | Trong Practice/Mock | Cue card, chuẩn bị 60s, start early, note nếu được hỗ trợ |
| S07 | Recording | Trong Practice/Mock | Question + elapsed/max, input signal, stop, clear recording state |
| S08 | Playback/re-record | Trong Practice | Audio gốc, elapsed, chọn thu lại hoặc nộp, giữ blob |
| S09 | Upload/queued/processing | Trong Practice/Mock | Pending thực tế, retry an toàn, result chưa sẵn sàng |
| S10 | Practice result tổng quan | Trong Practice | Nullable overall, 4 tiêu chí, 1 ưu tiên cải thiện |
| S11 | Transcript và audio evidence | Trong result | Word IDs/timestamps, chọn đoạn nghe lại, ASR uncertain |
| S12 | Grammar/Vocabulary detail | Tab/panel result | Quote thật, sửa tối thiểu, phân biệt suggestion/error |
| S13 | Pronunciation partial/review | Tab/panel result | Bằng chứng thật hoặc chưa đủ; không tô từ đỏ thành lỗi chắc chắn |
| S14 | Mock setup | `/speaking/mock-test` — Có | Ba Part, trình tự, micro check, bắt đầu |
| S15 | Mock session Part 1/2/3 | `/speaking/mock-test/:testId` — Có route, revalidate session semantics | Một turn tại một thời điểm; timer/progress; recovery gap |
| S16 | Mock completion/result | Trong Mock | Tổng hợp session, coverage/missing, không hứa điểm IELTS chính thức |
| S17 | History | `/speaking/history` — Có | Practice/Mock, status, band null, lọc và replay |
| S18 | Progress/detail/compare | History có nền, compare dự kiến | Cùng model/rubric để so sánh; không đường trend từ partial thành 0 |
| S19 | Failed/cant-hear/needs-review | Variants S09/S10 | Lý do dễ hiểu, bản ghi còn hay mất, bước tiếp theo |
| S20 | Teacher Speaking review | Giao T11 — Dự kiến | Evidence player, rubric, provisional vs final, release/request lại |

Mock route `:testId` có trong frontend không tự chứng minh backend hỗ trợ resume theo URL;
AI bàn giao phải xác nhận ID là exam set hay session, mô tả deep-link behavior thực tế.

## 6. Admin — thiết kế dự kiến theo DESIGN.md

Tất cả nhóm dưới đây chưa có route/Admin authorization trong app đã đọc. Các path nếu thiết kế
sẽ là **đề xuất**, không sửa router production trong refactor hoặc dựng fake CRUD như đã xong.

| ID | Page | Nội dung dự kiến |
|---|---|---|
| A01 | Tổng quan học thuật | Term, lớp/level, completion, điểm bốn skill, drill-down |
| A02 | Levels/programs | Danh sách và form thiết lập level/course |
| A03 | Classes | Danh sách, chi tiết, teacher/enrollment theo data model tương lai |
| A04 | Students | Directory/search/filter |
| A05 | Student profile | Enrollment, submissions, scores, feedback |
| A06 | Teachers | Directory/expertise/assigned classes |
| A07 | Teacher detail | Lớp và hàng chờ chấm; không attendance/teaching hours |
| A08 | Curriculum | Courses/units/lessons/materials và bốn skill |
| A09 | Reports | Level/class outcomes, completion, score trends |
| A10 | Settings/access/rubrics | Term, quyền dự kiến, rubric/release policy, audit; không lộ provider keys |

## 7. Checklist đủ page

Mỗi screen/view ID phải có: role/permission assumption, route hoặc parent state, nguồn dữ liệu,
primary CTA, loading/empty/error, desktop/mobile, keyboard/focus và API gap.
Form create/edit, confirmation, toast và denied/error không cần page URL riêng nhưng phải có variant.
Không dùng screenshot một trang dashboard để nhận là đã thiết kế toàn bộ flow.

AI refactor cập nhật mapping source sau di chuyển và ghi trong báo cáo; giữ nguyên ID thiết kế này
để đối chiếu Stitch screenshots/exports về sau. Thiết kế sẽ được rebase lên code bàn giao thực tế.
