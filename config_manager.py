import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ConfigManager:
    """Simple configuration manager for My-AI-Bot.

    Responsibilities:
      - load JSON config from disk
      - provide basic validation for MT5-related config keys
      - helpers to access trading and cycle config
    """

    @staticmethod
    def load_config(path: str) -> Dict[str, Any]:
        """Load JSON config from `path` and return dict."""
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    @staticmethod
    def validate_config(cfg: Dict[str, Any]) -> bool:
        """Run a set of lightweight validations and return True if config looks usable.

        This does NOT attempt to validate secrets or network connectivity — only
        presence and basic types for required fields.
        """
        if not isinstance(cfg, dict):
            logger.error("Config is not a JSON object/dictionary")
            return False

        mt5_cfg = cfg.get("mt5")
        if not mt5_cfg or not isinstance(mt5_cfg, dict):
            logger.error("Missing 'mt5' configuration section")
            return False

        # terminal_path is the most important field to allow mt5.initialize to find the terminal
        if not mt5_cfg.get("terminal_path"):
            logger.error("mt5.terminal_path is required in config and should point to your MT5 terminal.exe")
            return False

        # Optional but recommended fields to check types
        if not isinstance(mt5_cfg.get("timeout", 10), (int, float)):
            logger.error("mt5.timeout must be a number")
            return False

        trading = cfg.get("trading")
        if trading and not isinstance(trading, dict):
            logger.error("'trading' section must be a JSON object if present")
            return False

        return True

    @staticmethod
    def get_trading_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
        return cfg.get("trading", {})

    @staticmethod
    def get_cycle_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
        return cfg.get("cycle", {})
