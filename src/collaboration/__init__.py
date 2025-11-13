"""
Collaboration module for multi-agent coordination via MessageBus.
"""

from src.collaboration.message_models import MessageType, AgentRole, CollaborationMessage, ConsensusSignal, FinalPlan

# MAF (Multi-Agent Framework) components - optional imports
try:
    from src.collaboration.provider_registry import (
        ProviderCapability,
        ProviderMetadata,
        ProviderInstance,
        ProviderRegistry,
        provider_registry,
        initialize_default_providers,
        initialize_mock_providers,
    )

    from src.collaboration.provider_pool import (
        PoolStrategy,
        PoolConfig,
        ConnectionInfo,
        ProviderPoolStats,
        CircuitBreaker,
        ProviderPool,
        provider_pool,
    )

    from src.collaboration.multi_provider_coordinator import (
        ProviderRole,
        CollaborationConfig,
        MultiProviderCoordinator,
        CollaborationCoordinator,
    )

    from src.collaboration.orchestrator import (
        OrchestrationStrategy,
        OrchestrationConfig,
        RoleAssignment,
        Orchestrator,
        orchestrator,
    )

    from src.collaboration.config import (
        MAF_CONFIG_SCHEMA,
        MAFConfigLoader,
        maf_config_loader,
        create_default_configs,
        DEFAULT_CONFIGS,
    )

    from src.collaboration.maf_messagebus_integration import (
        MAFMessageBusAdapter,
        MAFMessageBusCoordinator,
        initialize_maf_messagebus_integration,
        maf_messagebus_coordinator,
    )

    MAF_AVAILABLE = True
except (ImportError, SyntaxError) as e:
    # MAF components not available due to syntax errors or missing dependencies
    MAF_AVAILABLE = False
    ProviderCapability = None
    ProviderMetadata = None
    ProviderInstance = None
    ProviderRegistry = None
    provider_registry = None
    initialize_default_providers = None
    PoolStrategy = None
    PoolConfig = None
    ConnectionInfo = None
    ProviderPoolStats = None
    CircuitBreaker = None
    ProviderPool = None
    provider_pool = None
    ProviderRole = None
    CollaborationConfig = None
    MultiProviderCoordinator = None
    CollaborationCoordinator = None
    OrchestrationStrategy = None
    OrchestrationConfig = None
    RoleAssignment = None
    Orchestrator = None
    orchestrator = None
    MAF_CONFIG_SCHEMA = None
    MAFConfigLoader = None
    maf_config_loader = None
    create_default_configs = None
    DEFAULT_CONFIGS = None

__all__ = [
    # Original message models
    "MessageType",
    "AgentRole",
    "CollaborationMessage",
    "ConsensusSignal",
    "FinalPlan",
    # MAF availability flag
    "MAF_AVAILABLE",
]

# Add MAF components if available
if MAF_AVAILABLE:
    __all__.extend(
        [
            # MAF Provider Registry
            "ProviderCapability",
            "ProviderMetadata",
            "ProviderInstance",
            "ProviderRegistry",
            "provider_registry",
            "initialize_default_providers",
            "initialize_mock_providers",
            # MAF Provider Pool
            "PoolStrategy",
            "PoolConfig",
            "ConnectionInfo",
            "ProviderPoolStats",
            "CircuitBreaker",
            "ProviderPool",
            "provider_pool",
            # MAF Coordinator
            "ProviderRole",
            "CollaborationConfig",
            "MultiProviderCoordinator",
            "CollaborationCoordinator",
            # MAF Orchestrator
            "OrchestrationStrategy",
            "OrchestrationConfig",
            "RoleAssignment",
            "Orchestrator",
            "orchestrator",
            # MAF Configuration
            "MAF_CONFIG_SCHEMA",
            "MAFConfigLoader",
            "maf_config_loader",
            "create_default_configs",
            "DEFAULT_CONFIGS",
            # MAF-MessageBus Integration
            "MAFMessageBusAdapter",
            "MAFMessageBusCoordinator",
            "initialize_maf_messagebus_integration",
            "maf_messagebus_coordinator",
        ]
    )
