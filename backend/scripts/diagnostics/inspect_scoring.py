"""Print representative scoring parser outputs without starting the app."""

from app.modules.speaking.assessment.scoring import (
    clean_grammar_errors,
    parse_band,
    parse_grammar_errors,
    parse_off_topic,
)


def main():
    print("Band:", parse_band('{"band": 7.5, "comment_vn": "Khá tốt"}'))
    print("OffTopic:", parse_off_topic('{"band": 6.0, "relevance": "unrelated", "reason_vn": "Nói linh tinh"}'))
    print("Grammar:", parse_grammar_errors('{"band": 6.5, "errors": [{"error": "He go", "correct": "He goes", "explain_vn": "He là số ít"}]}'))
    print("Cleaned:", clean_grammar_errors('{"band": 6.5, "errors": [{"error": "go", "correct": "goes", "explain_vn": "He là số ít"}]}', "I go to school"))


if __name__ == "__main__":
    main()
