"""
统一配置模块
从 .env 文件读取 LLM 提供商和模型配置
"""
from dotenv import load_dotenv
import os

load_dotenv()

# LLM 提供商选择: openai / anthropic / gemini / deepseek / qwen / ollama
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")

# 可选：覆盖默认模型名称
LLM_MODEL = os.getenv("LLM_MODEL", None)

# 可选：自定义 API base_url（用于代理/中转）
LLM_BASE_URL = os.getenv("LLM_BASE_URL", None)


def get_llm_provider() -> str:
    return LLM_PROVIDER


def get_llm_model() -> str | None:
    return LLM_MODEL


def get_llm_base_url() -> str | None:
    return LLM_BASE_URL
