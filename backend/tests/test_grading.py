from app.modules.submissions.grading import grade_answers, normalize_answer


def test_normalize_answer():
    assert normalize_answer("  TRUE. ") == "true"
    assert normalize_answer("Modern") == "modern"
    assert normalize_answer(None) == ""
    assert normalize_answer("A  B") == "a b"


def test_grade_answers_exact():
    grade = grade_answers(["A", "TRUE", "modern"], ["A", "TRUE", "modern"])
    assert grade["score"] == 3
    assert grade["total"] == 3


def test_grade_answers_case_punctuation():
    grade = grade_answers(["a", "true", "Modern"], ["A", "TRUE", "modern"])
    assert grade["score"] == 3


def test_grade_answers_partial():
    grade = grade_answers(["A", "B", "C"], ["A", "D", "C"])
    assert grade["score"] == 2
    assert [r["correct"] for r in grade["results"]] == [True, False, True]


def test_grade_answers_no_key():
    grade = grade_answers(["A"], None)
    assert grade["total"] == 0
    assert grade["score"] == 0
