"""
Provider Registry for Multi-Agent Framework (MAF)

Dynamic provider loading and capability management system for multi-provider AI collaboration.
Supports registration, discovery, and capability-based provider selection.
"""

import logging
from typing import Dict, List, Any, Optional, Type, Callable
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import time

logger = logging.getLogger(__name__)


class ProviderCapability(Enum):
    """Provider capabilities for role assignment."""

    TEXT_GENERATION = "text_generation"
    CODE_ANALYSIS = "code_analysis"
    CRITICAL_THINKING = "critical_thinking"
    CREATIVE_WRITING = "creative_writing"
    MATHEMATICAL = "mathematical"
    RESEARCH = "research"
    VALIDATION = "validation"
    SYNTHESIS = "synthesis"


@dataclass
class ProviderMetadata:
    """Metadata for AI provider capabilities and characteristics."""

    name: str
    provider_type: str
    model: str
    capabilities: List[ProviderCapability] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    cost_per_token: float = 0.0
    max_tokens: int = 4096
    response_time_ms: int = 1000
    reliability_score: float = 0.9  # 0.0 to 1.0
    last_health_check: float = field(default_factory=time.time)
    health_status: str = "unknown"  # healthy, degraded, failed


@dataclass
class ProviderInstance:
    """Runtime instance of a provider with client and metadata."""

    metadata: ProviderMetadata
    client: Any  # The actual model client instance
    weight: float = 1.0  # Voting weight in consensus
    is_active: bool = True


