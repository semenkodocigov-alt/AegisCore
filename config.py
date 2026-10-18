"""Aegis Core configuration management.

Thread-safe singleton with atomic persistence and value validation.
"""
import os
import json
import logging
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Expected types for each config key (used for validation)
_CONFIG_SCHEMA: Dict[str, type] = {
    "use_improved_signatures": bool,
    "enable_sound": bool,
    "enable_usb_monitoring": bool,
    "enable_autorun_scanning": bool,
    "backup_on_delete": bool,
    "secure_delete_passes": int,
    "cache_duration": int,
    "max_threads": int,
    "max_file_size": int,
    "log_file": (str, type(None)),  # type: ignore[dict-item]
    "vt_api_key_env": str,
    "vt_api_key": str,
    "quarantine_dir": str,
    "backup_dir": str,
}


class Config:
    """Application configuration with atomic save and thread safety."""

    # Default configuration values
    DEFAULT_CONFIG: Dict[str, Any] = {
        "use_improved_signatures": True,   # Use signatures_improved.py with VirusTotal
        "enable_sound": True,              # Enable sound effects
        "enable_usb_monitoring": False,    # Enable USB monitoring by default
        "enable_autorun_scanning": True,   # Autorun scanning
        "backup_on_delete": True,          # Create backup before deletion
        "secure_delete_passes": 3,         # Passes for secure delete
        "cache_duration": 604800,          # Cache lifetime (7 days in seconds)
        "max_threads": 4,                  # Max scan threads
        "max_file_size": 104857600,        # Max file size (100 MB)
        "log_file": None,                  # Log file path (None = no file logging)
        "vt_api_key_env": "VIRUSTOTAL_API_KEY",  # Env var name for API key
        "vt_api_key": "",                  # VirusTotal API key (direct)
        "quarantine_dir": "./quarantine",  # Quarantine directory
        "backup_dir": "./backups",         # Backup directory
    }

    def __init__(self, config_file: Optional[str] = None) -> None:
        """Initialize configuration, loading from file if available.

        Args:
            config_file: Path to JSON config file. Defaults to config.json
                         in the same directory as this module.
        """
        self._lock = threading.Lock()
        self.config_file: Path = (
            Path(config_file) if config_file else Path(__file__).parent / "config.json"
        )
        self.settings: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file, merging with defaults.

        Returns the merged config dict.
        """
        if isinstance(self.config_file, str):
            self.config_file = Path(self.config_file)

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded: Dict[str, Any] = json.load(f)
                config = self.DEFAULT_CONFIG.copy()
                config.update(loaded)
                self._validate_config(config)
                return config
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON in config file: %s", e)
            except OSError as e:
                logger.warning("Cannot read config file: %s", e)
            logger.info("Using default configuration")

        # Create default config file
        default = self.DEFAULT_CONFIG.copy()
        self._save_config(default)
        return default

    @staticmethod
    def _validate_config(config: Dict[str, Any]) -> None:
        """Validate config value types against the schema.

        Logs warnings for mismatched types and resets them to defaults.
        """
        for key, expected_type in _CONFIG_SCHEMA.items():
            if key not in config:
                continue
            value = config[key]
            # Handle union types like (str, NoneType)
            if isinstance(expected_type, tuple):
                if not isinstance(value, expected_type):
                    logger.warning(
                        "Config key '%s' has invalid type %s (expected %s), "
                        "resetting to default",
                        key, type(value).__name__, expected_type,
                    )
                    if key in Config.DEFAULT_CONFIG:
                        config[key] = Config.DEFAULT_CONFIG[key]
            else:
                if not isinstance(value, expected_type):
                    logger.warning(
                        "Config key '%s' has invalid type %s (expected %s), "
                        "resetting to default",
                        key, type(value).__name__, expected_type.__name__,
                    )
                    if key in Config.DEFAULT_CONFIG:
                        config[key] = Config.DEFAULT_CONFIG[key]

    def _save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Save configuration atomically (write to temp file, then rename).

        Args:
            config: Config dict to save. Defaults to self.settings.
        """
        config = config or self.settings
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            # Atomic write: create temp file in same dir, then rename
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self.config_file.parent),
                suffix='.tmp',
                prefix='config_',
            )
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                os.replace(tmp_path, str(self.config_file))
                logger.debug("Configuration saved: %s", self.config_file)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except OSError as e:
            logger.error("Failed to save configuration: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.

        Args:
            key: The config parameter name.
            default: Fallback value if key is not present.
        """
        with self._lock:
            return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and persist to disk.

        Args:
            key: The config parameter name.
            value: The new value.
        """
        with self._lock:
            self.settings[key] = value
            self._save_config()

    def get_vt_api_key(self) -> str:
        """Get the VirusTotal API key.

        Checks the direct config value first, then falls back to the
        environment variable specified in the config.
        """
        api_key: str = self.get("vt_api_key", "")
        if api_key:
            return api_key
        env_var: str = self.get("vt_api_key_env", "VIRUSTOTAL_API_KEY")
        return os.environ.get(env_var, "")

    def is_using_improved_signatures(self) -> bool:
        """Check whether the improved signature database is enabled."""
        return bool(self.get("use_improved_signatures", True))

    def print_config(self) -> None:
        """Log the current configuration (replaces direct print output)."""
        separator = "=" * 50
        lines = [separator, "КОНФИГУРАЦИЯ AEGIS CORE", separator]
        with self._lock:
            for key, value in self.settings.items():
                lines.append(f"{key:.<30} {value}")
        lines.append(separator)
        output = "\n".join(lines)
        logger.info("\n%s", output)


# ---------------------------------------------------------------------------
# Thread-safe singleton
# ---------------------------------------------------------------------------

_config_instance: Optional[Config] = None
_config_lock = threading.Lock()


def get_config(config_file: Optional[str] = None) -> Config:
    """Get the global Config singleton (thread-safe lazy initialization).

    Args:
        config_file: Optional path to JSON config file (used only on
                     first call to create the instance).
    """
    global _config_instance
    if _config_instance is None:
        with _config_lock:
            # Double-checked locking
            if _config_instance is None:
                _config_instance = Config(config_file)
    return _config_instance


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cfg = get_config()
    cfg.print_config()

    # Example:
    # cfg.set("enable_sound", False)
    # cfg.print_config()
