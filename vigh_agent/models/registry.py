"""
Model Registry and Auto-Discovery for VIGH-02 AI AGENT.
Automatically probes local endpoints (Ollama, LM Studio, etc.) and lists models.
"""

from typing import List, Dict, Any, Optional, Tuple
from vigh_agent.config import config
from vigh_agent.models.provider import BaseProvider
from vigh_agent.models.ollama_provider import OllamaProvider
from vigh_agent.models.lmstudio_provider import OpenAICompatibleProvider
from vigh_agent.models.cloud_provider import CloudProvider


class ModelRegistry:
    """Discovers, catalogs, and instantiates model providers."""

    CODING_MODEL_PRIORITY = [
        "qwen2.5-coder:7b",
        "qwen2.5-coder:32b",
        "qwen2.5-coder:14b",
        "qwen2.5-coder:3b",
        "qwen2.5-coder:1.5b",
        "deepseek-coder:6.7b",
        "deepseek-coder:1.3b",
        "codellama:7b",
        "llama3.2:latest",
        "llama3.2:3b",
        "llama3.1:8b",
        "gemma3:4b",
        "falcon3:3b",
        "mistral:7b"
    ]

    def __init__(self):
        self.ollama = OllamaProvider(base_url=config.get("ollama_base_url", "http://127.0.0.1:11434"))
        self.lmstudio = OpenAICompatibleProvider(
            name="lmstudio",
            base_url=config.get("lmstudio_base_url", "http://127.0.0.1:1234/v1")
        )

    def scan_all_models(self) -> List[Dict[str, Any]]:
        """Scans all local and configured providers for available models."""
        all_models = []
        
        # 1. Ollama models
        if self.ollama.health_check():
            ollama_models = self.ollama.list_models()
            all_models.extend(ollama_models)

        # 2. LM Studio models
        if self.lmstudio.health_check():
            lm_models = self.lmstudio.list_models()
            all_models.extend(lm_models)

        # 3. Custom local endpoint if configured
        custom_url = config.get("custom_base_url")
        if custom_url:
            custom_p = OpenAICompatibleProvider(name="custom", base_url=custom_url)
            if custom_p.health_check():
                all_models.extend(custom_p.list_models())

        return all_models

    def auto_detect_best_model(self) -> Tuple[str, str]:
        """
        Auto-detects the best available model.
        Returns: (provider_name: str, model_id: str)
        """
        configured_provider = config.get("provider", "ollama")
        configured_model = config.get("model", "qwen2.5-coder:7b")

        available_models = self.scan_all_models()
        if not available_models:
            # Fallback to configured
            return configured_provider, configured_model

        available_ids = [m["id"] for m in available_models]

        # If configured model is present, keep it
        if configured_model in available_ids:
            # Determine provider
            for m in available_models:
                if m["id"] == configured_model:
                    return m.get("provider", "ollama"), configured_model

        # Otherwise pick the highest priority coding model
        for priority_model in self.CODING_MODEL_PRIORITY:
            for m in available_models:
                if m["id"] == priority_model or priority_model in m["id"]:
                    return m.get("provider", "ollama"), m["id"]

        # Default to first available local model
        first = available_models[0]
        return first.get("provider", "ollama"), first["id"]

    def get_provider(self, provider_name: Optional[str] = None, model_name: Optional[str] = None) -> BaseProvider:
        """Instantiates the appropriate provider with current or requested model."""
        if not provider_name or not model_name:
            detected_p, detected_m = self.auto_detect_best_model()
            provider_name = provider_name or detected_p
            model_name = model_name or detected_m

        provider_name = provider_name.lower()

        if provider_name == "ollama":
            return OllamaProvider(
                base_url=config.get("ollama_base_url", "http://127.0.0.1:11434"),
                model=model_name
            )
        elif provider_name in ("lmstudio", "localai", "vllm", "llama.cpp"):
            return OpenAICompatibleProvider(
                name=provider_name,
                base_url=config.get("lmstudio_base_url", "http://127.0.0.1:1234/v1"),
                model=model_name
            )
        elif provider_name == "custom":
            return OpenAICompatibleProvider(
                name="custom",
                base_url=config.get("custom_base_url", "http://127.0.0.1:8000/v1"),
                model=model_name,
                api_key=config.get("custom_api_key", "")
            )
        elif provider_name in ("openai", "groq", "openrouter", "gemini"):
            api_key = config.get(f"{provider_name}_api_key", "")
            return CloudProvider(
                provider_name=provider_name,
                api_key=api_key,
                model=model_name
            )
        else:
            # Default to Ollama
            return OllamaProvider(
                base_url=config.get("ollama_base_url", "http://127.0.0.1:11434"),
                model=model_name
            )


# Global registry singleton
model_registry = ModelRegistry()
