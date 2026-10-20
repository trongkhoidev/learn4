# Brief thiết kế Stitch — LexiLearn theo role, Speaking là trọng tâm

Trạng thái: brief và prompt chuẩn bị cho giai đoạn sau refactor. Chưa tạo project/screen trong Stitch.
Ngày: 2026-10-18. Nguồn: `DESIGN.md` và [page inventory](role-page-inventory.md).

## 1. Điều kiện bắt đầu

Đọc `docs/verification/refactor-handoff-report.md` của AI triển khai trước. Kiểm tra route/data map
và phân biệt feature có thật với design-only. Dùng code đã bàn giao, không copy các clone Next.js.

Phiên lập kế hoạch hiện tại chưa thấy công cụ Stitch được kết nối; tìm plugin “Stitch” không trả
kết quả khớp. Điều này không kết luận Stitch không tồn tại hoặc không thể dùng qua giao diện.
Ở giai đoạn thiết kế, kiểm tra lại Stitch MCP/plugin hoặc phiên browser đã đăng nhập. Không tuyên bố
đã dùng Stitch nếu chưa tạo được project và artifacts thật. Nếu thiếu phiên truy cập, hoàn tất brief/
mapping nhưng ghi rõ phần generate/export chưa thực hiện; không tự đổi sang provider khác rồi gắn nhãn Stitch.

## 2. Hướng thẩm mỹ

Một workspace học thuật hiện đại, dễ đọc, bình tĩnh, ưu tiên thao tác. Giao diện tiếng Việt;
đề Speaking và quote giữ tiếng Anh nguyên gốc. Giữ hướng từ DESIGN hiện tại:

- Canvas `#F5F7FA`, surface `#FFFFFF`, text/nav `#17365D`, accent `#2F65A7`.
- Pale selected `#EAF1F8`, secondary text `#526174`, border `#DCE3EB`, error `#A94F3D`.
- Geist Sans hỗ trợ dấu Việt; số/đồng hồ dùng tabular numerals. Test font fallback thực tế.
- Sidebar desktop khoảng 248px, max content khoảng 1440px; phiên làm bài có focus layout.
- Target control ≥44px, text body khoảng 16px, border radius 8–12px, focus rõ.
- Một CTA nổi bật cho bước hiện tại. Dùng whitespace/divider trước khi thêm card lồng nhau.
- Không gradient/neon/glow, hiệu ứng gây phân tâm, avatar AI giả giám khảo hoặc số liệu bịa.
- Không attendance, billing/subscription hoặc auth UI ngoài mô hình hiện tại nếu chưa được bổ sung.

Ba shell dùng chung tokens/components, khác information density: Admin thiên bảng/tổng quan;
Teacher thiên hàng chờ và review; Student thiên bước tiếp theo. Speaking focus giảm điều hướng
trong lúc thu/thi, chỉ giữ context, timer và nút cần thiết. Không đổi role bằng một selector giả quyền.

## 3. Batch thiết kế và output

| Batch | Screen IDs | Mục tiêu |
|---|---|---|
| D0 | Foundations, shells | Tokens, typography, controls, table/forms/dialog, score/status/evidence patterns |
| D1 | S04–S13, S19 | Luồng Speaking luyện tập hoàn chỉnh, cả trạng thái lỗi/partial |
| D2 | S14–S16, S20/T11 | Thi thử và giáo viên review Speaking |
| D3 | S01–S03, S17–S18 | Vào luyện, thư viện, lịch sử/tiến độ |
| D4 | P01–P04, T01–T15, U01–U11 | Các page Teacher/Student còn lại, all-skill forms/results |
| D5 | A01–A10 | Admin design-only có API/data gap |
| D6 | Cross-flow review | Nhất quán, mobile, accessibility, prototype links, mapping về code |

Thiết kế desktop 1440px và mobile 390px; thử reflow 360px/768px/1024px, không chỉ scale screenshot.
Tablet có thể dùng layout rules thay vì tạo mọi screenshot; recorder/result/review cần có mobile thật.
Mỗi batch kiểm tra cùng design system trước generate tiếp, tránh mỗi screen một style.

