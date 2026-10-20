from app.modules.speaking.pronunciation.acoustic import (
    avg_logprob_to_confidence,
    color_word,
    compute_fluency_acoustic,
    detect_noise,
)


def test_confidence():
    assert avg_logprob_to_confidence(None) == 0.0
    assert avg_logprob_to_confidence(0.0) == 1.0
    c = avg_logprob_to_confidence(-0.1)
    assert 0.0 <= c <= 1.0


def test_color_word():
    assert color_word(0.9) == "green"
    assert color_word(0.7) == "yellow"
    assert color_word(0.5) == "red"


def test_detect_noise():
    assert detect_noise([{"no_speech_prob": 0.9}], "hello") == "cant_hear"
    assert detect_noise([{"no_speech_prob": 0.1}], "hello world") is None
    assert detect_noise([{"no_speech_prob": 0.1}], "") == "cant_hear"


def test_fluency_acoustic_positive():
    words = [
        {"start": 0.0, "end": 0.3},
        {"start": 0.35, "end": 0.6},
        {"start": 0.65, "end": 0.9},
    ]
    assert compute_fluency_acoustic(words, 1.0) > 0


def test_fluency_acoustic_empty():
    assert compute_fluency_acoustic([], 0.0) == 0.0
    assert compute_fluency_acoustic(None, 10.0) == 0.0
