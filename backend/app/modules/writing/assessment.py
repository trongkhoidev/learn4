import json

from app.core.config import settings
from app.integrations.llm.transport import complete

WRITING_SYSTEM = "You are a senior IELTS Writing examiner. Be strict and unbiased.\nReturn ONLY valid JSON, no markdown."

WRITING_USER = """Task type: {task_type}
Prompt: {question}
Essay: {essay}

Evaluate on 4 IELTS criteria (score 0-9, 0.5 increments):
{{
  "task_response": {{"score": float, "feedback": "Vietnamese", "strengths": [str], "weaknesses": [str]}},
  "coherence_cohesion": {{"score": float, "feedback": "Vietnamese", "linkers_used": [str], "suggestions": [str]}},
  "lexical_resource": {{"score": float, "feedback": "Vietnamese", "advanced_words": [str], "repetitions": [str]}},
  "grammatical_accuracy": {{"score": float, "feedback": "Vietnamese"}},
  "errors": [{{"original": str, "corrected": str, "type": str, "explain": "Vietnamese"}}],
  "improved_sample": "English, ~1 band higher, natural"
}}
Rules: word_count < 150 (task1) / < 250 (task2) → penalize task_response; feedback tiếng Việt; improved_sample tiếng Anh."""


def grade_writing(task_type: str, question: str, essay: str) -> dict:
    model = settings.gemini_model if settings.llm_provider == "gemini" else settings.groq_writing_model
    content = complete(
        model,
        [
            {"role": "system", "content": WRITING_SYSTEM},
            {"role": "user", "content": WRITING_USER.format(task_type=task_type, question=question, essay=essay)},
        ],
        max_tokens=4096,
    )
    result = json.loads(content)
    result["word_count"] = len(essay.split())
    result["task_type"] = task_type
    return result
