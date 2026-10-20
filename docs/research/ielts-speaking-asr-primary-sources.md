# Nguồn gốc và khuyến nghị ASR cho IELTS Speaking

Ngày kiểm tra: 18/10/2026. Phạm vi: tài liệu công khai; không đăng nhập luyennoi.com, không thu âm/đánh giá trực tiếp dịch vụ đối chiếu, không chạy training. Phần “đề xuất” là quyết định kỹ thuật cần kiểm nghiệm trên dữ liệu của dự án, không phải kết quả thực nghiệm.

## 1. Có thể xác minh gì về luyennoi.com?

[Trang chủ](https://luyennoi.com/) công bố chấm bốn tiêu chí, chấm từng câu, sửa lỗi/cải thiện câu trả lời, forecast, thi thử và công cụ quản lý lớp cho giáo viên. Đây là mô tả tính năng của nhà cung cấp; chưa kiểm chứng hành vi bên trong tài khoản. [Trang đối chiếu](https://luyennoi.com/alphafeature/testimonials) đăng phản hồi và ảnh điểm thi của một số người dùng. Những trường hợp chọn đăng không cung cấp benchmark độc lập, tập mẫu đầy đủ, sai số hay phân bố nhóm người học. Vì vậy chưa có căn cứ khẳng định dịch vụ đó đạt một mức chính xác cụ thể hoặc suy ra hệ thống của dự án đã ngang bằng.

## 2. Whisper cần học đúng nhiệm vụ

[Mã nguồn và README Whisper](https://github.com/openai/whisper) cung cấp trọng số mở, nhận dạng tiếng nói và xử lý bản ghi bằng cửa sổ trượt 30 giây. README mô tả `turbo` là biến thể tối ưu từ `large-v3` với đánh đổi tốc độ/độ chính xác; hiệu năng còn phụ thuộc dữ liệu và môi trường. Việc một mô hình hiểu tốt giọng Việt nói tiếng Anh phải được đo trên chính nhóm người học mục tiêu.

[OpenAI Docs về speech-to-text](https://developers.openai.com/api/docs/guides/speech-to-text) nêu prompt `whisper-1` có giới hạn 224 token và không tuân theo chỉ dẫn như mô hình văn bản đa dụng. Prompt giúp cung cấp ngữ cảnh/tên riêng hoặc định hướng kiểu phiên âm; không cập nhật trọng số và không bảo đảm giữ đủ filler hay lỗi ngữ pháp. Vì vậy “hãy chấm IELTS chính xác” không phải cách training Whisper.

[Hướng dẫn SFT của OpenAI](https://developers.openai.com/api/docs/guides/supervised-fine-tuning) mô tả fine-tuning cho các mô hình được hỗ trợ và bài toán đầu ra văn bản có giám sát; tài liệu đã kiểm tra không thiết lập quy trình fine-tune hosted `whisper-1`. Không nên thiết kế sản phẩm dựa trên giả định API đó cho phép tải dữ liệu IELTS để train Whisper. Muốn cập nhật Whisper thực sự, chọn pipeline trọng số mở và hạ tầng huấn luyện riêng.

[Hướng dẫn của đội Hugging Face Transformers](https://huggingface.co/blog/fine-tune-whisper) trình bày fine-tuning Whisper bằng cặp audio–transcript, feature extractor, tokenizer, sequence-to-sequence trainer và WER. Đầu vào cần lấy mẫu đúng 16 kHz. Ví dụ preprocessing đệm/cắt ở 30 giây: không được đưa audio hai phút kèm toàn bộ transcript vào pipeline cắt 30 giây vì nhãn sẽ không còn khớp audio.

### Đề xuất chọn baseline và checkpoint

1. Giữ `turbo` hiện tại làm baseline A; khóa revision, cấu hình decode, VAD và phiên bản runtime.
2. Benchmark cùng tập dữ liệu với `large-v3` chưa fine-tune làm baseline B. Không mặc định mô hình lớn sẽ giải quyết lỗi bảo toàn disfluency.
3. Nếu có GPU phù hợp, thử LoRA trên `openai/whisper-large-v3-turbo` trước vì gần cấu hình phục vụ hiện tại; ghi rõ đây là ứng viên thí nghiệm. So sánh với phiên bản turbo chưa fine-tune trên người nói chưa từng gặp.
4. Chỉ cân nhắc full fine-tuning hoặc LoRA `large-v3` khi audit lỗi và benchmark cho thấy đáng đổi thêm chi phí/độ trễ. Với tài nguyên nhỏ, `small.en` có thể dùng để kiểm tra pipeline dữ liệu, không phải mặc định thay turbo khi phục vụ.
5. Huấn luyện bằng transcript nguyên văn: giữ “I go yesterday”, lặp từ, từ đệm nghe được và self-correction. Không dùng câu đã sửa thành “I went yesterday” làm nhãn ASR. Bản diễn đạt tốt hơn phải là đầu ra coaching riêng.
6. Không đưa band, bài mẫu hoặc từ khóa bắt buộc của đề vào nhãn ASR; chúng tạo mục tiêu khác nhận dạng lời nói. Ngữ cảnh nhận dạng chỉ gồm dữ kiện có thật và không được dùng để đoán đáp án.

## 3. ASR và phát âm là hai phép đo khác nhau

[Microsoft Pronunciation Assessment](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment) trả về dữ kiện mức phoneme/từ và prosody như stress, intonation, nhịp nói. Tài liệu phân biệt scripted/unscripted và nói mô hình STT của chế độ unscripted khác Azure STT thông thường. Đây là ví dụ cụ thể cho việc nhận dạng từ và đánh giá cách phát âm là hai nhiệm vụ riêng. Không nên lấy điểm 0–100 của dịch vụ này chia tỷ lệ thành band IELTS; cần hiệu chuẩn độc lập.

[Band descriptors IELTS](https://ielts.org/cdn/ielts-guides/ielts-speaking-band-descriptors.pdf) xét độ dễ hiểu, connected speech, stress, rhythm và intonation, bên cạnh âm/từ. Accent không phải lỗi tự động. Tài liệu còn nói đánh giá theo hiệu suất trung bình qua tất cả các phần. Suy luận sản phẩm: một câu ngắn chỉ đủ phản hồi luyện tập hạn chế; không thể gọi kết quả đó là điểm thi toàn bài đã xác thực.

**Đề xuất ranh giới bằng chứng:**

- Transcript hỗ trợ lexical resource và grammatical range/accuracy, nhưng phải đưa uncertain spans vào grader để tránh phạt lỗi nhận dạng thành lỗi học viên.
- Fluency cần thời gian từ audio, khoảng dừng thật và disfluency. Dấu câu do ASR sinh không đủ để đo pause; không suy ra hesitation vì thiếu dấu câu.
- Pronunciation cần bằng chứng audio có timestamp và mô hình/đánh giá âm học phù hợp. Không có dữ kiện thì trả `insufficient_evidence`, `band: null`, lý do và bước bổ sung.
- Forced alignment chỉ đặt transcript lên trục thời gian; bản thân sự tồn tại của alignment không chứng minh có chấm phoneme chính xác.
- Câu rewrite là ví dụ luyện tập, không thay `transcript_verbatim` và không dùng lại để chấm câu nói gốc.

## 4. Rubric đúng và giới hạn band

[IELTS giải thích cách chấm](https://ielts.org/news-and-insights/demystifying-the-ielts-speaking-test): bốn tiêu chí gồm Fluency and Coherence, Lexical Resource, Grammatical Range and Accuracy, Pronunciation; trọng số bằng nhau. [Định dạng Speaking chính thức](https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-speaking) có ba phần trong 11–14 phút, giám khảo đánh giá xuyên suốt bài thi.

**Đề xuất:** gắn `scope: answer_practice` hoặc `scope: full_mock`; ghi `practice_estimate`, không tự nhận điểm IELTS chính thức. Chỉ tính tổng ước lượng bốn tiêu chí khi cả bốn đủ bằng chứng theo chính sách chất lượng đã kiểm nghiệm; nếu pronunciation thiếu thì không mặc định 5/6/7 hoặc dùng trung bình ba tiêu chí thay cho tổng bốn. Không đổi WPM, số filler hoặc lexical diversity thành band bằng công thức cố định.

## 5. Đo ASR trước khi train

[JiWER của Jitsi](https://github.com/jitsi/jiwer) cung cấp WER, CER và công cụ phân tích sai khác; bản 4 định nghĩa trường hợp transcript tham chiếu rỗng để đánh giá hallucination trên im lặng. WER tính lỗi thay thế, xóa, chèn theo số từ tham chiếu; CER đo mức ký tự. Các phép đo này đánh giá transcript so với nhãn, không tự đo mức thành thạo IELTS.

### Thiết kế benchmark đề xuất

- Thu một pilot gồm nhiều người nói thực, trình độ khác nhau, giọng vùng miền, thiết bị và độ ồn thường gặp; có cả Part 1 ngắn và Part 2 dài. Quy mô khởi đầu thực dụng: 30–50 người nói, vài trăm lượt trả lời; đây là mốc lập kế hoạch, không phải cỡ mẫu đủ chứng minh độ chính xác cho mọi nhóm.
- Tạo nhãn nguyên văn do người nghe audio xác nhận. Tách `verbatim_reference`, `normalized_reference` và `uncertain_spans`; dùng hai người kiểm tra các câu khó, giải quyết bất đồng thay vì tự lấy output model làm ground truth.
- Chia train/dev/test theo **người nói** trước khi cắt chunk; mọi đoạn từ một người/bản ghi nằm cùng split. Giữ thêm tập topic chưa thấy. Không tune prompt/hyperparameter trên test.
- Báo cáo normalized WER và verbatim WER với quy tắc normalization được khóa; CER là chỉ số bổ sung. Không normalize bỏ filler/lặp/từ sai nếu mục tiêu đang đo bảo toàn các đặc điểm đó.
- Thêm tỉ lệ giữ filler, self-correction, lặp từ; tỉ lệ ASR tự sửa grammar; giữ nguyên phủ định, số, thì, tên riêng; hallucination trên silence/noise; độ lệch timestamp và recall của vùng không chắc chắn.
- Chia kết quả theo band tham chiếu, accent, độ ồn và thiết bị. Ước lượng bất định bằng bootstrap theo người nói thay vì coi các chunk cùng người là mẫu độc lập.
- Đo latency p50/p95, chi phí và thời gian xử lý/audio duration. Không chọn checkpoint chỉ theo loss hoặc WER trung bình.

### Điều kiện tiến sang fine-tune

Chỉ train khi lỗi lặp lại có nhãn đáng tin, pipeline chunk/audio đúng và thay prompt/decoding chưa đủ. Khởi đầu có thể gán nhãn 20–50 giờ audio thực để làm pilot; mở rộng theo learning curve, không hứa một số giờ nhất định sẽ đạt chuẩn. Giữ dữ liệu im lặng/ồn và mẫu người nói khó; tránh dùng TTS giọng chuẩn làm phần chính của tập train mục tiêu giọng Việt tự phát.

Chọn checkpoint bằng dev set, đánh giá test một lần cho quyết định. Đề xuất gate ban đầu có thể là cải thiện WER tương đối ít nhất 10% so với baseline và không làm xấu mức bảo toàn lỗi/filler hay nhóm accent quan trọng; con số này là quyết định sản phẩm cần chốt theo baseline, không phải chuẩn ngành. Tách gate ASR khỏi gate chấm IELTS.

## 6. Kiểm định grader và output

**Đề xuất thực nghiệm riêng:** tập mock đầy đủ do hai người chấm có chuyên môn IELTS đánh giá độc lập, giải quyết bất đồng. So sánh MAE band từng tiêu chí, sai số tổng, tỷ lệ trong ±0.5 band, thiên lệch theo nhóm, độ nhất quán khi chạy lại và tỷ lệ nhận xét được audio/transcript xác nhận. Không dùng mức tương quan đơn lẻ để tuyên bố “sát thi thật”. Chưa có dữ liệu này thì kết luận phải là “chưa xác nhận được độ chính xác”.

Output nên lưu `audio_quality`, `asr_model_revision`, `transcript_verbatim`, `uncertain_spans`, `evidence[]` chứa quote/timestamp, trạng thái đủ bằng chứng cho từng tiêu chí, band ước lượng hoặc null, hướng dẫn luyện tập và phiên bản rubric/prompt. Validator phải kiểm tra quote là substring thật, timestamp nằm trong audio, không có lỗi học viên nằm hoàn toàn trong uncertain spans, và không có pronunciation band khi thiếu audio evidence.

Các thay đổi trên là kế hoạch, chưa được triển khai hoặc huấn luyện trong tài liệu này. Nên hoàn thiện ranh giới bằng chứng và benchmark trước khi chi tiền huấn luyện.
