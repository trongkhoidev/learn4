from app.modules.speaking.assessment.scoring import _normalize, _number_words_to_digits


def test_number_words_simple():
    assert _number_words_to_digits("twenty one") == "21"
    assert _number_words_to_digits("two hundred") == "200"


def test_number_words_keeps_other_words():
    assert _number_words_to_digits("i have two cats") == "i have 2 cats"


def test_normalize_expands_contractions_and_stems():
    n = _normalize("I'm running to the store")
    assert "i am" in n
    assert "run" in n
    assert "running" not in n


def test_normalize_removes_fillers():
    n = _normalize("I am like uh going")
    assert "like" not in n
    assert "uh" not in n
    assert "go" in n


def test_normalize_dedup_repeats():
    n = _normalize("the the book")
    assert n == "the book"
