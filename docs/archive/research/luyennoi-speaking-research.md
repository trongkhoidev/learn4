# Nghiên cứu luyennoi.com — Speaking (thuật toán chấm điểm chính xác)

> Mục tiêu: tái tạo Speaking của LexiLearn **tương đương luyennoi.com**.
> Nguồn: phân tích bundle thật của luyennoi.com (SvelteKit, `_app/immutable/chunks/`).
> File gốc đã decode: `test-score.a908273a.js`, `stores.b8de58bc.js`, `result.f24450cf.js`, `utils-client.7c9cc638.js`.

---

## 1. Kiến trúc luyennoi.com (quan sát thực tế)

| Tầng | Quan sát |
|---|---|
| Frontend | SvelteKit (SSR), deploy **Netlify**; media trên **CloudFront** (`difz6g2sivtgc.cloudfront.net`) |
| Auth | **AWS Cognito** (`cognito-idp.ap-southeast-1.amazonaws.com`) + Google Sign-In |
| Backend | **AWS AppSync GraphQL** (`...appsync-api.ap-southeast-1.amazonaws.com/graphql`) |
| Data | DynamoDB (kết quả có `pk`/`sk`, pagination) + S3 (cache `CACHED-ALL-DAILY-USER-RESULTS-V2`) |
| STT + acoustic | **Tính ở server** → client chỉ nhận `userAudio{transcript, noise}` và `score{...}` |
| LLM | 3 call song song (fluency/grammar/vocab); theo spec đã giải mã là **Groq Whisper + Llama-3.3-70b** |

**Hàm chấm chính** ở client: `userAudio2ScoreV3` (export `g` trong `test-score.js`). Đây là hàm tổng hợp deterministic — mọi logic điểm số nằm ở đây, còn feature acoustic (`pronun.score`, `fluency.score`) do server trả về.

---

## 2. Cấu trúc dữ liệu `score` (đầu vào hàm chấm)

> ⚠️ `pronun.score` và `fluency.score` là **BAND (0-9)**, không phải raw. Server luyennoi đã
> áp `he()` (confidence→band) và `de()` (raw disfluency→band) **trước khi lưu** — bằng chứng là
> `g()` dùng `pronun.score` trực tiếp làm band (chỉ cap 7) và nhánh `acoustic>=8` trong `D()`.

```jsonc
{
  "pronun":  { "score": 6.5 },                 // BAND (0-9) = he(confidence) — server đã chuyển
  "fluency": { "score": 7.0, "chat": "relation : related\n…\nBand: 7.0" },  // score = BAND = de(raw), chat = text LLM
  "grammar": "… Band: 6.0",                    // text LLM
  "vocab":   "… Band: 6.5"                     // text LLM
}
userAudio = { "transcript": "...", "noise": null | "cant_hear" }
```

---

## 3. Thuật toán chấm CHÍNH XÁC (dịch sang Python)

> **2 lỗi port hay mắc (đã xử lý trong code):**
> 1. **JS `Math.round` ≠ Python `round`** — JS làm tròn half-up (6.5→7), Python banker's (6.5→6).
>    Phải dùng `js_round(x) = floor(x + 0.5)` ở mọi chỗ gốc gọi `Math.round`.
> 2. **Regex band gốc `Band:\s*` KHÔNG chấp nhận `Band :` (có space)** → prompt phải in `Band: X.X`.

### 3.1 Parse band từ text LLM

```python
import re

def parse_band(text: str) -> float:          # hàm A() / fe()
    m = re.search(r'Band:\s*(\d+(\.\d+)?)', text or "")
    return float(m.group(1)) if m else 0.0
```

### 3.2 Phát hiện lạc đề (`ce()`)

```python
def parse_off_topic(chat: str):
    if not chat:
        return {"isOffTopic": None, "explanation": None}
    t = chat.strip()
    m = re.search(r'relation\s*:\s*(related|weakly[\s-]*related|unrelated)\b', t, re.I)
    is_off = bool(m) and m.group(1).lower().replace('-', ' ').strip() == "unrelated"
    m2 = re.search(r'reason\s*:\s*([\s\S]*?)(?:\r?\n\s*(?:evidence|relation)\s*:|$)', t, re.I)
    expl = m2.group(1).strip() if m2 else None
    if not is_off:
        expl = None
    return {"isOffTopic": is_off, "explanation": expl}
```

