"""
Configuration Schema for Multi-Agent Framework (MAF)

JSON schema validation and configuration management for multi-provider collaboration setups.
Provides validation, defaults, and configuration loading for MAF orchestrations.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from dataclasses import asdict

try:
    import jsonschema

    JSONSCHEMA_AVAILABLE = True
except ImportError:
    jsonschema = None
    JSONSCHEMA_AVAILABLE = False

from .multi_provider_coordinator import CollaborationConfig, ProviderRole
from .provider_registry import ProviderCapability

logger = logging.getLogger(__name__)


# JSON Schema for MAF Configuration
MAF_CONFIG_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Human-readable name for this MAF configuration"},
        "description": {"type": "string", "description": "Description of what this configuration is designed for"},
        "version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+\\.\\d+$",
            "description": "Semantic version of this configuration",
        },
        "providers": {
            "type": "array",
            "minItems": 2,
            "maxItems": 6,
            "items": {
                "type": "object",
                "properties": {
                    "provider_id": {"type": "string", "description": "Unique identifier for the provider"},
                    "role": {
                        "type": "string",
                        "enum": ["analyzer", "critic", "synthesizer", "validator", "researcher", "implementer"],
                        "description": "Role this provider plays in the collaboration",
                    },
                    "weight": {
                        "type": "number",
                        "minimum": 0.1,
                        "maximum": 5.0,
                        "default": 1.0,
                        "description": "Voting weight for consensus decisions",
                    },
                    "capabilities": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": [
                                "text_generation",
                                "code_analysis",
                                "critical_thinking",
                                "creative_writing",
                                "mathematical",
                                "research",
                                "validation",
                                "synthesis",
                            ],
                        },
                        "description": "Capabilities this provider brings to the collaboration",
                    },
                    "model_override": {"type": "string", "description": "Override the default model for this provider"},
                },
                "required": ["provider_id", "role"],
            },
        },
        "collaboration_settings": {
            "type": "object",
            "properties": {
                "max_rounds": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 5,
                    "description": "Maximum number of conversation rounds",
                },
                "convergence_threshold": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "default": 0.6,
                    "description": "Minimum convergence score for consensus (0-1)",
                },
                "review_mode": {
                    "type": "boolean",
                    "default": False,
                    "description": "Pause after each round for human review",
                },
                "consensus_strategy": {
                    "type": "string",
                    "enum": ["weighted_vote", "majority", "expert_consensus"],
                    "default": "weighted_vote",
                    "description": "Strategy for reaching consensus",
                },
                "timeout_per_round": {
                    "type": "number",
                    "minimum": 10.0,
                    "maximum": 300.0,
                    "default": 60.0,
                    "description": "Timeout in seconds per round",
                },
            },
        },
        "task_types": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "code_review",
                    "architecture_design",
                    "problem_solving",
                    "creative_writing",
                    "research",
                    "analysis",
                    "implementation",
                ],
            },
            "description": "Types of tasks this configuration is optimized for",
        },
        "metadata": {
            "type": "object",
            "properties": {
                "author": {"type": "string"},
                "created": {"type": "string", "format": "date-time"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
    "required": ["name", "providers"],
}


class MAFConfigLoader:
    """
    Loads and validates MAF configuration files.

    Provides methods to load configurations from JSON files,
    validate them against the schema, and convert to CollaborationConfig objects.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path(__file__).parent / "configs"
        self.config_dir.mkdir(exist_ok=True)

    def load_config(self, config_name: str) -> CollaborationConfig:
        """
        Load a MAF configuration by name.

        Args:
            config_name: Name of the configuration file (without .json extension)

        Returns:
            CollaborationConfig object

        Raises:
            FileNotFoundError: If config file doesn't exist
            jsonschema.ValidationError: If config doesn't match schema
            ValueError: If config cannot be converted to CollaborationConfig
        """
        config_path = self.config_dir / f"{config_name}.json"

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration '{config_name}' not found at {config_path}")

        with open(config_path, "r") as f:
            config_data = json.load(f)

        # Validate against schema
        self.validate_config(config_data)

        # Convert to CollaborationConfig
        return self._data_to_config(config_data)

    def validate_config(self, config_data: Dict[str, Any]) -> None:
        """
        Validate configuration data against the MAF schema.

        Args:
            config_data: Configuration data to validate

        Raises:
            jsonschema.ValidationError: If validation fails
        """
        if not JSONSCHEMA_AVAILABLE:
            logger.warning("jsonschema not available, skipping configuration validation")
            return

        try:
            jsonschema.validate(config_data, MAF_CONFIG_SCHEMA)
            logger.info("Configuration validation successful")
        except jsonschema.ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise

    def save_config(
        self, config: CollaborationConfig, config_name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Save a CollaborationConfig as a MAF configuration file.

        Args:
            config: Configuration to save
            config_name: Name for the configuration file
            metadata: Additional metadata to include

        Returns:
            Path to the saved configuration file
        """
        config_data = self._config_to_data(config, metadata or {})
        config_path = self.config_dir / f"{config_name}.json"

        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2, default=str)

        logger.info(f"Configuration saved to {config_path}")
        return config_path

    def list_configs(self) -> List[str]:
        """List all available MAF configuration files."""
        return [f.stem for f in self.config_dir.glob("*.json")]

    def _data_to_config(self, data: Dict[str, Any]) -> CollaborationConfig:
        """Convert JSON data to CollaborationConfig object."""
        settings = data.get("collaboration_settings", {})

        providers = []
        for p_data in data["providers"]:
            capabilities = set()
            for cap_str in p_data.get("capabilities", []):
                try:
                    capabilities.add(ProviderCapability[cap_str.upper()])
                except KeyError:
                    logger.warning(f"Unknown capability: {cap_str}")

            provider = ProviderRole(
                provider_id=p_data["provider_id"],
                role=p_data["role"],
                weight=p_data.get("weight", 1.0),
                capabilities=capabilities,
            )
            providers.append(provider)

        return CollaborationConfig(
            providers=providers,
            max_rounds=settings.get("max_rounds", 5),
            convergence_threshold=settings.get("convergence_threshold", 0.6),
            review_mode=settings.get("review_mode", False),
            consensus_strategy=settings.get("consensus_strategy", "weighted_vote"),
            timeout_per_round=settings.get("timeout_per_round", 60.0),
        )

    def _config_to_data(self, config: CollaborationConfig, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Convert CollaborationConfig to JSON data."""
        return {
            "name": metadata.get("name", "MAF Configuration"),
            "description": metadata.get("description", "Multi-Agent Framework configuration"),
            "version": metadata.get("version", "1.0.0"),
            "providers": [
                {
                    "provider_id": p.provider_id,
                    "role": p.role,
                    "weight": p.weight,
                    "capabilities": [cap.value for cap in p.capabilities],
                }
                for p in config.providers
            ],
            "collaboration_settings": {
                "max_rounds": config.max_rounds,
                "convergence_threshold": config.convergence_threshold,
                "review_mode": config.review_mode,
                "consensus_strategy": config.consensus_strategy,
                "timeout_per_round": config.timeout_per_round,
            },
            "task_types": metadata.get("task_types", []),
            "metadata": metadata,
        }


# Predefined MAF Configurations
DEFAULT_CONFIGS = {
    "grok_claude_dual": {
        "name": "Grok + Claude Dual Agent",
        "description": "Classic dual-agent collaboration between Grok and Claude",
        "version": "1.0.0",
        "providers": [
            {
                "provider_id": "grok",
                "role": "primary_agent",
                "weight": 1.0,
                "capabilities": ["text_generation", "critical_thinking", "research"],
            },
            {
                "provider_id": "claude",
                "role": "secondary_agent",
                "weight": 1.0,
                "capabilities": ["text_generation", "validation", "creative_writing"],
            },
        ],
        "collaboration_settings": {
            "max_rounds": 5,
            "convergence_threshold": 0.6,
            "review_mode": False,
            "consensus_strategy": "weighted_vote",
            "timeout_per_round": 60.0,
        },
        "task_types": ["problem_solving", "analysis", "implementation"],
        "metadata": {"author": "MAF System", "tags": ["dual", "classic", "balanced"]},
    },
    "code_review_trio": {
        "name": "Code Review Trio",
        "description": "Grok, Claude, and Gemini for comprehensive code review",
        "version": "1.0.0",
        "providers": [
            {
                "provider_id": "grok",
                "role": "analyzer",
                "weight": 1.2,
                "capabilities": ["code_analysis", "critical_thinking"],
            },
            {
                "provider_id": "claude",
                "role": "validator",
                "weight": 1.0,
                "capabilities": ["code_analysis", "validation"],
            },
            {
                "provider_id": "gemini",
                "role": "researcher",
                "weight": 0.8,
                "capabilities": ["research", "text_generation"],
            },
        ],
        "collaboration_settings": {
            "max_rounds": 4,
            "convergence_threshold": 0.7,
            "review_mode": True,
            "consensus_strategy": "expert_consensus",
            "timeout_per_round": 45.0,
        },
        "task_types": ["code_review", "analysis"],
        "metadata": {"author": "MAF System", "tags": ["code", "review", "trio"]},
    },
    "creative_quartet": {
        "name": "Creative Quartet",
        "description": "All four providers for maximum creative output",
        "version": "1.0.0",
        "providers": [
            {
                "provider_id": "grok",
                "role": "analyzer",
                "weight": 1.0,
                "capabilities": ["critical_thinking", "research"],
            },
            {
                "provider_id": "claude",
                "role": "synthesizer",
                "weight": 1.2,
                "capabilities": ["creative_writing", "synthesis"],
            },
            {
                "provider_id": "gemini",
                "role": "implementer",
                "weight": 0.9,
                "capabilities": ["text_generation", "creative_writing"],
            },
            {
                "provider_id": "openai",
                "role": "critic",
                "weight": 1.1,
                "capabilities": ["validation", "creative_writing"],
            },
        ],
        "collaboration_settings": {
            "max_rounds": 6,
            "convergence_threshold": 0.5,
            "review_mode": False,
            "consensus_strategy": "weighted_vote",
            "timeout_per_round": 75.0,
        },
        "task_types": ["creative_writing", "problem_solving", "research"],
        "metadata": {"author": "MAF System", "tags": ["creative", "quartet", "maximum"]},
    },
}


def create_default_configs(loader: MAFConfigLoader) -> None:
    """
    Create default MAF configuration files.

    Args:
        loader: MAFConfigLoader instance
    """
    for config_name, config_data in DEFAULT_CONFIGS.items():
        try:
            config = loader._data_to_config(config_data)
            loader.save_config(config, config_name, config_data.get("metadata", {}))
            logger.info(f"Created default config: {config_name}")
        except Exception as e:
            logger.error(f"Failed to create config {config_name}: {e}")


# Global config loader instance
maf_config_loader = MAFConfigLoader()