class ProviderRegistry:
    """
    Central registry for AI providers in the MAF system.

    Manages provider registration, discovery, health monitoring, and capability-based selection.
    """

    def __init__(self):
        self._providers: Dict[str, ProviderInstance] = {}
        self._capability_index: Dict[ProviderCapability, List[str]] = {}
        self._health_check_interval = 60  # seconds
        self._health_monitor_task: Optional[asyncio.Task] = None

    async def start_health_monitoring(self):
        """Start background health monitoring for all providers."""
        if self._health_monitor_task and not self._health_monitor_task.done():
            return

        self._health_monitor_task = asyncio.create_task(self._health_monitor_loop())
        logger.info("Started provider health monitoring")

    async def stop_health_monitoring(self):
        """Stop background health monitoring."""
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped provider health monitoring")

    async def _health_monitor_loop(self):
        """Background task for periodic health checks."""
        while True:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self._health_check_interval)

    async def _perform_health_checks(self):
        """Perform health checks on all registered providers."""
        for provider_id, instance in self._providers.items():
            try:
                # Simple health check - try to get available models
                if hasattr(instance.client, "get_available_models"):
                    await instance.client.get_available_models()
                    instance.metadata.health_status = "healthy"
                else:
                    # For providers without model listing, assume healthy
                    instance.metadata.health_status = "healthy"

                instance.metadata.last_health_check = time.time()
                logger.debug(f"Provider {provider_id} health check: {instance.metadata.health_status}")

            except Exception as e:
                instance.metadata.health_status = "failed"
                instance.metadata.last_health_check = time.time()
                logger.warning(f"Provider {provider_id} health check failed: {e}")

    def register_provider(self, provider_id: str, client: Any, metadata: ProviderMetadata, weight: float = 1.0) -> bool:
        """
        Register a new provider instance.

        Args:
            provider_id: Unique identifier for the provider
            client: The model client instance
            metadata: Provider capabilities and characteristics
            weight: Voting weight for consensus (default 1.0)

        Returns:
            True if registration successful, False if provider_id already exists
        """
        if provider_id in self._providers:
            logger.warning(f"Provider {provider_id} already registered, skipping")
            return False

        instance = ProviderInstance(metadata=metadata, client=client, weight=weight, is_active=True)

        self._providers[provider_id] = instance

        # Update capability index
        for capability in metadata.capabilities:
            if capability not in self._capability_index:
                self._capability_index[capability] = []
            self._capability_index[capability].append(provider_id)

        logger.info(f"Registered provider: {provider_id} ({metadata.provider_type}:{metadata.model})")
        return True

    def unregister_provider(self, provider_id: str) -> bool:
        """
        Unregister a provider.

        Args:
            provider_id: Provider to remove

        Returns:
            True if successfully removed, False if not found
        """
        if provider_id not in self._providers:
            return False

        instance = self._providers[provider_id]

        # Remove from capability index
        for capability in instance.metadata.capabilities:
            if capability in self._capability_index:
                self._capability_index[capability] = [
                    pid for pid in self._capability_index[capability] if pid != provider_id
                ]
                if not self._capability_index[capability]:
                    del self._capability_index[capability]

        del self._providers[provider_id]
        logger.info(f"Unregistered provider: {provider_id}")
        return True

    def get_provider(self, provider_id: str) -> Optional[ProviderInstance]:
        """Get a provider instance by ID."""
        return self._providers.get(provider_id)

    def get_providers_by_capability(
        self, capability: ProviderCapability, only_healthy: bool = True
    ) -> List[ProviderInstance]:
        """
        Get providers that have a specific capability.

        Args:
            capability: Required capability
            only_healthy: Only return healthy providers

        Returns:
            List of matching provider instances
        """
        provider_ids = self._capability_index.get(capability, [])
        providers = []

        for pid in provider_ids:
            instance = self._providers.get(pid)
            if instance and instance.is_active:
                if not only_healthy or instance.metadata.health_status == "healthy":
                    providers.append(instance)

        return providers

    def get_all_providers(self, only_healthy: bool = True, only_active: bool = True) -> List[ProviderInstance]:
        """Get all registered providers with optional filtering."""
        providers = []
        for instance in self._providers.values():
            if only_active and not instance.is_active:
                continue
            if only_healthy and instance.metadata.health_status != "healthy":
                continue
            providers.append(instance)
        return providers

    def select_providers_for_task(
        self, required_capabilities: List[ProviderCapability], min_providers: int = 1, max_providers: int = 5
    ) -> List[ProviderInstance]:
        """
        Select optimal providers for a task based on capabilities and health.

        Args:
            required_capabilities: Capabilities needed for the task
            min_providers: Minimum number of providers to select
            max_providers: Maximum number of providers to select

        Returns:
            Selected provider instances, ordered by suitability
        """
        candidates = []

        # Find providers with required capabilities
        for capability in required_capabilities:
            providers = self.get_providers_by_capability(capability, only_healthy=True)
            for provider in providers:
                if provider not in candidates:
                    candidates.append(provider)

        if len(candidates) < min_providers:
            logger.warning(f"Only found {len(candidates)} providers, need at least {min_providers}")
            # Return what we have, even if unhealthy
            candidates = []
            for capability in required_capabilities:
                providers = self.get_providers_by_capability(capability, only_healthy=False)
                for provider in providers:
                    if provider not in candidates:
                        candidates.append(provider)

        # Sort by reliability and weight
        candidates.sort(key=lambda p: (p.metadata.reliability_score * p.weight), reverse=True)

        return candidates[:max_providers]

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the provider registry."""
        total_providers = len(self._providers)
        healthy_providers = len([p for p in self._providers.values() if p.metadata.health_status == "healthy"])
        active_providers = len([p for p in self._providers.values() if p.is_active])

        capability_counts = {}
        for capability, providers in self._capability_index.items():
            capability_counts[capability.value] = len(providers)

        return {
            "total_providers": total_providers,
            "healthy_providers": healthy_providers,
            "active_providers": active_providers,
            "capability_distribution": capability_counts,
            "health_monitoring_active": self._health_monitor_task is not None,
        }


# Global registry instance
provider_registry = ProviderRegistry()


async def initialize_default_providers():
    """
    Initialize the registry with default providers from configuration.
    This would be called during system startup.
    """
    logger.info("Initializing default providers...")
    # TODO: Implement provider initialization
    pass


class MockProviderClient:
    """
    Mock provider client for testing MAF functionality without API keys.
    Returns predefined responses based on provider type and role.
    """

    def __init__(self, provider_type: str, model: str):
        self.provider_type = provider_type
        self.model = model

    async def generate_response(self, prompt: str, role: str = "general") -> str:
        """
        Generate a mock response based on the provider type and role.

        Args:
            prompt: The input prompt
            role: The role this provider is playing (analyzer, critic, etc.)

        Returns:
            Mock response string
        """
        # Base responses by role
        role_responses = {
            "analyzer": f"As an analyzer using {self.provider_type} ({self.model}), I break down the task: {prompt[:100]}... Key components identified: structure, requirements, constraints.",
            "critic": f"As a critic using {self.provider_type} ({self.model}), I evaluate: {prompt[:100]}... Potential issues: edge cases, scalability, error handling.",
            "synthesizer": f"As a synthesizer using {self.provider_type} ({self.model}), I combine perspectives: {prompt[:100]}... Unified approach: integrate analysis with critical evaluation.",
            "validator": f"As a validator using {self.provider_type} ({self.model}), I verify: {prompt[:100]}... Validation results: requirements met, best practices followed.",
            "researcher": f"As a researcher using {self.provider_type} ({self.model}), I investigate: {prompt[:100]}... Research findings: related work, current trends, recommendations.",
            "implementer": f"As an implementer using {self.provider_type} ({self.model}), I plan execution: {prompt[:100]}... Implementation steps: design, development, testing, deployment.",
        }

        response = role_responses.get(role, f"As {self.provider_type} ({self.model}), I respond to: {prompt[:100]}...")

        # Add some variety based on provider type
        if self.provider_type == "grok":
            response += " My unique perspective comes from xAI's training on diverse internet data."
        elif self.provider_type == "claude":
            response += " I focus on being helpful, harmless, and honest in my analysis."
        elif self.provider_type == "gemini":
            response += " I leverage multimodal capabilities for comprehensive understanding."
        elif self.provider_type == "openai":
            response += " I provide balanced, well-reasoned responses based on extensive training."

        return response


async def initialize_mock_providers():
    """
    Initialize the registry with mock providers for testing.
    Creates mock instances of all supported providers without requiring API keys.
    """
    logger.info("Initializing mock providers for testing...")

    # Mock provider configurations
    mock_configs = [
        {
            "id": "grok",
            "type": "grok",
            "model": "grok-4-fast-reasoning",
            "capabilities": [
                ProviderCapability.TEXT_GENERATION,
                ProviderCapability.CRITICAL_THINKING,
                ProviderCapability.RESEARCH,
                ProviderCapability.CODE_ANALYSIS,
            ],
            "strengths": ["Creative problem solving", "Real-time knowledge", "Humor and wit"],
            "weaknesses": ["Limited training data cutoff", "Can be verbose"],
            "cost_per_token": 0.0,  # Free for mock
            "max_tokens": 8192,
            "response_time_ms": 800,
            "reliability_score": 0.95,
        },
        {
            "id": "claude",
            "type": "claude",
            "model": "claude-3-5-sonnet",
            "capabilities": [
                ProviderCapability.TEXT_GENERATION,
                ProviderCapability.VALIDATION,
                ProviderCapability.CREATIVE_WRITING,
                ProviderCapability.CODE_ANALYSIS,
            ],
            "strengths": ["Safety and ethics", "Long context understanding", "Structured reasoning"],
            "weaknesses": ["Can be overly cautious", "Slower response times"],
            "cost_per_token": 0.0,
            "max_tokens": 4096,
            "response_time_ms": 1200,
            "reliability_score": 0.98,
        },
        {
            "id": "gemini",
            "type": "gemini",
            "model": "gemini-1.5-pro",
            "capabilities": [
                ProviderCapability.TEXT_GENERATION,
                ProviderCapability.RESEARCH,
                ProviderCapability.MATHEMATICAL,
                ProviderCapability.SYNTHESIS,
            ],
            "strengths": ["Multimodal capabilities", "Fast responses", "Strong in math/science"],
            "weaknesses": ["Less creative writing", "Can be inconsistent"],
            "cost_per_token": 0.0,
            "max_tokens": 32768,
            "response_time_ms": 600,
            "reliability_score": 0.92,
        },
        {
            "id": "openai",
            "type": "openai",
            "model": "gpt-4o",
            "capabilities": [
                ProviderCapability.TEXT_GENERATION,
                ProviderCapability.CREATIVE_WRITING,
                ProviderCapability.CRITICAL_THINKING,
                ProviderCapability.CODE_ANALYSIS,
            ],
            "strengths": ["Versatile", "High quality output", "Good at following instructions"],
            "weaknesses": ["Expensive", "Less innovative", "Training data biases"],
            "cost_per_token": 0.0,
            "max_tokens": 8192,
            "response_time_ms": 1000,
            "reliability_score": 0.96,
        },
    ]

    # Register each mock provider
    for config in mock_configs:
        client = MockProviderClient(config["type"], config["model"])

        metadata = ProviderMetadata(
            name=f"{config['type'].title()} Mock",
            provider_type=config["type"],
            model=config["model"],
            capabilities=config["capabilities"],
            strengths=config["strengths"],
            weaknesses=config["weaknesses"],
            cost_per_token=config["cost_per_token"],
            max_tokens=config["max_tokens"],
            response_time_ms=config["response_time_ms"],
            reliability_score=config["reliability_score"],
            health_status="healthy",
        )

        success = provider_registry.register_provider(
            provider_id=config["id"], client=client, metadata=metadata, weight=1.0
        )

        if success:
            logger.info(f"Registered mock provider: {config['id']}")
        else:
            logger.warning(f"Failed to register mock provider: {config['id']}")

    logger.info(f"Mock provider initialization complete. Registered {len(mock_configs)} providers.")