Output đích: Stitch project URL/ID, screen IDs theo inventory, screenshots/exports, component/token
notes, clickable flow nếu tool hỗ trợ, và bảng mapping page/state → route/module → data requirements.
Ghi rõ capability nào không có export/prototype thay vì nhận đã làm. Không có raw learner audio,
tên thật, keys hoặc private materials trong prompt/artifacts gửi Stitch; dùng dữ liệu giả có nhãn.

## 4. Chi tiết Speaking Practice

### S04 — kiểm tra mic

Giải thích xin quyền trước browser prompt, chọn thiết bị chỉ khi browser hỗ trợ, input level là
mức thu chứ không điểm phát âm. Test ngắn → nghe lại → tiếp tục. Variants: permission not asked,
denied, no device, device busy, disconnected, unsupported browser, quiet/clipping, working.
CTA đổi theo state, không bật record khi mic chưa sẵn sàng. Không dùng waveform trang trí làm tín hiệu mic thật.

### S05/S06/S07 — ready, chuẩn bị và ghi âm

Desktop chia khoảng 40/60 giữa đề và recording workspace; mobile một cột, đề gọn nhưng mở được,
controls cố định phía dưới có safe-area, không che nội dung. Một câu hỏi mỗi turn.
Part 2 cue card hiển thị đủ bullet, preparation 60s, recording tối đa 120s; đồng hồ hiển thị phase rõ,
không dùng một timer mơ hồ. Practice có thể start early theo backend/UI thực; note-taking đánh dấu gap nếu chưa có.

Recording có nhãn “Đang ghi âm”, elapsed/max, input signal và stop lớn. Không lạm dụng pulse animation;
respect reduced motion. Tránh pause trong Mock nếu rule không cho phép; timeout và exit warning có thiết kế.
TTS đọc đề phải kết thúc trước thu. Ghi rõ mic mất kết nối có giữ đoạn đã thu không dựa trên capability thật.

### S08/S09 — nghe lại, nộp và chờ xử lý

Playback có play/pause, seek, elapsed/duration, record again, submit; submit không đồng thời với recording.
Thu lại cần xác nhận nếu sẽ bỏ bản ghi. Loading tách upload và pending/job processing khi backend có signal.
Nếu server chỉ có pending, dùng “Đang xử lý bài nói”, không bịa phần trăm hay “đang phân tích ngữ điệu”.
Timeout UI không có nghĩa job fail. Nút kiểm tra kết quả/history chỉ khi có route/ID thực; không tự tạo attempt mới.
Mất mạng cần hiển thị bản ghi còn cục bộ hay không; không hứa autosave/resume nếu chưa có hỗ trợ.

### S10–S13 — kết quả có bằng chứng

Phần đầu: status, assessment source, nullable overall. “Chưa đủ dữ liệu” dùng dấu gạch và lý do,
không band 0, không progress ring hoặc màu đỏ khiến hiểu là năng lực kém.
Bốn criterion có nhãn đầy đủ, trạng thái và feedback ngắn; một việc luyện tiếp ưu tiên.
Không ép mọi criterion có band. Điểm AI luyện tập và điểm giáo viên chốt có hierarchy riêng.

Phần chính: audio player đồng bộ transcript; chọn quote thì highlight và replay đúng đoạn với padding.
Độ chắc nhận dạng dùng underline/icon/label, không biến màu ASR thành đúng/sai pronunciation.
Tabs hoặc sections FC/LR/GRA/Pronunciation. Mỗi feedback: quan sát → bằng chứng → ý nghĩa → sửa tối thiểu/
bài tập; phân biệt lỗi thực với gợi ý phong cách. Không viết lại transcript gốc thành đáp án đẹp.
Human correction (nếu tính năng có) lưu tách và nhãn nguồn, không overwrite evidence âm thanh.

Pronunciation thiếu validated evidence: thông báo ngắn, không tạo IPA/lỗi âm giả hoặc band ngẫu nhiên.
Model/version details đưa vào disclosure cho người review, không lộ các nhãn kỹ thuật vào learner flow.
`llm_provider_not_ready` phải được map thành lời nhắn dễ hiểu, không render raw key như nội dung sản phẩm.

