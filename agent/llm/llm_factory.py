"""
LLM 工厂模块
根据 .env 中的 LLM_PROVIDER 配置，创建对应的大模型实例
支持自定义 base_url 和 API Key
"""
import os
from agent.config import get_llm_provider, get_llm_model, get_llm_base_url
from agent.logger.logger import get_logger
from agent.exceptions.custom_exception import CustomException

logger = get_logger(__name__)

# 提供商 → 默认模型映射
DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "gemini": "gemini-2.0-flash",
    "deepseek": "deepseek-chat",
    "qwen": "qwen-plus",
    "ollama": "llama3.2:3b",
}

# 提供商 → API Key 环境变量名
API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
}


def get_llm():
    """
    根据配置创建 LLM 实例。
    优先使用 .env 中的 LLM_MODEL，否则使用各提供商默认模型。
    LLM_BASE_URL 可覆盖官方 API 地址（用于代理/中转）。
    """
    provider = get_llm_provider()
    model = get_llm_model() or DEFAULT_MODELS.get(provider)
    base_url = get_llm_base_url()
    api_key = os.getenv(API_KEY_ENV.get(provider, ""), None)

    logger.info("Initializing LLM: provider=%s, model=%s, base_url=%s", provider, model, base_url or "default")

    try:
        if provider == "openai":
            return _create_openai(model, base_url, api_key)
        elif provider == "anthropic":
            return _create_anthropic(model, api_key)
        elif provider == "gemini":
            return _create_gemini(model, api_key)
        elif provider == "deepseek":
            return _create_deepseek(model, base_url, api_key)
        elif provider == "qwen":
            return _create_qwen(model, api_key)
        elif provider == "ollama":
            return _create_ollama(model, base_url)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    except Exception as e:
        logger.error("Failed to create LLM: %s", e, exc_info=True)
        raise CustomException(e)


def _create_openai(model: str, base_url: str | None, api_key: str | None):
    from langchain_openai import ChatOpenAI
    import httpx

    trust_env = os.getenv("LLM_TRUST_ENV_PROXY", "0").strip().lower() in {"1", "true", "yes", "on"}
    kwargs = {
        "model": model,
        "temperature": 0,
        "timeout": float(os.getenv("LLM_TIMEOUT", "30")),
        "max_retries": int(os.getenv("LLM_MAX_RETRIES", "1")),
        "http_client": httpx.Client(
            trust_env=trust_env,
            timeout=float(os.getenv("LLM_TIMEOUT", "30")),
        ),
    }
    if base_url:
        kwargs["base_url"] = base_url
    if api_key:
        kwargs["api_key"] = api_key
    return ChatOpenAI(**kwargs)


def _create_anthropic(model: str, api_key: str | None):
    from langchain_anthropic import ChatAnthropic
    kwargs = {"model": model, "temperature": 0}
    if api_key:
        kwargs["api_key"] = api_key
    return ChatAnthropic(**kwargs)


def _create_gemini(model: str, api_key: str | None):
    from langchain_google_genai import ChatGoogleGenerativeAI
    kwargs = {"model": model, "temperature": 0}
    if api_key:
        kwargs["google_api_key"] = api_key
    return ChatGoogleGenerativeAI(**kwargs)


def _create_deepseek(model: str, base_url: str | None, api_key: str | None):
    from langchain_openai import ChatOpenAI
    import httpx

    trust_env = os.getenv("LLM_TRUST_ENV_PROXY", "0").strip().lower() in {"1", "true", "yes", "on"}
    # DeepSeek 兼容 OpenAI 接口
    kwargs = {
        "model": model,
        "temperature": 0,
        "base_url": base_url or "https://api.deepseek.com/v1",
        "timeout": float(os.getenv("LLM_TIMEOUT", "30")),
        "max_retries": int(os.getenv("LLM_MAX_RETRIES", "1")),
        "http_client": httpx.Client(
            trust_env=trust_env,
            timeout=float(os.getenv("LLM_TIMEOUT", "30")),
        ),
    }
    if api_key:
        kwargs["api_key"] = api_key
    return ChatOpenAI(**kwargs)


def _create_qwen(model: str, api_key: str | None):
    from langchain_community.chat_models.tongyi import ChatTongyi
    kwargs = {"model": model, "temperature": 0}
    if api_key:
        kwargs["dashscope_api_key"] = api_key
    return ChatTongyi(**kwargs)


def _create_ollama(model: str, base_url: str | None):
    from langchain_ollama import ChatOllama
    kwargs = {"model": model, "temperature": 0}
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOllama(**kwargs)
