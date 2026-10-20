# Stitch design handoff — LexiLearn

> **BẢN CŨ — KHÔNG TRIỂN KHAI.** Người dùng từ chối bộ này vì rối và lệch UI hiện tại. Xem [review tối giản](simplification-review.md) và bộ thay thế được tạo sau review.

Ngày kiểm tra: 2026-10-19. Trạng thái: đã tạo bộ thiết kế để review; chưa triển khai vào ứng dụng.

## Project và sản phẩm bàn giao

- **[LexiLearn — Speaking & Academic Workspace](https://stitch.withgoogle.com/projects/1076417280022710747)**.
- Project ID: `1076417280022710747`.
- Canvas có **52 màn hình và một bảng design system**: 41 desktop, 11 mobile. Trong đó hai màn feedback V2 thay thế hai bản feedback nháp; không phải 52 route riêng biệt.
- Đã mở lại project để kiểm tra lưu trữ, đối chiếu preview với danh mục và đọc nội dung render của hai bản feedback V2.
- [Danh mục màn hình và node ID](stitch/canvas-screen-map.json), [đối chiếu nội dung ban đầu](stitch/content-audit.json), [nội dung feedback V2](stitch/feedback-v2-content-audit.json).
- [Ảnh tổng quan](stitch/canvas-final.jpg), [feedback desktop](stitch/feedback-desktop-v2.jpg), [feedback mobile](stitch/feedback-mobile-v2.jpg), [chi tiết mobile](stitch/feedback-mobile-detail.jpg).
- Không có ZIP export đã xác minh. Project Stitch và các ảnh trên là artifact được bàn giao.

## Phạm vi thiết kế

| Nhóm | Luồng đã có trên canvas |
|---|---|
| Speaking | Trang chủ, thư viện chủ đề, đề bài, kiểm tra micro, chuẩn bị Part 2, ghi âm, nghe lại, gửi bài và phục hồi lỗi, kết quả từng bài, thiết lập mock, lượt Part 3, kết quả mock, lịch sử và tiến bộ |
| Giáo viên | Tổng quan, workspace lớp, tạo/sửa lớp, tạo bài Reading/Listening/Writing/Speaking, hàng đợi chấm, chấm bài khách quan, Writing review, Speaking review, hồ sơ học viên |
| Học viên | Tham gia lớp, trang lớp và lịch sử, làm bài Reading/Listening/Writing, xem kết quả và hồ sơ tiến bộ |
| Quản trị | Tổng quan học thuật, cấp độ/chương trình, quản lý lớp, danh bạ học viên/giáo viên, giáo trình, báo cáo, cấu hình và rubric |
| Mobile | Kiểm tra micro, chuẩn bị, ghi âm, nghe lại/gửi, feedback, lượt mock, giáo viên review, trang lớp, hàng đợi chấm và tổng quan quản trị |

Các màn có nhiều mã trong tên là thiết kế gộp hoặc chứa biến thể. Danh mục này không chứng nhận từng route, dialog và trạng thái trong [inventory](role-page-inventory.md) đã có một frame độc lập. 15 caption trên canvas vẫn mang tên `Generating Screen...` dù preview đã có nội dung; dùng node ID và `intended_name` trong JSON để định vị. Các frame này không được tính là còn đang chờ render.

## Hướng UI

Phong cách học thuật, nền sáng, navy `#17365D`, blue `#2F65A7`, khoảng cách thoáng, ưu tiên đề bài và hành động tiếp theo. Stitch dùng **Be Vietnam Pro** cho nội dung và **JetBrains Mono** cho số/nhãn; khi triển khai cần gom thành tokens chung cho các role.

Speaking ưu tiên một hành động chính mỗi bước, phân biệt chuẩn bị/ghi âm/nghe lại/gửi bài, đồng thời đặt audio, transcript, bằng chứng và phản hồi gần nhau. Trạng thái thiếu dữ liệu phải dễ nhận biết trên desktop và mobile.

## Feedback ưu tiên: S10 V2

- Desktop node: `64d39a45f50741379dcdf06556124a92`.
- Mobile node: `c1931eb1b37d4b37b088c826f0afd569`.
- Đã đọc preview thực tế: FC/LR/GRA có nhãn tạm tính; Pronunciation hiển thị chưa đủ bằng chứng; overall không có band số khi thiếu tiêu chí.
- Không có ngưỡng 80/90 giây hay điều kiện thời lượng để mở khóa phát âm trong hai bản V2.
- Có audio minh họa, transcript, đoạn cần nghe lại, sửa `go → went`, hành động luyện lại và thông báo đây không phải điểm IELTS chính thức.
- Hai bản cũ `cd906149951545709e869cecffbc2ec1` và `5973bc647d3645dd84b0cb717b782f30` giữ lại để tham khảo bố cục, không dùng làm đặc tả nội dung.

## Những điểm cần xử lý khi triển khai

Đây là proposal UI, chưa phải bộ thiết kế đã duyệt toàn bộ nội dung. Stitch có tự thêm câu chữ và hành vi; các lượt sửa bằng prompt không đảm bảo mọi frame đã được cập nhật. Các điểm quan sát được:

1. Một số bản nháp còn copy “chuẩn Cambridge”, ngưỡng thời lượng 80 giây, thời lượng bắt buộc, AI lọc nhiễu hoặc lời hứa khôi phục. Không đưa các nội dung này vào sản phẩm nếu không có đặc tả và bằng chứng hỗ trợ.
2. Feedback V2 desktop vẫn có role switch và chi tiết kỹ thuật như sample rate; bỏ khỏi learner flow trừ khi thực sự cần. Nhãn “Chuẩn thang đo” cũng cần thay bằng mô tả ước lượng luyện tập.
3. Mobile V2 tự thêm lời khuyên phát âm khi đoạn audio chưa rõ. Thay bằng “Nghe lại đoạn này để kiểm tra nội dung”; không suy ra lỗi phát âm từ nhận dạng không chắc chắn.
4. Một số preview ghi âm/mock tự chạy timer hoặc hết giờ. Khi triển khai phải lấy state từ recorder hiện có; không sao chép JavaScript demo của Stitch.
5. Admin và các luồng approve/release/re-record, cross-skill profiles, dedicated mic setup, mock resume là concept; đối chiếu API gaps trong [báo cáo refactor](../verification/refactor-handoff-report.md). Không coi frame thiết kế là feature đã hoàn thành.

## Hợp đồng triển khai và kiểm tra

Giữ engine/jobs và contract `speaking-v3`, nullable bands, evidence IDs, uncertainty và behavior recorder hiện tại. Phân biệt rõ đánh giá AI tạm tính và đánh giá giáo viên. Không suy ra pronunciation chỉ từ transcript hoặc WPM; không dùng điểm mặc định để lấp dữ liệu thiếu.

Nguồn thiết kế: `DESIGN.md`, [page inventory](role-page-inventory.md), [brief](stitch-redesign-brief.md) và báo cáo refactor. Dữ liệu ví dụ là tổng hợp; không upload source, audio học viên, credentials hay dữ liệu lớp thật. Quyền chia sẻ project không thay đổi.

Trong lượt này chỉ tạo thiết kế và tài liệu, không sửa application code. Đã kiểm tra preview/ảnh, số lượng frame và JSON artifacts; không chạy lại typecheck, lint, build hoặc app tests vì không thay mã ứng dụng. Chưa xác minh export code hoặc tương tác end-to-end của sản phẩm từ các mockup.
