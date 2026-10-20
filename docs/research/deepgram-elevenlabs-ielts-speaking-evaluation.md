# Đánh giá Deepgram và ElevenLabs cho IELTS Speaking

Ngày kiểm tra: 20/10/2026. Tất cả thông tin nhà cung cấp trong tài liệu này lấy từ nguồn chính thức đang công khai tại ngày kiểm tra. Giá, quota và tính năng có thể thay đổi; cần khóa model/version và lưu cấu hình trong mỗi lần benchmark.

## Kết luận để ra quyết định

Deepgram Nova-3 và ElevenLabs Scribe v2 đều đáng đưa vào benchmark ASR của sản phẩm. Chúng có thể cải thiện transcript, tên riêng, timestamp và tín hiệu bất định, nhưng **không bên nào cung cấp phép chấm IELTS hoặc pronunciation assessment có thể dùng trực tiếp cho bốn tiêu chí**. Cả hai chỉ nên là tầng thu thập bằng chứng cho grader:

- **Fluency and Coherence:** timestamp, pause, filler, repetition và self-correction hỗ trợ đo fluency; coherence vẫn cần phân tích nội dung theo rubric.
- **Lexical Resource:** transcript nguyên văn hỗ trợ đánh giá range, precision, collocation và paraphrase; lỗi ASR phải được loại khỏi bằng chứng chấm.
- **Grammatical Range and Accuracy:** transcript nguyên văn hỗ trợ đánh giá cấu trúc và lỗi; không được chạy transcript editing hoặc chế độ làm sạch trước khi chấm.
- **Pronunciation:** word confidence/log probability của ASR đo mức chắc chắn khi nhận dạng, không đo chính xác phoneme, word stress, sentence stress, rhythm, intonation, connected speech hay listener effort. Cần tầng âm học/phát âm riêng và hiệu chuẩn với giám khảo.

Khuyến nghị hiện tại là benchmark song song **Faster Whisper hiện tại**, **Deepgram Nova-3 batch** và **ElevenLabs Scribe v2 batch** trên audio thật của người Việt luyện IELTS. Không đổi nhà cung cấp chỉ dựa trên quảng cáo WER. Nếu cần feedback ngay sau khi ghi âm, batch vẫn phù hợp cho chấm cuối lượt; realtime là luồng UX riêng và không nên quyết định band từ partial transcript.

## Khả năng của Deepgram

### Nhận dạng và ngôn ngữ

