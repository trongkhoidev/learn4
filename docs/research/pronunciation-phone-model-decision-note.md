# Decision note: lựa chọn phone-posterior model cho Pronunciation Engine

Ngày: 2026-10-21. Trạng thái: **chưa chọn production model** — quyết định cuối phụ thuộc
benchmark trên audio người Việt luyện IELTS, license review lần cuối và availability
weights. Không model nào trong bảng dưới được coi là production-ready.

Yêu cầu: English phone posterior theo frame (không phải chỉ WER), mở weights,
license cho phép serving, chạy được trên CPU container, revision pin được.

## Ứng viên so sánh

| Tiêu chí | A. `facebook/wav2vec2-lv-60-espeak-cv-ft` | B. Allosaurus | C. MFA English acoustic model |
| --- | --- | --- | --- |
| Loại output | CTC posterior per frame theo espeak phone inventory (posteriors lấy bằng CTC softmax) | IPA phone nhận dạng (top phones, k-best) | Phone/word alignment (không posterior thuần) |
| License (kiểm tra 2026-10-21) | Apache-2.0 (model card Hugging Face) | GPL-3.0 (repo `xinjli/allosaurus`) | Phần mềm MFA MIT; model phải kiểm license tại nguồn tải |
| Phone inventory | Rộng, espeak-based, cần mapping về ARPAbet/MFA; mapping mất thông tin phải được ghi | Universal (many languages), cần lọc về inventory English | ARPAbet chuẩn, khớp CMUdict |
| Revision pinning | Commit hash + checksum manifest được | Package + model file checksum được | Model zip checksum được |
| Target CPU/RAM (ước lượng, chưa đo) | large model ~1.3 GB weights, RAM thực tế >2 GB; cần benchmark RTF trên container 1 vCPU | Nhẹ hơn, nhưng GPL + pipeline riêng | Nhẹ, chạy OK trên CPU |
| Benchmark requirement | RTF, posteriors sanity, mapping coverage, đồng nhất với lexicon | | |

## Quyết định hiện tại

1. **Ứng viên chính để benchmark tiếp theo: A (wav2vec2 espeak)** vì license đã xác nhận
   Apache-2.0 và output posterior per frame đúng dạng engine cần. Chưa pin vì chưa đo
   RTF/RAM trên container mục tiêu và chưa xác nhận mapping phone inventory.
2. B (Allosaurus) bị hạ ưu tiên: GPL-3.0 dar cảnh báo copyleft khi serving nội bộ; giữ
   làm fallback nếu A thất bại benchmark.
3. C (MFA) giữ vai trò alignment (đã có adapter), không dùng làm phone posterior.
4. **Blocked:** chưa có weights/cache local, chưa benchmark, chưa audit mapping
   ARPAbet <-> espeak phones. Cho tới khi xong cả ba: runtime dùng
   FrozenPhoneModel/fake adapter trong tests, không tải model trong CI, production
   mode giữ `disabled`.