### 3.3 Merge Fluency (`D()`)

> ⚠️ **Khác tóm tắt trong spec** — round về **số nguyên** và có 1 ngoại lệ.

```python
def merge_fluency(acoustic: float, llm: float) -> float:   # D(acoustic, llm)
    if llm <= 5:
        return llm
    n = (acoustic + llm) / 2
    r = js_round(n)                   # round half-up về SỐ NGUYÊN (không phải 0.5)
    if n < 7.5:
        r = min(r, 7)
    # ngoại lệ: llm>=7 và acoustic>=8 → giữ r; còn lại cap tại llm
    return r if (llm >= 7 and acoustic >= 8) else min(r, llm)
```

### 3.4 Chấm tổng (`g()` = `userAudio2ScoreV3`)

```python
def user_audio_2_score(score, transcript: str, task_type: str, noise):
    if not score or parse_off_topic((score.get("fluency") or {}).get("chat", ""))["isOffTopic"]:
        return {"overall": 0, "pronun": 0, "fluency": 0, "grammar": 0, "vocab": 0}

    grammar   = parse_band(score.get("grammar", ""))
    vocab     = parse_band(score.get("vocab", ""))
    fluency_l = parse_band((score.get("fluency") or {}).get("chat", ""))   # band từ LLM
    fluency_a = (score.get("fluency") or {}).get("score") or 0             # acoustic (server)

    if fluency_l == 0 and fluency_a != 0:
        fluency = js_round(fluency_a * 2) / 2       # chỉ có acoustic
    elif fluency_l != 0 and fluency_a == 0:
        fluency = fluency_l                         # chỉ có LLM
    else:
        fluency = merge_fluency(fluency_a, fluency_l)

    pronun = (score.get("pronun") or {}).get("score") or 0

    # (1) cap pronun: bất kỳ band nào trong {fluency, grammar, vocab} < 6 → pronun ≤ 7
    if fluency < 6 or grammar < 6 or vocab < 6:
        pronun = min(pronun, 7)

    # (2) trả lời quá ngắn → −1 mỗi band (floor 0)
    if is_too_short(task_type, transcript):
        pronun, fluency, grammar, vocab = (max(x - 1, 0) for x in (pronun, fluency, grammar, vocab))

    # (3) noise
    hidden = False
    if noise == "cant_hear":
        pronun, hidden = 0, True

    # (4) overall = floor(mean(band>0) * 2) / 2
    pos = [b for b in (grammar, vocab, pronun, fluency) if b > 0]
    overall = (sum(pos) / len(pos) * 2 // 1) / 2 if pos else 0   # floor(mean*2)/2

    return {"overall": overall, "pronun": pronun, "fluency": fluency,
            "grammar": grammar, "vocab": vocab, "isPronunHiddenByNoise": hidden}
```

> **Thứ tự penalty quan trọng**: (1) cap pronun → (2) −1 too-short → (3) noise zero pronun. Không được đảo.

### 3.5 Kiểm tra "quá ngắn" (`_()` = `i`)

```python
PART2_TYPES = {"PART 2", "PART 2 cue card", "PART 2 FOLLOW UP", "TEST PART 2"}
WORD_MIN_PART2 = 100    # U = 100
WORD_MIN_OTHER = 20     # H = 20

def is_too_short(task_type: str, transcript: str) -> bool:
    wc = len((transcript or "").split())
    if task_type in PART2_TYPES:
        return wc <= WORD_MIN_PART2
    return wc <= WORD_MIN_OTHER
```

### 3.6 Band pronunciation (`he()`) — chuyển confidence → band (server-side)

```python
def pronun_conf_to_band(conf: float) -> float:
    if not conf:
        return 0
    low, high = 0.483, 0.85
    band = 3 + (conf - low) / (high - low) * 6     # base 3, range 6 → 3..9
    band = max(band, 1)
    if band > 9:
        band = 0                                   # ngoài range → 0 (không hợp lệ)
    return js_round(band * 2) / 2
```

### 3.7 Band fluency acoustic (`de()`) — chuyển raw disfluency → band (server-side)

