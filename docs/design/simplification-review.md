# UI simplification review — 2026-10-19

Bản Stitch ngày 18–19/10 bị người dùng từ chối vì rối và lệch UI hiện có. Không triển khai bộ 52 màn đó như design source of truth.

## Nguồn đã kiểm tra

- `learn4/src/app/practice/page.jsx`, `learn4/src/app/dashboard/page.jsx`, `learn4/src/components/speaking/SpeakingNavbar.jsx`: bản Speaking Next.js có sẵn, flow chọn chủ đề → luyện → kết quả; nav ngang, nền sáng, tím #570df8, Lexend.
- `learn4/docs/research/luyennoi-com-9ca6db8d/root-8a5edab2/DESIGN_TOKENS.md`: token và tài liệu tham chiếu cũ.
- `frontend/src/layouts/SpeakingLayout.jsx` và `docs/verification/screenshots/speaking-practice-desktop.png`: UI Speaking đang dùng, nav ngang, Geist, nền #f4f6fb, blue #2563eb và tím ở bước chuẩn bị, tối đa hai vùng nội dung.
- `frontend/src/layouts/ClassroomLayout.jsx`, `frontend/tailwind.config.js`, screenshot teacher/student: giáo viên có sidebar xanh rêu #19352c, nền #f7f7f2; học viên có sidebar slate #0f172a và active blue.

Ưu tiên UI `frontend` hiện tại khi có khác biệt. Dùng bản `learn4/` làm tham chiếu luồng và tinh thần Speaking; không sao chép fake band, streak, lời hứa nâng band hay scoring simulation của bản cũ.

Ngoài filesystem, đã tìm thấy project Stitch **LexiLearn** có sẵn (`13706532085540753166`), gồm hướng xanh rêu và các bản blue. Chỉ đọc để đối chiếu; không thay đổi project này.

## Sai lệch cần sửa

Bộ Stitch trước đổi Speaking sang sidebar, áp navy và hai font mới cho mọi role, thêm quá nhiều card lồng, nhãn kỹ thuật và đoạn giải thích. Những thay đổi này không xuất phát từ code hiện tại. Số frame nhiều không đảm bảo thiết kế phù hợp.

## Quy tắc mới

- Giữ shell từng role và font Geist của frontend. Không có role switch trên learner UI.
- Mỗi màn một việc và một CTA chính. Tối đa hai vùng nội dung chính desktop, một cột mobile.
- Title 24–28px; body 14–16px; helper 12–13px; không ép nội dung vào chữ li ti.
- Dùng khoảng trắng và divider; card chỉ khi cần nhóm thao tác. Không KPI/biểu đồ nếu không giúp quyết định ở màn đó.
- Speaking giữ thanh ngang: Tổng quan / Luyện theo chủ đề / Thi thử / Lịch sử.
- Ghi âm: đề bài + recorder, timer và nút dừng; không feedback, dashboard hay hướng dẫn dài cùng lúc.
- Nghe lại: player + Ghi lại/Gửi câu trả lời. Không waveform trang trí hoặc chỉ số âm thanh kỹ thuật.
- Kết quả: một dòng trạng thái, bốn tiêu chí gọn, một gợi ý tiếp theo; transcript và phân tích theo tiêu chí nằm trong disclosure đóng mặc định. Không lặp CTA ở đầu và cuối.
- Missing score hiển thị “— / Chưa đủ dữ liệu”, tuyệt đối không lấp 0 hoặc suy ra phát âm từ transcript chưa rõ.
- Teacher review giữ audio/transcript bên trái, điểm và nhận xét giáo viên bên phải; AI suggestion thu gọn. Admin là concept mở rộng theo teacher shell, không tự thêm nghiệp vụ.

## Tiêu chí kiểm tra bản mới

Kiểm tra screenshot và nội dung preview thật: đúng shell, font/palette, CTA đơn, không nhãn schema/API/sample-rate/SLA/AI engine; vùng chính đọc được ở kích thước thông thường. Mockup không chứng minh backend hoặc chấm điểm hoạt động.
