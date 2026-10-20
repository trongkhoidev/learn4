from app.core.config import settings
from app.integrations.llm.transport import groq_vision_completion

OCR_PROMPT = "Transcribe the handwritten English essay in this image exactly, preserving paragraphs and punctuation."


def transcribe_image(base64_data: str, mime_type: str = "image/jpeg") -> str:
    return groq_vision_completion(
        settings.groq_ocr_model,
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}},
                ],
            }
        ],
        temperature=0.0,
    )