```python
def fluency_score_to_band(s: float) -> float:
    if not s:
        return 0
    # ĐẢO: giá trị thấp hơn = tốt hơn. s≈5.93 → band 4 ; s≈1.02 → band 9
    hi, lo = 1.02, 5.93
    band = 4 + (s - lo) / (hi - lo) * 5            # base 4, range 5 → 4..9
    band = min(max(band, 1), 9)
    return js_round(band * 2) / 2
```

---

## 4. Pipeline lỗi ngữ pháp CHÍNH XÁC (4 tầng + chuẩn hóa)

### 4.1 Parse dòng lỗi (`Z()` = `w`)

```python
def _norm(s): return re.sub(r'[^a-z]', '', s.lower()).strip()

def parse_grammar_errors(text: str):
    errs = []
    for line in (text or "").split('\n'):
        line = line.strip()
        if not line or '->' not in line:
            continue
        left, right = line.split('->', 1)
        err = left.lstrip('-').replace('"', '').strip()
        parts = right.split(':')
        correct = parts[0].strip('()"').strip()
        explain = parts[1].strip('()"').strip() if len(parts) > 1 else ''
        if _norm(err) != _norm(correct):           # bỏ cặp tự sửa thành chính nó
            errs.append({"error": err, "correct": correct, "explain": explain})
    return errs
```

### 4.2 Lọc 4 tầng (`Fe()` = `p`)

```python
def clean_grammar_errors(text: str, answer: str):
    errs = parse_grammar_errors(text)
    # tầng 1 (se): bỏ lỗi mà sau chuẩn hóa == đáp án
    errs = [e for e in errs if normalize(e["error"]) != normalize(e["correct"])]
    # tầng 2 (ie): bỏ lỗi vặt (None, dấu phẩy/dấu chấm, lặp từ, "không tự nhiên")
    errs = [e for e in errs
            if e["error"].lower() not in ("none",)
            and "dấu phẩy" not in e["explain"] and "dấu chấm" not in e["explain"]
            and "lặp từ" not in e["explain"] and "lặp lại" not in e["explain"]
            and "không tự nhiên" not in e["explain"]]
    # tầng 3 (ae): chỉ giữ lỗi thực sự xuất hiện trong bài (so khớp cleaned text)
    cleaned_answer = re.sub(r"[^a-zA-Z\s'-]", '', answer)
    return [e for e in errs if re.sub(r"[^a-zA-Z\s'-]", '', e["error"]) in cleaned_answer]
```

### 4.3 Chuẩn hóa văn bản (`F()`)

```python
FILLERS = ["uh","uhm","um","erm","er","eh","ah","oh","hmm","mm","well","you know",
           "like","sort of","sorta","kinda","kind of","gonna","going to","wanna",
           "want to","and","actually","basically","literally","just"]

def normalize(text: str) -> str:
    t = expand_contractions(text)      # i'm→i am, don't→do not, can't→can not … (bảng J ~40 cặp)
    t = re.sub(r'[^\w\s]', ' ', t)     # bỏ dấu câu
    t = stem(t)                        # stemming (hàm G từ result.js)
    t = number_words_to_digits(t)      # "twenty one"→"21", "a hundred"→"100" …
    for f in FILLERS:
        t = re.sub(r'\b' + f + r'\b', ' ', t, flags=re.I)
    t = re.sub(r'\b(\w+)(\s+\1\b)+', r'\1', t)   # gộp từ lặp liên tiếp
    return re.sub(r'\s+', ' ', t).strip()
```

> Mục đích: dùng để **so khớp** và **dedup** lỗi — không hiển thị cho học viên.
> Đã implement trong `scoring_service.py`: `_expand_contractions` + `_number_words_to_digits` (port bộ `P`/`T`/`te`/`ne`/`re`/`oe`) + `_stem` (PorterStemmer) + filler + dedup.

---

## 5. Tổng hợp điểm nhiều câu (mock test / bảng band)

```python
def median(xs):                        # d()
    if not xs: return 0
    xs = sorted(xs)
    n = len(xs)
    return (xs[n//2 - 1] + xs[n//2]) / 2 if n % 2 == 0 else xs[n//2]

def agg(xs, t=7.25):                   # R(): mean >= t → ceil, ngược lại round
    if not xs: return 0
    m = sum(xs) / len(xs)
    return math.ceil(m) if m >= t else js_round(m)

def agg_pronun(xs):                    # Re(): ngưỡng 8.25
    if not xs: return 0
    m = sum(xs) / len(xs)
    return math.ceil(m) if m >= 8.25 else js_round(m)

def overall_of(xs):                    # Pe(): floor(mean(>0)*2)/2
    pos = [x for x in xs if x > 0]
    return math.floor(sum(pos) / len(pos) * 2) / 2 if pos else 0
```

