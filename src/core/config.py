"""
Configuration management for HyperEternalAgent framework.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class LLMConfig:
    """LLM configuration."""

    provider: str = "openai"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    base_url: Optional[str] = None

    def __post_init__(self) -> None:
        # Resolve environment variables
        if self.api_key and self.api_key.startswith("${") and self.api_key.endswith("}"):
            env_var = self.api_key[2:-1]
            self.api_key = os.environ.get(env_var)


@dataclass
class AgentConfig:
    """Agent configuration."""

    agent_id: str = ""
    agent_type: str = ""
    llm: Optional[LLMConfig] = None
    tools: List[Dict[str, Any]] = field(default_factory=list)
    limits: Dict[str, Any] = field(default_factory=dict)
    retry_policy: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PersistenceConfig:
    """Persistence configuration."""

    backend: str = "redis"
    url: str = "redis://localhost:6379/0"
    checkpoint_interval: int = 300
    max_snapshots: int = 10


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""

    enabled: bool = True
    metrics_port: int = 9090
    log_level: str = "INFO"
    log_file: str = "./logs/hypereternal.log"


@dataclass
class RuntimeConfig:
    """Runtime configuration."""

    max_workers: int = 10
    task_timeout: int = 3600
    heartbeat_interval: int = 30


@dataclass
class SystemConfig:
    """System configuration."""

    name: str = "HyperEternalAgent"
    version: str = "0.1.0"
    runtime: RuntimeConfig = field(default_factory=RuntimeConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    llm: Dict[str, LLMConfig] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemConfig":
        """Create from dictionary."""
        runtime_data = data.get("runtime", {})
        persistence_data = data.get("persistence", {})
        monitoring_data = data.get("monitoring", {})

        llm_configs = {}
        for provider, config in data.get("llm", {}).get("providers", {}).items():
            llm_configs[provider] = LLMConfig(
                provider=provider,
                **config,
            )

        return cls(
            name=data.get("name", "HyperEternalAgent"),
            version=data.get("version", "0.1.0"),
            runtime=RuntimeConfig(**runtime_data) if runtime_data else RuntimeConfig(),
            persistence=PersistenceConfig(**persistence_data) if persistence_data else PersistenceConfig(),
            monitoring=MonitoringConfig(**monitoring_data) if monitoring_data else MonitoringConfig(),
            llm=llm_configs,
        )


class ConfigLoader:
    """Configuration loader."""

    def __init__(self, config_dirs: Optional[List[str]] = None):
        self.config_dirs = config_dirs or ["./config"]
        self._cache: Dict[str, Any] = {}

    def load_yaml(self, config_name: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        config_path = self._find_config_file(config_name)
        if not config_path:
            raise FileNotFoundError(f"Configuration file not found: {config_name}")

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Resolve environment variables
        config = self._resolve_env_vars(config)
        return config

    def load_system_config(self, config_path: Optional[str] = None) -> SystemConfig:
        """Load system configuration."""
        if config_path:
            data = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        else:
            data = self.load_yaml("config")

        return SystemConfig.from_dict(data.get("system", {}))

    def _find_config_file(self, config_name: str) -> Optional[str]:
        """Find configuration file."""
        extensions = [".yaml", ".yml", ".json"]
        for config_dir in self.config_dirs:
            for ext in extensions:
                path = os.path.join(config_dir, f"{config_name}{ext}")
                if os.path.exists(path):
                    return path
        return None

    def _resolve_env_vars(self, config: Any) -> Any:
        """Resolve environment variables in configuration."""
        import re

        if isinstance(config, str):
            # Match ${VAR} or ${VAR:default}
            pattern = r"\$\{([^}:]+)(?::([^}]*))?\}"
            matches = re.findall(pattern, config)

            for var_name, default in matches:
                env_value = os.environ.get(var_name, default)
                config = config.replace(
                    f"${{{var_name}:{default}}}" if default else f"${{{var_name}}}",
                    env_value,
                )
            return config
        elif isinstance(config, dict):
            return {k: self._resolve_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._resolve_env_vars(item) for item in config]
        return config

    def clear_cache(self) -> None:
        """Clear configuration cache."""
        self._cache.clear()


# Global configuration loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_dirs: Optional[List[str]] = None) -> ConfigLoader:
    """Get global configuration loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_dirs)
    return _config_loader
