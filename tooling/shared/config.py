#!/usr/bin/env python3
"""
Shared configuration utilities for Carinthia blog tools.

Provides API key lookup with environment variable priority and config file fallback.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, Any


class ConfigManager:
    """Manages configuration loading with environment variable priority."""

    def __init__(self):
        self.config_path = Path.home() / ".config" / "carinthia" / "config.json"
        self._config_cache: Optional[Dict[str, Any]] = None

    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if self._config_cache is not None:
            return self._config_cache

        if not self.config_path.exists():
            self._config_cache = {}
            return self._config_cache

        try:
            with open(self.config_path, 'r') as f:
                self._config_cache = json.load(f)
                return self._config_cache
        except (json.JSONDecodeError, IOError, OSError):
            self._config_cache = {}
            return self._config_cache

    def get_api_key(self, key_name: str) -> Optional[str]:
        """
        Get API key with environment variable priority and config file fallback.

        Args:
            key_name: The environment variable name (e.g., 'OPENAI_API_KEY')

        Returns:
            API key string if found, None otherwise
        """
        # First check environment variable (highest priority)
        env_value = os.getenv(key_name)
        if env_value:
            return env_value

        # Fallback to config file
        config = self._load_config_file()
        return config.get('api_keys', {}).get(key_name)

    def has_api_key(self, key_name: str) -> bool:
        """Check if API key is available from any source."""
        return self.get_api_key(key_name) is not None

    def get_editor(self) -> Optional[str]:
        """Get editor with environment variable priority and config file fallback."""
        # Check HUGO_EDITOR first
        hugo_editor = os.getenv('HUGO_EDITOR')
        if hugo_editor:
            return hugo_editor

        # Check EDITOR
        editor = os.getenv('EDITOR')
        if editor:
            return editor

        # Fallback to config file
        config = self._load_config_file()
        return config.get('editor', 'zed')  # Default to zed

    def get_blip_editor(self) -> str:
        """Get blip editor with environment variable priority and config file fallback."""
        # Check BLIP_EDITOR first (specific env var for blips)
        blip_editor = os.getenv('BLIP_EDITOR')
        if blip_editor:
            return blip_editor

        # Check EDITOR as fallback
        editor = os.getenv('EDITOR')
        if editor:
            return editor

        # Fallback to config file
        config = self._load_config_file()
        return config.get('blip_editor', 'vim')  # Default to vim

    def create_example_config(self) -> None:
        """Create an example configuration file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        example_config = {
            "api_keys": {
                "OPENAI_API_KEY": "your-openai-api-key-here",
                "ANTHROPIC_API_KEY": "your-anthropic-api-key-here"
            },
            "editor": "zed",
            "blip_editor": "vim"
        }

        if not self.config_path.exists():
            with open(self.config_path, 'w') as f:
                json.dump(example_config, f, indent=2)


# Global instance for easy importing
config_manager = ConfigManager()