[Deepgram Models & Languages](https://developers.deepgram.com/docs/models-languages-overview/) mô tả Nova-3 là model general-purpose cao nhất của họ cho batch và streaming, gồm English `en`, các locale `en-US`, `en-GB`, `en-AU`, `en-IN`, `en-NZ`, cùng Vietnamese `vi`. [Language docs](https://developers.deepgram.com/docs/language/) nói English model hướng tới các accent toàn cầu nhưng chuẩn hóa chính tả đầu ra theo American English. Nếu đặt một ngôn ngữ cụ thể, hệ thống chỉ cố nhận dạng ngôn ngữ đó; code-switching cần model/cấu hình multilingual tương thích.

Điều này có hai hệ quả cho bài IELTS của người Việt:

1. Dùng English model cho phần trả lời tiếng Anh; một địa danh Việt như “Quảng Trị” nên được truyền bằng keyterm, không đổi toàn bộ request sang Vietnamese.
2. Không đánh giá lỗi spelling Anh–Anh/Anh–Mỹ từ chính tả mà Deepgram tự chuẩn hóa.

Deepgram tự công bố Nova-3 giảm WER so với một nhóm đối thủ, nhưng đây là số liệu của nhà cung cấp và không mô tả riêng người Việt nói tiếng Anh. Nó không thay thế benchmark của sản phẩm.

### Keyterm và tên riêng

[Keyterm Prompting](https://developers.deepgram.com/docs/keyterm) hỗ trợ Nova-3 batch, Nova-3 streaming và Flux. Tài liệu công bố khả năng tăng keyterm recall rate “up to 90%”, hỗ trợ tới 100 term, khuyến nghị thực tế tập trung vào khoảng 20–50 term quan trọng, và giới hạn tổng cộng 500 token mỗi request/update. Streaming cho phép thay danh sách keyterm giữa luồng qua message `Configure`; regional endpoint ngoài global hiện chưa hỗ trợ cập nhật giữa luồng.

Keyterm là bias nhận dạng, không phải ground truth. “Đà Nẵng” trong danh sách không chứng minh người học đã nói “Đà Nẵng”. Kết quả phải tiếp tục lưu raw audio, raw transcript, confidence và trạng thái “cần nghe lại” cho trường hợp cạnh tranh như `Ghana`/`Đà Nẵng`.

### Timestamp, confidence, filler và diarization

[Deepgram confidence docs](https://developers.deepgram.com/docs/confidence) nói mỗi word có `start`, `end`, `confidence`; confidence transcript và word là hai trường riêng. Họ mô tả word confidence là xác suất đã hiệu chuẩn, đồng thời cảnh báo:

- confidence không cung cấp second-best correction;
- confidence cao không bảo đảm WER thấp trên một transcript cụ thể;
- model có thể tự tin nhưng sai khi accent/domain không khớp;
- không so trực tiếp confidence giữa các nhà cung cấp;
- confidence của final transcript đáng tin hơn interim result.

[Pre-recorded feature matrix](https://developers.deepgram.com/docs/stt-pre-recorded-feature-overview) liệt kê filler-word capture cho English, utterance segmentation, punctuation, diarization và smart formatting. [Diarization docs](https://developers.deepgram.com/docs/diarization) trả speaker label cho từng word và `speaker_confidence` ở batch; Nova batch hỗ trợ diarization. Trong IELTS một người nói, diarization chủ yếu giúp tách giọng examiner, prompt phát từ loa hoặc tiếng chen vào khỏi câu trả lời.

Khi chấm, bật giữ filler và giữ riêng transcript verbatim. Smart formatting chỉ tạo bản hiển thị; punctuation/capitalization do ASR sinh không được tính là năng lực grammar của người học.

### Batch, streaming và giới hạn

[Pre-recorded API](https://developers.deepgram.com/docs/pre-recorded-audio) trả word timing/confidence và nhận file tới 2 GB; request trực tiếp quá 10 phút với Nova/Base/Enhanced có thể timeout, khi đó dùng callback/asynchronous flow. [Streaming API](https://developers.deepgram.com/reference/speech-to-text/listen-streaming) trả interim/final transcript qua WebSocket. [Endpointing](https://developers.deepgram.com/docs/endpointing/) dùng VAD và khoảng im lặng để báo speech final. Flux thêm model-native turn detection nhưng chỉ cần thiết khi sản phẩm có hội thoại examiner realtime; Nova-3 phù hợp hơn cho lượt trả lời đã thu âm và có bộ feature rộng.

### Giá và credit

[Trang giá Deepgram](https://deepgram.com/pricing) công bố $200 credit ban đầu cho Pay As You Go, không yêu cầu thẻ, sau đó trả theo dùng. Tại ngày kiểm tra:

- Nova-3 monolingual pre-recorded: **$0.0043/phút**; multilingual: **$0.0052/phút**.
- Nova-3 monolingual streaming đang có giá khuyến mại **$0.0048/phút**; multilingual **$0.0058/phút**.
- Keyterm prompting: cộng **$0.0013/phút**; smart formatting và diarization được ghi là included cho pre-recorded.
- Pay As You Go công bố tối đa 50 concurrent REST và 150 WSS request.

Các con số streaming có nhãn promotional; mô hình chi phí phải đọc giá tại runtime/procurement thay vì hard-code.

## Khả năng của ElevenLabs

### Nhận dạng và ngôn ngữ

[ElevenLabs STT overview](https://elevenlabs.io/docs/overview/capabilities/speech-to-text) mô tả Scribe v2 batch và Scribe v2 Realtime hỗ trợ hơn 90 ngôn ngữ, gồm English và Vietnamese; batch có smart multi-language detection. Scribe v2 batch hướng tới độ chính xác cao và audio dài; realtime hướng tới độ trễ khoảng 150 ms. Tuyên bố “over 98% transcription accuracy” trên [trang giá API](https://elevenlabs.io/pricing/api) là số liệu marketing của nhà cung cấp, không phải kết quả trên learner English của dự án.

### Keyterm và xử lý transcript

[Keyterm prompting guide](https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/batch/keyterm-prompting) cho phép tối đa 1.000 keyterm ở batch, tối đa 50 ký tự mỗi term; realtime cho tối đa 50 keyterm, 20 ký tự mỗi term. Guide minh họa model dùng context để tránh ép một keyterm vào mọi vị trí. [API reference](https://elevenlabs.io/docs/api-reference/speech-to-text/convert) giới hạn mỗi batch keyterm tối đa 5 từ và ghi keyterm surcharge 20%; trên 100 keyterm có minimum billable duration 20 giây.

Scribe v2 còn có `no_verbatim` và `transcript_edit`. Hai tính năng này **không được dùng cho transcript chấm điểm**:

- `no_verbatim=true` loại filler, false start và disfluency, làm mất bằng chứng Fluency and Coherence.
- `transcript_edit` nhận instruction ngôn ngữ tự nhiên và trả bản đã chỉnh bên cạnh bản gốc; nó phù hợp bản đọc dễ hiểu, không phù hợp làm đầu vào chấm grammar/lexicon.

Nếu dùng, chỉ lưu chúng thành `transcript_display` hoặc `suggested_correction`, tách khỏi `transcript_verbatim`.

### Timestamp, confidence, audio event và diarization

[Create transcript API](https://elevenlabs.io/docs/api-reference/speech-to-text/convert) trả word/character timestamp, speaker ID và cho phép diarization tới 32 speaker. [Get transcript API](https://elevenlabs.io/docs/api-reference/speech-to-text/get) cho thấy mỗi word có `start`, `end` và `logprob`. Log probability có thể dùng để tìm vùng ASR không chắc, nhưng tài liệu không định nghĩa nó là pronunciation quality hay IELTS evidence. API đã kiểm tra không công bố N-best/second-best hypotheses; correction vẫn cần decode/provider thứ hai hoặc xác nhận của người học.

Scribe có dynamic audio tags như laughter và non-speech sound. Tín hiệu này hữu ích cho audio-quality gate và giải thích khoảng ngắt, nhưng không tự quy đổi thành band.

### Batch, realtime và giới hạn

[STT overview](https://elevenlabs.io/docs/overview/capabilities/speech-to-text) công bố batch nhận audio/video tới 3 GB, tối đa 10 giờ ở standard mode, hỗ trợ webhook async và multi-channel. Realtime dùng WebSocket, có word timestamp và commit control. Với speaking practice sau mỗi câu, dùng batch để lấy transcript cuối ổn định; realtime chỉ phục vụ live caption, VAD và trải nghiệm examiner tương tác.

### Giá, free tier và quyền thương mại

[Trang giá API](https://elevenlabs.io/pricing/api) tại ngày kiểm tra công bố:

- Scribe v2 batch: **$0.22/giờ**.
- Scribe v2 Realtime: **$0.39/giờ**.
- Keyterm prompting batch: cộng **$0.05/giờ**; realtime: cộng **$0.08/giờ**.
- Transcript editing batch: cộng **$0.07/giờ**; realtime: cộng **$0.12/giờ**.

[Trang pricing chung](https://elevenlabs.io/pricing) công bố Free plan có 10.000 credit/tháng. Quota thực tế và cách quy đổi giữa UI/API thay đổi theo plan, nên benchmark phải đọc subscription dashboard và usage API thay vì suy ra số phút cố định.

Điểm cần xử lý trước khi bán sản phẩm: [ElevenLabs Terms of Service](https://elevenlabs.io/terms-of-use) nói Free User chỉ được dùng dịch vụ cho mục đích phi thương mại; Paid User mới có thể dùng thương mại theo điều khoản. [Billing docs](https://elevenlabs.io/docs/overview/administration/billing) cũng nói free output chỉ dùng phi thương mại với attribution. Vì vậy free API có thể dùng cho prototype/benchmark nội bộ, nhưng production trả phí cho người dùng cần một paid plan và kiểm tra lại contract tại thời điểm launch.

## Hai nhà cung cấp có chấm được bốn tiêu chí không?

| Tiêu chí | Deepgram | ElevenLabs | Kết luận dùng trong sản phẩm |
| --- | --- | --- | --- |
| Fluency & Coherence | Word timing, confidence, filler, utterance/VAD | Word timing, logprob, audio tags; phải để `no_verbatim=false` | Hữu ích làm bằng chứng pause/rate/disfluency. Không có band IELTS sẵn và coherence cần grader theo rubric. |
| Lexical Resource | Transcript + keyterm | Transcript + contextual keyterm | Có thể đưa transcript đã đánh dấu uncertain span vào grader. Không để keyterm làm tăng giả tạo lexical range. |
| Grammar Range & Accuracy | Verbatim transcript nếu giữ filler/lỗi | Verbatim transcript; tránh transcript editing/no-verbatim | Có thể hỗ trợ grader, nhưng lỗi ASR và punctuation tự sinh phải bị loại khỏi bằng chứng. |
| Pronunciation | Không có phoneme/stress/intonation score trong API STT đã kiểm tra | Không có pronunciation assessment trong API STT đã kiểm tra | Không dùng confidence/logprob làm điểm pronunciation. Cần model âm học chuyên biệt và calibration với examiner. |

[IELTS Speaking Band Descriptors](https://ielts.org/cdn/ielts-guides/ielts-speaking-band-descriptors.pdf) yêu cầu pronunciation xét phonological features, connected speech, rhythm, stress, intonation, intelligibility và ảnh hưởng của accent. [IELTS explanation](https://ielts.org/news-and-insights/demystifying-the-ielts-speaking-test) xác nhận bốn tiêu chí có trọng số bằng nhau. Vì vậy việc đổi ASR có thể nâng độ tin cậy của ba tiêu chí đầu và dữ liệu fluency, nhưng không tự hoàn thiện pronunciation scoring.

## Ma trận benchmark ra quyết định

Chạy cùng một tập audio và cùng split theo người nói cho ba baseline: Faster Whisper hiện tại, Deepgram Nova-3 monolingual batch, ElevenLabs Scribe v2 batch. Mỗi cloud provider chạy hai cấu hình: không keyterm và có keyterm. Không dùng transcript edit/no-verbatim. Khóa model ID, ngày chạy và toàn bộ option.

### Tập đánh giá tối thiểu

- 300–500 câu trả lời thật, gồm Part 1, Part 2 và Part 3; tối thiểu 30–50 người nói chưa xuất hiện trong prompt tuning.
- Phân tầng accent vùng Việt Nam, giới tính/độ tuổi nếu thu thập hợp pháp, band tham chiếu, thiết bị, phòng yên/ồn và tốc độ nói.
- Case bắt buộc: tên người/địa danh Việt, code-switch ngắn, numbers/dates, negation, homophone, linking, weak forms, âm cuối, false start, repetition, self-correction, filler, silence/noise và audio bị cắt.
- Hai annotator nghe và tạo transcript verbatim có timestamp; giải quyết bất đồng. Tách reference nguyên văn và reference chuẩn hóa.
- Một tập mock đầy đủ 11–14 phút được ít nhất hai giám khảo có chuyên môn chấm độc lập để đánh giá grader, tách khỏi tập đo ASR.

### Trọng số đề xuất

| Nhóm đo | Trọng số | Metric bắt buộc |
| --- | ---: | --- |
| Transcript fidelity | 25% | Verbatim WER, normalized WER, CER; báo cáo theo subgroup |
| Bảo toàn lỗi/ngôn ngữ người học | 15% | Recall filler, repetition, self-correction; tỷ lệ ASR tự sửa grammar; negation/number preservation |
| Proper noun và keyterm | 15% | Keyterm recall/precision; false insertion rate; KRR có/không prompt |
| Timing và fluency evidence | 10% | Word-boundary error, pause detection precision/recall, speaking-time error |
| Uncertainty quality | 10% | Precision/recall phát hiện word sai, AUPRC hoặc calibration error; không so threshold thô giữa provider |
| Accent và điều kiện thu âm | 10% | Worst-group WER, chênh lệch nhóm, noise/device degradation |
| Ảnh hưởng tới grader | 10% | MAE từng criterion, tỷ lệ trong ±0.5 band, unsupported-feedback rate khi thay duy nhất ASR |
| Vận hành | 5% | p50/p95 latency, timeout/retry rate, chi phí thực mỗi phút, concurrency |

### Hard gate trước khi chọn

Một provider không được chọn làm primary nếu vi phạm một trong các gate sau trên test set đã khóa:

1. Tự sửa lỗi grammar hoặc xóa disfluency nhiều hơn baseline đến mức thay đổi bằng chứng chấm.
2. False insertion của keyterm khiến tên riêng được “đoán” dù audio không nói.
3. Làm xấu đáng kể negation, number hoặc proper noun ở một subgroup quan trọng.
4. Timestamp không đủ chính xác để phát lại vùng cần nghe và đo pause.
5. Không giữ được raw response/model revision để audit.
6. Grader tạo feedback không được audio/transcript hỗ trợ hoặc pronunciation band khi thiếu bằng chứng âm học.

### Quy tắc chọn kiến trúc

- Chọn **một primary ASR** theo điểm tổng sau khi qua hard gate.
- Chỉ gọi **secondary ASR** khi word confidence/logprob thấp, proper noun quan trọng, hai decode bất đồng, audio quality xấu hoặc kết quả có tác động lớn tới band. Cách routing này kiểm soát chi phí tốt hơn chạy hai provider cho mọi câu.
- Với disagreement, lưu cả hai transcript và alignment; LLM chỉ được đề xuất “cần nghe lại”, không tự tuyên bố đáp án đúng nếu audio/keyterm không đủ bằng chứng.
- Learner confirmation thay đổi `intended_text` để coaching, không thay raw transcript và không được coi là audio-confirmed pronunciation.
- Đánh giá lại hàng tháng hoặc khi provider đổi model; dùng canary set cố định để phát hiện regression.

## Kiến trúc sản phẩm đề xuất

1. **Audio quality gate:** clipping, silence, SNR, duration, microphone/channel problems.
2. **Primary verbatim ASR:** raw word, timestamp, confidence/logprob, speaker, filler/audio event và model metadata.
3. **Selective second pass:** alternate provider hoặc alternate decode cho vùng rủi ro; keyterm lấy từ learner/topic metadata nhưng luôn gắn nguồn.
4. **Evidence ledger:** phân biệt `audio_confirmed`, `provider_agreement`, `provided_keyterm`, `context_only`, `learner_confirmed` và `unresolved`.
5. **Fluency feature layer:** pause, articulation/speech rate, repetition, repair và run length; hiệu chuẩn trên audio thật, không quy đổi WPM bằng threshold cố định.
6. **Pronunciation layer riêng:** phoneme/word/prosody/intelligibility evidence. Nếu chưa có, trả `insufficient_evidence` cho phần không quan sát được thay vì bịa điểm.
7. **Rubric grader:** đọc transcript verbatim, uncertain spans, acoustic evidence và IELTS descriptors; mọi nhận xét có quote/timestamp.
8. **Calibration và audit:** so với examiner, theo dõi sai số từng criterion/subgroup, lưu prompt/model/rubric version và cho phép nghe lại.

Deepgram có lợi thế rõ ở confidence được tài liệu hóa, filler/utterance feature, dynamic keyterm và chi phí batch cạnh tranh. ElevenLabs có lợi thế ở Scribe v2 contextual keyterms quy mô lớn, multilingual coverage, logprob, audio tags và API batch rất rẻ; tuy nhiên free plan không phù hợp production thương mại. Không thể tuyên bố bên nào chính xác hơn cho người Việt nói tiếng Anh trước khi chạy benchmark nói trên.
