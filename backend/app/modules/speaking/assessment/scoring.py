"""Deterministic Speaking scoring — ported 1:1 from luyennoi.com `test-score.js`.

Notes on exactness:
- JS `Math.round` is half-up; Python `round` is banker's. Use `js_round` everywhere.
- `pronun.score` and `fluency.score` fed into `user_audio_2_score` are BANDS (0-9),
  already converted server-side via `pronun_conf_to_band` / `fluency_score_to_band`.
- The band regex allows spaces before the colon (e.g. `Band : X.X`), to accommodate
  models like Gemini that occasionally add spaces.
- `_normalize` (the original `F`) applies number-word expansion then Porter stemming.
"""

import math
import re

PART2_TYPES = {"PART 2", "PART 2 cue card", "PART 2 FOLLOW UP", "TEST PART 2", "MOCK_PART2"}
WORD_MIN_PART2 = 100
WORD_MIN_OTHER = 20

BAND_RE = re.compile(r"Band\s*:\s*(\d+(\.\d+)?)")
RELATION_RE = re.compile(r"relation\s*:\s*(related|weakly[\s-]*related|unrelated)\b", re.IGNORECASE)
REASON_RE = re.compile(r"reason\s*:\s*([\s\S]*?)(?:\r?\n\s*(?:evidence|relation)\s*:|$)", re.IGNORECASE)

FILLERS = [
    "uh", "uhm", "um", "erm", "er", "eh", "ah", "oh", "hmm", "mm", "well",
    "you know", "like", "sort of", "sorta", "kinda", "kind of", "gonna",
    "going to", "wanna", "want to", "and", "actually", "basically", "literally", "just",
]

CONTRACTIONS = {
    "i'm": "i am", "i'll": "i will", "i've": "i have", "i'd": "i would",
    "you're": "you are", "you'll": "you will", "you've": "you have", "you'd": "you would",
    "he's": "he is", "he'll": "he will", "he'd": "he would",
    "she's": "she is", "she'll": "she will", "she'd": "she would",
    "it's": "it is", "it'll": "it will",
    "we're": "we are", "we'll": "we will", "we've": "we have", "we'd": "we would",
    "they're": "they are", "they'll": "they will", "they've": "they have", "they'd": "they would",
    "that's": "that is", "there's": "there is", "what's": "what is",
    "who's": "who is", "where's": "where is", "let's": "let us",
    "isn't": "is not", "aren't": "are not", "wasn't": "was not", "weren't": "were not",
    "don't": "do not", "doesn't": "does not", "didn't": "did not",
    "haven't": "have not", "hasn't": "has not", "hadn't": "had not",
    "won't": "will not", "wouldn't": "would not", "can't": "can not", "cannot": "can not",
    "couldn't": "could not", "shouldn't": "should not", "mustn't": "must not",
}


def js_round(x):
    return math.floor(x + 0.5)


