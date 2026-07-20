import base64
import os

import httpx
from dotenv import load_dotenv
from openai import OpenAI

from agent.logger.logger import get_logger

logger = get_logger(__name__)

load_dotenv()

DEFAULT_OCR_MODEL = "deepseek-ai/DeepSeek-OCR"


def describe_image(image_bytes: bytes, mime_type: str = "image/png") -> str:
    """Describe an image/page as natural language for retrieval."""
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("OCR_MODEL", DEFAULT_OCR_MODEL)

    if not api_key or not base_url:
        logger.warning("OCR skipped because OPENAI_API_KEY or LLM_BASE_URL is missing")
        return ""

    data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    trust_env = os.getenv("LLM_TRUST_ENV_PROXY", "0").strip().lower() in {"1", "true", "yes", "on"}
    timeout = float(os.getenv("OCR_TIMEOUT", os.getenv("LLM_TIMEOUT", "60")))

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        http_client=httpx.Client(trust_env=trust_env, timeout=timeout),
    )

    prompt = (
        "Extract the useful knowledge from this PDF page or image. "
        "Return natural language suitable for retrieval-based question answering. "
        "Include visible headings, paragraph facts, table meanings, chart trends, "
        "important numbers, labels, and conclusions. Do not output markdown tables."
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        logger.warning("OCR model call failed: %s", exc, exc_info=True)
        return ""

