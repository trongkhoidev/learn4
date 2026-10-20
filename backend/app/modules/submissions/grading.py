import re


def normalize_answer(value: str | None) -> str:
    if value is None:
        return ""
    s = value.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def grade_answers(answers: list[str] | None, answer_key: list[str] | None) -> dict:
    key = answer_key or []
    student_answers = answers or []
    results = []
    correct_count = 0
    for i, expected in enumerate(key):
        given = student_answers[i] if i < len(student_answers) else ""
        exp_norm = normalize_answer(expected)
        ok = exp_norm != "" and normalize_answer(given) == exp_norm
        if ok:
            correct_count += 1
        results.append({"index": i + 1, "given": given, "expected": expected, "correct": ok})
    return {"score": correct_count, "total": len(key), "results": results}