Variants bắt buộc: scored, partial, needs_review, insufficient_sample, cant_hear, failed,
legacy result thiếu timestamp, provider thiếu word probability, audio expired/deleted.
Nếu audio không còn, disable replay có lý do, giữ feedback/history nếu policy cho phép.

## 5. Mock Test và teacher review

Mock setup có tổng quan ba Part và mic check. Trong test hiển thị Part/turn và phase rõ, cue card ở
Part 2, không hiện feedback gợi ý giữa các câu làm sai trải nghiệm thi. Lưu tiến trình/reconnect phải
dựa vào backend thật; không quảng cáo resume nếu session/URL chưa hỗ trợ. Kết thúc hiển thị coverage,
tiêu chí còn thiếu và status toàn bài; không coi partial là toàn bài đạt band 0.

Teacher review Speaking ưu tiên desktop ba vùng: danh sách bài/turn; audio + transcript; rubric/feedback.
Mobile chuyển thành các section/tab có owner/status/next action luôn rõ. Cột rubric phân biệt AI
provisional và teacher final; quote chọn được, replay uncertain segments, note và criterion controls.
Actions dự kiến: lưu nháp, duyệt/trả kết quả, yêu cầu thu lại. Cần backend release/permission/audit:
gắn design-only nếu chưa có. Không dùng một nút “AI chấm xong” để tự xuất điểm final cho học viên.

## 6. Teacher/Student/Admin ngoài Speaking

Thiết kế đủ từng ID trong inventory, kể cả modal/state. Teacher builder dùng chung khung với từng skill,
không nhồi cả bốn form lên một màn hình. Review answer key và preview student có current owner rõ.
Writing có text evidence và giáo viên chốt, Reading/Listening có material/answer navigation.
Admin chỉ số drill-down được và dữ liệu minh họa có nhãn, không attendance hoặc tạo bảng số đẹp thiếu nguồn.

Không biến các concept curriculum/terms/enrollment/RBAC trong DESIGN thành production feature chỉ bằng UI.
Tạo `data-gaps.md` trong bàn giao để AI backend triển khai sau, không dùng mock data fallback âm thầm.

## 7. Prompt gốc cho Stitch

Dùng prompt dưới làm project context. Mỗi lần generate bổ sung đúng batch/screen IDs và state matrix,
không yêu cầu tất cả page trong một lần rồi chấp nhận các screen thiếu.

```text
Design LexiLearn, a Vietnamese academic workspace for an English learning center.
The roles are Admin (future design scope), Teacher, and Student. Speaking practice is a
feature used by learners, not a fourth role. Keep role navigation consistent and access-aware.
Design a connected product with a reusable system, not a set of unrelated landing pages.

Use this visual direction: calm academic workspace, canvas #F5F7FA, white surfaces,
navy #17365D text/navigation, blue #2F65A7 primary actions, #EAF1F8 selections,
#526174 secondary text, #DCE3EB borders, #A94F3D errors. Geist Sans with Vietnamese
diacritics and tabular timer numerals. Comfortable typography, 44px minimum controls,
8–12px corners, restrained borders and whitespace. No gradients, neon, glow, decorative
waveforms, attendance metrics, billing or fake authentication/role switching.

Vietnamese interface, English IELTS question text and exact learner quotes. One primary
next action per state. Current role, class/assignment, owner and status must be clear.
Separate teacher-approved results from provisional AI practice estimates. Never imply an
official IELTS result. Missing bands are null with a plain-language explanation, never zero.
ASR uncertainty is not a pronunciation error. Never invent phoneme/stress/intonation evidence.

Speaking is the core experience. Cover microphone setup, question, Part 2 preparation,
recording, playback/re-record, submit, real pending states, evidence-based feedback,
Mock Test, history and teacher review. Keep recording distraction-free. Part 2 preparation
is 60 seconds and speaking is up to 120 seconds. Do not invent percentage progress or
analysis stages unsupported by the supplied data contract. No feedback mid-Mock.

Create desktop at 1440px and responsive mobile at 390px; accommodate 360px and tablet.
Support keyboard navigation, visible focus, text status labels, reduced motion, persistent
form labels, usable timers, and safe-area controls. Do not rely on color alone.

Use labeled fictional sample data only. Mark screens/actions whose APIs do not exist as
future design concepts in handoff notes. Do not pretend those features are implemented.
Keep generated UI code separate from application business logic and API contracts.

For the requested screen IDs, return coherent layouts, key state variants, reused components,
and navigation connections. Preserve screen IDs/names so exports can map back to the app.
```

