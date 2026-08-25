"""
Configuration management for VIGH-02 AI AGENT.
Persists settings in ~/.vigh02/config.json.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

CONFIG_DIR = Path.home() / ".vigh02"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": "2.0.0",
    "provider": "ollama",  # 'ollama', 'lmstudio', 'custom', 'openai', 'anthropic', 'gemini', 'groq'
    "model": "qwen2.5-coder:7b",
    "ollama_base_url": "http://127.0.0.1:11434",
    "lmstudio_base_url": "http://127.0.0.1:1234/v1",
    "custom_base_url": "http://127.0.0.1:8000/v1",
    "custom_api_key": "",
    "openai_api_key": "",
    "anthropic_api_key": "",
    "gemini_api_key": "",
    "groq_api_key": "",
    "temperature": 0.2,
    "max_tokens": 4096,
    "auto_confirm_read": True,
    "auto_confirm_write": False,
    "auto_confirm_exec": False,
    "web_host": "127.0.0.1",
    "web_port": 8440,
    "auto_open_browser": True,
    "theme": "dark",
    "ignored_patterns": [
        "__pycache__", ".git", ".idea", ".vscode", "node_modules",
        "dist", "build", ".venv", "venv", ".next", ".nuxt",
        "*.pyc", "*.pyo", "*.pyd", "*.so", "*.dll", "*.exe",
        ".DS_Store", "Thumbs.db", ".gemini"
    ]
}


class ConfigManager:
    """Manages loading, updating, and saving configuration."""

    def __init__(self):
        self.config_dir = CONFIG_DIR
        self.config_file = CONFIG_FILE
        self._config: Dict[str, Any] = DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> Dict[str, Any]:
        """Loads configuration from file or creates default."""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._config.update(saved)
            else:
                self.save()
        except Exception:
            self._config = DEFAULT_CONFIG.copy()
        return self._config

    def save(self) -> None:
        """Saves current configuration to file."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save config to {self.config_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Set configuration value."""
        self._config[key] = value
        if auto_save:
            self.save()

    def update(self, updates: Dict[str, Any], auto_save: bool = True) -> None:
        """Bulk update configuration."""
        self._config.update(updates)
        if auto_save:
            self.save()

    @property
    def all(self) -> Dict[str, Any]:
        """Return all config values."""
        return self._config.copy()


# Global singleton
config = ConfigManager()
