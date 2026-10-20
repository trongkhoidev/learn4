# LexiLearn — UI tối giản

Ngày review: 2026-10-19.

**[Mở bộ thiết kế thay thế trên Stitch](https://stitch.withgoogle.com/projects/17195059594239635825)**

Bộ 52 màn trước bị người dùng từ chối. Bộ mới tập trung 14 màn chính để thể hiện bố cục tối giản và cách giữ shell từng role; không phải bản thiết kế độc lập cho mọi route/dialog của toàn hệ thống. Chưa sửa mã ứng dụng.

## Cơ sở đối chiếu

Đã đọc mã Speaking có sẵn trong `learn4/src`, token/reference trong `learn4/docs`, layout/components hiện tại của `frontend`, và ảnh Speaking/Teacher/Student ở `docs/verification/screenshots`. [Review nguồn và sai lệch](../simplification-review.md) ghi rõ đường dẫn. Ưu tiên frontend hiện tại nếu bản Next.js cũ khác biệt.

Thiết kế mới giữ Speaking dùng navbar ngang, Geist, blue/violet và nền sáng; giáo viên dùng sidebar xanh rêu/nền ấm. Học viên dùng sidebar slate với active blue. Quản trị là concept theo shell xanh rêu, có menu riêng. Không có role switch trong Speaking.

## 14 màn thực tế

| Nhóm | Màn |
|---|---|
| Speaking desktop | SP01 Tổng quan, SP02 Chủ đề, SP03 Chuẩn bị, SP04 Ghi âm, SP05 Nghe lại, SP06 Kết quả, SP07 Lịch sử, SP08 Thi thử |
| Speaking mobile | SP04-M Ghi âm, SP06-M Kết quả |
| Giáo viên | TE01 Danh sách lớp, TE02 Chấm Speaking |
| Học viên | ST01 Bài tập |
| Quản trị concept | AD01 Danh sách lớp |

[Danh mục node ID và nội dung preview](screen-audit.json), [kiểm tra sau sửa sidebar](post-correction-audit.json). Caption một số frame vẫn là `Generating Screen...` dù nội dung đã render; dùng `intended_name` và `node_id` trong JSON để định vị. Nội dung trong JSON là snapshot minh họa, không phải đặc tả chấm điểm.

## Những thay đổi chính

- Speaking: tối đa hai vùng nội dung; trạng thái chuẩn bị, ghi âm, nghe lại và kết quả tách riêng.
- Ghi âm: đề bài, timer và nút dừng; bỏ dashboard và phân tích trong lúc nói.
- Nghe lại: player, gửi hoặc ghi lại; không trộn transcript vào bước này.
- Kết quả: bốn điểm gọn, một gợi ý cải thiện, ba disclosure đóng mặc định. Thiếu phát âm thì để “—”, không có overall số. Nội dung chi tiết chỉ mở khi người học cần.
- Teacher overview: danh sách lớp thay KPI/chart dày. Teacher review: audio/transcript bên trái, điểm và nhận xét bên phải; AI gợi ý thu gọn.
- Đã phát hiện và sửa sidebar giáo viên bị Stitch áp nhầm vào học viên/quản trị; đọc lại preview để xác minh menu đúng. Lịch sử bỏ thống kê band trung bình; mock bỏ câu khẳng định chuẩn hóa/giám khảo AI.

## Ảnh review

- [Speaking mobile: ghi âm và kết quả](speaking-mobile.jpg)
- [Kết quả desktop — ảnh trước lượt bỏ footer](speaking-result.jpg)
- [Màn học viên sau sửa sidebar](student-home.jpg)
- [Màn giáo viên chấm Speaking](teacher-review.jpg)
- [Canvas sau lượt sửa cuối](canvas-final.jpg)

## Giới hạn và yêu cầu khi triển khai

Đây là bản thiết kế để review, không phải bản emulation pixel-perfect đã duyệt. Stitch vẫn có một số sắc nền/panel và nhãn phụ khác code gốc. Frame desktop tự xuất hiện ở kích thước khoảng 1280×1024/1093 thay vì 1440×900 yêu cầu; phần nội dung chính gọn nhưng chưa kiểm chứng fit viewport thực tế. Cần dùng spacing/font tokens của frontend khi triển khai, không chép nguyên CSS từ mockup.

Preview recorder còn có timer chạy dù prompt yêu cầu static. Không dùng JavaScript demo này làm recorder thật. Footer chung và một số lời giải thích đã được yêu cầu bỏ; không khẳng định mọi copy thừa trên mọi frame đã được loại hết. Màn giáo viên có điểm minh họa; triển khai phải lấy dữ liệu thực và giữ nullable scores, trạng thái AI tạm tính/giáo viên, uncertainty/evidence theo contract hiện có. Không tự điền điểm mặc định hoặc suy ra phát âm từ transcript.

Các màn sâu như assignment builder, Reading/Listening/Writing attempt, hồ sơ, settings và toàn bộ state/error chưa được dựng lại thành frame riêng trong bộ 14 màn này. Áp quy tắc mới trong review nguồn; không dùng lại bộ cũ như visual source of truth.

Không upload source hoặc audio người học. Auto-review đã chặn thao tác đính kèm ảnh UI nội bộ lên Stitch; ảnh đó không được gửi. Bộ này được tạo bằng mô tả bố cục/màu sắc và ví dụ tổng hợp, không có thay đổi quyền chia sẻ.

Kiểm tra đã làm: đọc preview 14 màn; lưu screenshot Speaking desktop/mobile, học viên và giáo viên; đối chiếu sidebar sau sửa; kiểm tra JSON, node ID và liên kết artifact. Không chạy build/lint/app tests vì không thay application code; chưa xác minh tương tác sản phẩm hoặc ZIP export.
