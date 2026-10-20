from app.modules.speaking.assessment.scoring import (
    agg,
    agg_pronun,
    clean_grammar_errors,
    fluency_score_to_band,
    median,
    merge_fluency,
    overall_of,
    parse_band,
    parse_grammar_errors,
    parse_off_topic,
    pronun_conf_to_band,
    user_audio_2_score,
)


def _score(pronun=7.0, fluency_score=0.0, fluency_chat="Band: 7.0", grammar="Band: 7.0", vocab="Band: 7.0"):
    return {
        "pronun": {"score": pronun},
        "fluency": {"score": fluency_score, "chat": fluency_chat},
        "grammar": grammar,
        "vocab": vocab,
    }


def test_parse_band():
    assert parse_band("Band: 6.5") == 6.5
    assert parse_band("no band here") == 0.0
    assert parse_band("Band : 6.5") == 6.5  # regex allows space before colon


def test_parse_off_topic():
    assert parse_off_topic("relation : unrelated\nreason : nói lệch\nBand: 7.0")["isOffTopic"] is True
    assert parse_off_topic("relation : related\nBand: 6.5")["isOffTopic"] is False
    assert parse_off_topic("")["isOffTopic"] is None


def test_merge_fluency_llm_le_5():
    assert merge_fluency(8.0, 4.5) == 4.5


def test_merge_fluency_exception_llm7_acoustic8():
    assert merge_fluency(8.5, 7.0) == 8.0
    assert merge_fluency(9.0, 8.0) == 9.0


def test_merge_fluency_cap_at_llm():
    assert merge_fluency(9.0, 6.5) == 6.5


def test_merge_fluency_round_half_up_and_cap():
    assert merge_fluency(7.0, 6.0) == 6.0


def test_pronun_conf_to_band():
    assert pronun_conf_to_band(0.483) == 3.0
    assert pronun_conf_to_band(0.85) == 9.0
    assert pronun_conf_to_band(0.9) == 0.0  # >9 -> invalid -> 0
    assert pronun_conf_to_band(0) == 0.0


def test_fluency_score_to_band():
    assert fluency_score_to_band(1.02) == 9.0
    assert fluency_score_to_band(5.93) == 4.0
    assert fluency_score_to_band(0) == 0.0


def test_off_topic_zeroes_everything():
    score = _score(pronun=8.0, fluency_chat="relation : unrelated\nreason : x\nBand: 7.0")
    r = user_audio_2_score(score, "hello world", "PART 1", None)
    assert r["overall"] == 0.0 and r["pronun"] == 0.0 and r["grammar"] == 0.0


def test_cap_pronun_when_any_band_below_6():
    score = _score(pronun=8.5, fluency_chat="Band: 5.5", grammar="Band: 7.0", vocab="Band: 7.0")
    r = user_audio_2_score(score, "word " * 30, "PART 1", None)
    assert r["pronun"] == 7.0
    assert r["fluency"] == 5.5
    assert r["overall"] == 6.5


def test_too_short_penalty_part1():
    score = _score()
    r = user_audio_2_score(score, "hello", "PART 1", None)
    assert r["pronun"] == 6.0 and r["fluency"] == 6.0 and r["grammar"] == 6.0 and r["vocab"] == 6.0
    assert r["overall"] == 6.0


def test_noise_zeroes_pronun():
    score = _score()
    r = user_audio_2_score(score, "word " * 30, "PART 1", "cant_hear")
    assert r["pronun"] == 0.0 and r["isPronunHiddenByNoise"] is True
    assert r["overall"] == 7.0


def test_acoustic_only_fluency_rounds_half_up():
    score = _score(fluency_score=6.25, fluency_chat="")
    r = user_audio_2_score(score, "word " * 30, "PART 1", None)
    assert r["fluency"] == 6.5


def test_parse_grammar_errors():
    assert parse_grammar_errors('- "go" -> "went" : quá khứ') == [
        {"error": "go", "correct": "went", "explain": "quá khứ"}
    ]
    assert parse_grammar_errors('- "go" -> ("go") : không có lỗi') == []


def test_clean_grammar_errors_filters():
    text = '- "go" -> "went" : quá khứ\n- "a" -> "an" : dấu phẩy thừa'
    errs = clean_grammar_errors(text, "i go to school")
    assert errs == [{"error": "go", "correct": "went", "explain": "quá khứ"}]


def test_aggregation():
    assert median([6, 6, 6.5, 7]) == 6.25
    assert median([5, 6, 7]) == 6
    assert agg([6, 7, 8]) == 7
    assert agg([7, 8, 8]) == 8
    assert agg_pronun([8, 9]) == 9
    assert agg_pronun([7, 8]) == 8
    assert overall_of([6, 7, 8, 0]) == 5.5
