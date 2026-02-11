from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def _extract_response_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        blocks: list[str] = []
        for block in content:
            if isinstance(block, str):
                blocks.append(block)
                continue
            if isinstance(block, dict):
                maybe_text = block.get("text")
                if isinstance(maybe_text, str):
                    blocks.append(maybe_text)
        return "\n".join(blocks)
    return str(content)


def try_parse_json(content: Any) -> dict[str, Any] | None:
    text = _extract_response_text(content).strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


@dataclass(slots=True)
class LLMProviderFactory:
    provider: str = settings.LLM_PROVIDER.lower().strip()
    model: str = settings.LLM_MODEL

    def is_enabled(self) -> bool:
        if self.provider == "openai":
            return bool(settings.OPENAI_API_KEY)
        if self.provider == "anthropic":
            return bool(settings.ANTHROPIC_API_KEY)
        if self.provider == "ollama":
            return bool(settings.OLLAMA_BASE_URL)
        return False

    def build_chat_model(self, temperature: float = 0.0):
        if not self.is_enabled():
            return None

        try:
            if self.provider == "openai":
                from langchain_openai import ChatOpenAI

                return ChatOpenAI(
                    model=self.model,
                    temperature=temperature,
                    api_key=settings.OPENAI_API_KEY,
                )
            if self.provider == "anthropic":
                from langchain_anthropic import ChatAnthropic

                return ChatAnthropic(
                    model=self.model,
                    temperature=temperature,
                    api_key=settings.ANTHROPIC_API_KEY,
                )
            if self.provider == "ollama":
                from langchain_community.chat_models import ChatOllama

                return ChatOllama(
                    model=self.model,
                    base_url=settings.OLLAMA_BASE_URL,
                    temperature=temperature,
                )
        except Exception:
            logger.exception("Failed to initialize configured LLM provider '%s'.", self.provider)
            return None

        logger.warning("Unsupported LLM provider configured: %s", self.provider)
        return None