def _clamp_band(value):
    """Clamp to the public IELTS scale and round to the nearest half band."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0.0
    value = max(0.0, min(9.0, value))
    return math.floor(value * 2 + 0.5) / 2.0


def parse_band(text):
    m = BAND_RE.search(text or "")
    return float(m.group(1)) if m else 0.0


def parse_off_topic(chat):
    if not chat:
        return {"isOffTopic": None, "explanation": None}
    t = (chat or "").strip()
    m = RELATION_RE.search(t)
    is_off = bool(m) and m.group(1).lower().replace("-", " ").strip() == "unrelated"
    m2 = REASON_RE.search(t)
    expl = m2.group(1).strip() if m2 else None
    if not is_off:
        expl = None
    return {"isOffTopic": is_off, "explanation": expl}


def merge_fluency(acoustic, llm):
    if llm <= 5:
        return llm
    n = (acoustic + llm) / 2
    r = js_round(n)
    if n < 7.5:
        r = min(r, 7)
    return r if (llm >= 7 and acoustic >= 8) else min(r, llm)


def is_too_short(task_type, transcript):
    wc = len((transcript or "").split())
    if task_type in PART2_TYPES:
        return wc <= WORD_MIN_PART2
    return wc <= WORD_MIN_OTHER


def pronun_conf_to_band(conf):
    if not conf:
        return 0
    low, high = 0.483, 0.85
    band = 3 + (conf - low) / (high - low) * 6
    band = max(band, 1)
    if band > 9:
        band = 0
    return js_round(band * 2) / 2


def fluency_score_to_band(s):
    if not s:
        return 0
    hi, lo = 1.02, 5.93
    band = 4 + (s - lo) / (hi - lo) * 5
    band = min(max(band, 1), 9)
    return js_round(band * 2) / 2


def user_audio_2_score(score, transcript, task_type, noise):
    fluency = (score or {}).get("fluency") or {}
    if not score or parse_off_topic(fluency.get("chat", ""))["isOffTopic"]:
        return {"overall": 0.0, "pronun": 0.0, "fluency": 0.0, "grammar": 0.0,
                "vocab": 0.0, "isPronunHiddenByNoise": False}

    grammar = parse_band(score.get("grammar", ""))
    vocab = parse_band(score.get("vocab", ""))
    fluency_l = parse_band(fluency.get("chat", ""))
    fluency_a = fluency.get("score") or 0

    if fluency_l == 0 and fluency_a != 0:
        fluency = js_round(fluency_a * 2) / 2
    elif fluency_l != 0 and fluency_a == 0:
        fluency = fluency_l
    else:
        fluency = merge_fluency(fluency_a, fluency_l)

    pronun = (score.get("pronun") or {}).get("score") or 0

    if fluency < 6 or grammar < 6 or vocab < 6:
        pronun = min(pronun, 7)

    if is_too_short(task_type, transcript):
        pronun, fluency, grammar, vocab = (max(x - 1, 0) for x in (pronun, fluency, grammar, vocab))

    hidden = False
    if noise == "cant_hear":
        pronun, hidden = 0.0, True

    pos = [b for b in (grammar, vocab, pronun, fluency) if b > 0]
    overall = math.floor(sum(pos) / len(pos) * 2) / 2 if pos else 0.0

    return {"overall": overall, "pronun": pronun, "fluency": fluency,
            "grammar": grammar, "vocab": vocab, "isPronunHiddenByNoise": hidden}


def _norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower()).strip()


def parse_grammar_errors(text):
    errs = []
    for line in (text or "").split("\n"):
        line = line.strip()
        if not line or "->" not in line:
            continue
        left, right = line.split("->", 1)
        err = re.sub(r"^-", "", left).replace('"', "").strip()
        parts = right.split(":")
        correct = re.sub(r'[()"]', "", parts[0]).strip()
        explain = re.sub(r'[()"]', "", parts[1]).strip() if len(parts) > 1 else ""
        if _norm(err) != _norm(correct):
            errs.append({"error": err, "correct": correct, "explain": explain})
    return errs


def _expand_contractions(text):
    t = (text or "").lower().replace("‘", "'").replace("’", "'").replace("`", "'")
    for k, v in CONTRACTIONS.items():
        t = re.sub(r"\b" + re.escape(k) + r"\b", v, t)
    return t


NUMBER_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
NUMBER_SCALES = {"hundred": 100, "thousand": 1000, "million": 1000000}

_stemmer = None


def _get_stemmer():
    global _stemmer
    if _stemmer is None:
        from nltk.stem import PorterStemmer

        _stemmer = PorterStemmer()
    return _stemmer


def _number_group_with_scale(tokens):
    total = 0
    current = 0
    for tok in tokens:
        if tok == "hundred":
            current = (current or 1) * 100
        elif tok in NUMBER_SCALES:
            total += (current or 1) * NUMBER_SCALES[tok]
            current = 0
        else:
            current += NUMBER_UNITS[tok]
    return total + current


def _number_group_units(values):
    out = []
    i = 0
    while i < len(values):
        v = values[i]
        nxt = values[i + 1] if i + 1 < len(values) else None
        if v >= 20 and v % 10 == 0 and nxt is not None and nxt < 10:
            v = v + nxt
            i += 2
        else:
            i += 1
        out.append(v)
    if len(out) == 1:
        return str(out[0])
    return "".join(str(v) if j == 0 else str(v).zfill(2) for j, v in enumerate(out))


def _number_words_to_digits(text):
    tokens = text.split()
    result = []
    group = []

    def flush():
        if group:
            if any(t in NUMBER_SCALES for t in group):
                result.append(str(_number_group_with_scale(group)))
            else:
                result.append(_number_group_units([NUMBER_UNITS[t] for t in group]))
            group.clear()

    for tok in tokens:
        t = tok.lower()
        if t in NUMBER_UNITS or t in NUMBER_SCALES:
            group.append(t)
        else:
            if t == "and" and group:
                continue
            flush()
            if tok:
                result.append(tok)
    flush()
    return " ".join(result)


def _stem(text):
    stemmer = _get_stemmer()
    return " ".join(stemmer.stem(tok) if not tok.isdigit() else tok for tok in text.split())


def _normalize(text):
    t = _expand_contractions(text)
    t = re.sub(r"[^\w\s]", " ", t)
    t = _number_words_to_digits(t)
    t = _stem(t)
    for f in FILLERS:
        t = re.sub(r"\b" + re.escape(f) + r"\b", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(\w+)(\s+\1\b)+", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def _clean_chars(s):
    return re.sub(r"[^a-zA-Z\s'-]", "", s or "")


def clean_grammar_errors(text, answer):
    errs = parse_grammar_errors(text)
    errs = [e for e in errs if _normalize(e["error"]) != _normalize(e["correct"])]
    errs = [
        e for e in errs
        if e["error"].lower() not in ("none",)
        and "dấu phẩy" not in e["explain"]
        and "dấu chấm" not in e["explain"]
        and "lặp từ" not in e["explain"]
        and "lặp lại" not in e["explain"]
        and "không tự nhiên" not in e["explain"]
    ]
    cleaned_answer = _clean_chars(answer)
    return [e for e in errs if _clean_chars(e["error"]) in cleaned_answer]


def median(xs):
    if not xs:
        return 0
    s = sorted(xs)
    n = len(s)
    return (s[n // 2 - 1] + s[n // 2]) / 2 if n % 2 == 0 else s[n // 2]


def agg(xs, t=7.25):
    if not xs:
        return 0
    m = sum(xs) / len(xs)
    return math.ceil(m) if m >= t else js_round(m)


def agg_pronun(xs):
    if not xs:
        return 0
    m = sum(xs) / len(xs)
    return math.ceil(m) if m >= 8.25 else js_round(m)


def overall_of(xs):
    """Equal-weight criterion mean, rounded to the nearest half band.

    Missing evidence must be handled by the assessment status before calling
    this function. A zero is therefore a real value, not a criterion to drop.
    """
    if not xs:
        return 0
    values = [_clamp_band(x) for x in xs]
    return _clamp_band(sum(values) / len(values))
