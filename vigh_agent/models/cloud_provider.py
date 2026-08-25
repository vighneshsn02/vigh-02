"""
Cloud / Online Provider Fallback for VIGH-02 AI AGENT.
Allows using OpenAI, Anthropic, Gemini, Groq, OpenRouter when internet/keys are available.
"""

from typing import List, Dict, Any, Generator, Optional
from vigh_agent.models.lmstudio_provider import OpenAICompatibleProvider

CLOUD_ENDPOINTS = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai"
}


class CloudProvider(OpenAICompatibleProvider):
    """Cloud-based LLM provider (requires internet and API key)."""

    def __init__(self, provider_name: str, api_key: str, model: str):
        base_url = CLOUD_ENDPOINTS.get(provider_name.lower(), "https://api.openai.com/v1")
        super().__init__(
            name=provider_name,
            base_url=base_url,
            model=model,
            api_key=api_key
        )
