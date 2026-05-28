"""
Shared LLM client for business agents.

Switches between local Ollama and cloud APIs based on environment:
- SUBAGENT_MODE=local  → forces Ollama
- OLLAMA_URL set       → prefer Ollama
- Otherwise            → cloud with local fallback

Model selection:
- preference="speed"   → llama3.1:8b
- preference="quality" → qwen3:14b
"""

import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

from core import config
from integrations.llm import (
    ollama_chat,
    ollama_chat_stream,
    lmstudio_chat,
    lmstudio_chat_stream,
)
from integrations.claude import (
    claude_chat,
    claude_chat_stream,
    is_configured as claude_configured,
)
from integrations.gemini import gemini_chat, is_configured as gemini_configured
from integrations.openai_compatible import (
    openai_chat,
    openai_chat_stream,
    is_configured as openai_configured,
)

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified LLM client with environment-aware routing and model selection."""

    SPEED_MODEL = "llama3.1:8b"
    QUALITY_MODEL = "qwen3:14b"

    def __init__(self) -> None:
        self.mode = config.SUBAGENT_MODE  # local | cloud | hybrid
        self.ollama_url = config.OLLAMA_URL
        self.local_model = config.LOCAL_MODEL

    def _resolve_model(
        self, model: Optional[str] = None, preference: Optional[str] = None
    ) -> Optional[str]:
        """Pick a model based on explicit name or speed/quality preference."""
        if model:
            return model
        if preference == "speed":
            return self.SPEED_MODEL
        if preference == "quality":
            return self.QUALITY_MODEL
        return None

    def _prefer_local(self) -> bool:
        """Return True when environment says to use local inference."""
        return self.mode == "local" or bool(os.environ.get("OLLAMA_URL"))

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        preference: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stream: bool = False,
    ) -> str:
        """
        Send a chat request and return the full response text.

        Args:
            messages: OpenAI-style message list.
            model: Explicit model name (overrides preference).
            preference: "speed" or "quality" to auto-select a tuned local model.
            temperature: Sampling temperature.
            top_p: Nucleus sampling parameter.
            stream: If True, internally aggregates streamed chunks.

        Returns:
            Response text or an error string starting with "[LLM Error]".
        """
        resolved = self._resolve_model(model, preference)

        if stream:
            chunks = []
            async for chunk in self.chat_stream(
                messages, model=resolved, temperature=temperature, top_p=top_p
            ):
                chunks.append(chunk)
            return "".join(chunks)

        # Local-first path
        if self._prefer_local():
            try:
                return await ollama_chat(
                    messages, model=resolved, temperature=temperature, top_p=top_p
                )
            except Exception as e:
                logger.warning("Ollama failed (%s), falling back to cloud...", e)
            try:
                return await lmstudio_chat(
                    messages, model=resolved, temperature=temperature, top_p=top_p
                )
            except Exception:
                pass

        # Cloud path
        errors: List[str] = []
        if claude_configured():
            try:
                return await claude_chat(
                    messages, model=resolved, temperature=temperature, top_p=top_p
                )
            except Exception as e:
                errors.append(f"Claude: {e}")
        if openai_configured():
            try:
                return await openai_chat(
                    messages, model=resolved, temperature=temperature, top_p=top_p
                )
            except Exception as e:
                errors.append(f"OpenAI: {e}")
        if gemini_configured():
            try:
                return await gemini_chat(messages, temperature=temperature, top_p=top_p)
            except Exception as e:
                errors.append(f"Gemini: {e}")

        # Final fallback to local
        try:
            return await ollama_chat(
                messages, model=resolved, temperature=temperature, top_p=top_p
            )
        except Exception as e:
            errors.append(f"Ollama: {e}")
        try:
            return await lmstudio_chat(
                messages, model=resolved, temperature=temperature, top_p=top_p
            )
        except Exception as e:
            errors.append(f"LMStudio: {e}")

        return f"[LLM Error] {' | '.join(errors)}"

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        preference: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat response as text chunks.

        Yields text chunks. If all providers fail, yields a single error chunk.
        """
        resolved = self._resolve_model(model, preference)

        # Local-first path
        if self._prefer_local():
            try:
                async for chunk in ollama_chat_stream(
                    messages, model=resolved, temperature=temperature, top_p=top_p
                ):
                    yield chunk
                return
            except Exception as e:
                logger.warning("Ollama stream failed (%s), falling back...", e)
            try:
                async for chunk in lmstudio_chat_stream(
                    messages, model=resolved, temperature=temperature, top_p=top_p
                ):
                    yield chunk
                return
            except Exception:
                pass

        # Cloud path
        if claude_configured():
            try:
                async for chunk in claude_chat_stream(
                    messages, model=resolved, temperature=temperature, top_p=top_p
                ):
                    yield chunk
                return
            except Exception:
                pass
        if openai_configured():
            try:
                async for chunk in openai_chat_stream(
                    messages, model=resolved, temperature=temperature, top_p=top_p
                ):
                    yield chunk
                return
            except Exception:
                pass
        if gemini_configured():
            try:
                result = await gemini_chat(messages, temperature=temperature, top_p=top_p)
                for word in result.split(" "):
                    yield word + " "
                return
            except Exception:
                pass

        # Final fallback to local
        try:
            async for chunk in ollama_chat_stream(
                messages, model=resolved, temperature=temperature, top_p=top_p
            ):
                yield chunk
            return
        except Exception:
            pass
        try:
            async for chunk in lmstudio_chat_stream(
                messages, model=resolved, temperature=temperature, top_p=top_p
            ):
                yield chunk
            return
        except Exception:
            pass

        yield "[LLM Error] No provider available."