### Prompt batch Speaking Practice

```text
Use the LexiLearn project design system. Generate S04–S13 plus S19 as one connected
practice flow. Prioritize microphone permission and input check, Part 1/3 question,
Part 2 cue card and 60-second preparation, active recording with elapsed/max timer,
playback/re-record, submit/pending, then partial/scored result with four criteria.
The result workspace must sync original audio to exact transcript evidence. Treat uncertain
recognition as 'Cần nghe lại', not confirmed pronunciation failure. If pronunciation lacks
valid evidence, show 'Chưa đủ dữ liệu' and no band or overall based on only three criteria.
Show minimal corrections versus optional improvements distinctly. Include denied/no-device,
silent/truncated input, upload failure, timeout with continuing job, needs_review, audio
unavailable, and missing word-timing variants. Keep primary actions unambiguous on mobile.
Deliver desktop and mobile frames for ready, recording, playback, pending, result and failed.
```

### Prompt batch Mock và teacher review

```text
Extend the same LexiLearn design system for S14–S16 and S20/T11. Mock is sequential
Part 1, Part 2 preparation/speech, Part 3, completion. Display phase/turn and timer;
do not provide coaching during the test. Make reconnect/exit behavior explicit without
promising unsupported resume. Completion must support partial criteria and no overall.
Teacher review should prioritize original audio, timestamped transcript, uncertain spans,
rubric evidence, provisional AI feedback and separate teacher final judgement. Design
save-draft, release and request-re-record as future capability where APIs are missing.
Provide desktop review workspace and mobile stacked/tabbed alternatives with the same
content and accessible controls. Include pending, missing audio and permission/error states.
```

### Prompt tiếp tục các role

```text
Using the approved LexiLearn components and role shells, design the requested IDs from
the role-page inventory. For each screen preserve role, current class/assignment, primary
action, data source, status, loading/empty/error and responsive behavior. Teacher prepares,
reviews and releases work; Student completes and uses feedback; Admin configures and
reviews academic outcomes. Do not add attendance, billing or unsupported production claims.
Provide create/edit/confirmation variants for forms, all four skill variants for assignment
authoring and attempts, and realistic review states. List missing API capabilities in handoff.
```

## 8. Review và bàn giao thiết kế

- Mỗi inventory ID có screen hoặc variant đã map; không bỏ Student assignment Speaking vì đã có standalone Practice.
- Learner hoàn tất được task tiếp theo mà không cần đọc nhiều giải thích kỹ thuật.
- Cùng tokens/control/status giữa role; đủ desktop/mobile, permission/empty/error/partial.
- Timer/record/playback/submit không mâu thuẫn; pending không dẫn đến submit trùng.
- Transcript, uncertainty, evidence, band source và teacher-final rõ về ý nghĩa.
- Quote/timestamp nằm trong data contract; nguyên văn audio không bị thay bằng rewrite.
- Không có điều khiển không làm gì, permission giả, progress giả hoặc số KPI không có nguồn.
- Kiểm tra contrast, zoom/reflow, focus order, focus trap dialog, labels và reduced motion.
- Lưu `docs/design/stitch-handoff.md`: project/screens URLs, exports, frame IDs, viewport,
  component variants, route/module mapping, data gaps, interaction notes, trạng thái review.
- Chỉ sau bước này mới lên kế hoạch implement UI; code export Stitch là tham chiếu presentation,
  không được ghi đè recorder/state/jobs/assessment đã refactor và kiểm chứng.