**Ý nghĩa theo ngữ cảnh (từ code):**
- `k()` / `getUserMedianBandScore`: median các band (practice + test) để hiển thị bảng tiến bộ.
- `O()`: tổng hợp 1 phần (Part 1/2/3) từ danh sách kết quả → vocab/grammar/fluency qua `agg`, pronun qua `agg_pronun`, overall qua `overall_of`.
- `Se()` / `getEstimatedBandForDisplay`: nếu có `FULL TEST` thì median các full test; ngược lại nếu số ngày luyện ≥ 25 (`W`) thì median practice; không đủ → `insufficient`.

---

## 6. Feature map — clone vs bỏ

| Tính năng luyennoi | Clone? | Ghi chú |
|---|---|---|
| Chấm 4 tiêu chí + overall | ✅ | Thuật toán mục 3 |
| Phát hiện lạc đề (relation) | ✅ | Mục 3.2 |
| Lỗi ngữ pháp (sửa + giải thích) | ✅ | Mục 4 |
| Mock test (FULL TEST / PART 1/2/3) | ✅ | Mục 5 |
| Color-coded transcript | ✅ | từ `words[].probability` (ngưỡng suy từ spec 3.4) |
| `AUDIO2PHONEMES` / `WORD_PRONUN` / `PRONUN-PRACTICE` | ❌ | Phoneme-level, ngoài phạm vi |
| `REPEAT SENTENCE`, `S/ES`, `ED`, `PRESENT PERFECT/CONTINUOUS`, `FUTURE`, `Review Vocab`, `Phrase Practice` | ❌ | Micro-practice ngoài 4 kỹ năng |
| `CONVERSATION` (chat nói chuyện) | ❌ | Không nằm trong spec |
| TTS giọng đọc (Kokoro `af_heart`…) | ❌ | Cần thì thêm sau |
| Login/Google, billing, streak | ❌ | Spec yêu cầu không login/billing |

---

## 7. Khoảng trống cần calibration (nằm ở server luyennoi — chỉ suy luận)

| Feature | Đã biết chính xác | Cần calibration khi cài LexiLearn |
|---|---|---|
| `pronun.score` (band) | `he()` = 3 + (conf−0.483)/(0.85−0.483)×6 | cách normalize `avg_logprob → confidence` (exp có thể lệch vì whisper overconfident) |
| `fluency.score` (band) | `de()` = 4 + (raw−5.93)/(1.02−5.93)×5 | công thức raw disfluency từ word timestamps (speech rate + pause) |
| `noise` | xử lý `cant_hear` → pronun 0 | ngưỡng `no_speech_prob` / độ dài tối thiểu |
| color-coded transcript | — | ngưỡng probability: xanh ≥0.8 / vàng ≥0.6 / đỏ <0.6 (spec 3.4) |

**Kế hoạch calibration (giai đoạn 5):**
1. Chạy 10–20 mẫu audio thật qua `faster-whisper turbo` → thu `avg_logprob`, `words[].probability`, timestamps.
2. Vẽ phân phối để chọn `low/high` pronun (khởi tạo 0.483/0.85) và công thức `fluency.score` (khởi tạo theo đảo của speech rate + pause).
3. So sánh band xuất với band luyennoi trên cùng mẫu → hiệu chỉnh hằng số trong `.env`.

---

## 8. Ghi chú triển khai LexiLearn

- `scoring_service.py` port nguyên các hàm mục 3–5, giữ **đúng thứ tự penalty** và **rounding** (round số nguyên ở merge fluency).
- Unit test dùng các ca test khớp code gốc (mục 10 trong `PLAN_IMPLEMENTATION.md`).
- Acoustic feature (`pronun.conf`, `fluency.score`, `noise`) tính trong `stt_service` từ verbose_json của `faster-whisper` (giá trị `avg_logprob`, `probability`, timestamps, `no_speech_prob`).
- Hàm `merge_fluency` khác spec tóm tắt (round integer + ngoại lệ `llm>=7 && acoustic>=8`) — đây là bản **đúng**.
