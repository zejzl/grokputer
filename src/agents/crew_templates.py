"""
Predefined Crew Configurations and Flow Templates for Grokputer.

Provides ready-to-use CrewAI-inspired setups for common agent orchestration patterns.
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.agents.crew_orchestrator import (
    CrewMember,
    CrewOrchestrator,
    CrewRole,
    FlowExecution,
    FlowState,
    FlowStep,
)
from src.core.base_agent import BaseAgent


class CrewTemplates:
    """Factory for creating predefined Crew configurations."""

    @staticmethod
    def create_task_execution_crew(
        observer: BaseAgent,
        coordinator: BaseAgent,
        validator: BaseAgent,
        executor: BaseAgent,
        analyzer: BaseAgent = None,
        learner: BaseAgent = None,
    ) -> List[CrewMember]:
        """
        Create a standard task execution crew.

        This crew follows the classic CrewAI pattern:
        - Coordinator decomposes tasks
        - Observer provides context
        - Executor performs actions
        - Validator ensures safety
        - Analyzer monitors performance
        - Learner captures patterns
        """
        members = [
            CrewMember(
                agent=coordinator,
                role=CrewRole.COORDINATOR,
                capabilities={"task_decomposition", "planning", "coordination"},
                priority=5,
                max_concurrent_tasks=2,
            ),
            CrewMember(
                agent=observer,
                role=CrewRole.OBSERVER,
                capabilities={"screen_capture", "state_observation", "context_gathering"},
                priority=4,
                max_concurrent_tasks=1,
            ),
            CrewMember(
                agent=validator,
                role=CrewRole.VALIDATOR,
                capabilities={"safety_check", "validation", "risk_assessment"},
                priority=5,
                max_concurrent_tasks=3,
            ),
            CrewMember(
                agent=executor,
                role=CrewRole.EXECUTOR,
                capabilities={"command_execution", "tool_use", "action_performing"},
                priority=4,
                max_concurrent_tasks=2,
            ),
        ]

        if analyzer:
            members.append(
                CrewMember(
                    agent=analyzer,
                    role=CrewRole.ANALYZER,
                    capabilities={"performance_monitoring", "metrics_collection", "health_check"},
                    priority=3,
                    max_concurrent_tasks=1,
                )
            )

        if learner:
            members.append(
                CrewMember(
                    agent=learner,
                    role=CrewRole.LEARNER,
                    capabilities={"pattern_recognition", "learning", "adaptation"},
                    priority=3,
                    max_concurrent_tasks=1,
                )
            )

        return members

    @staticmethod
    def create_research_crew(
        coordinator: BaseAgent, analyzer: BaseAgent, learner: BaseAgent, memory_manager: BaseAgent = None
    ) -> List[CrewMember]:
        """
        Create a research and analysis crew.

        Focuses on information gathering, analysis, and learning patterns.
        """
        members = [
            CrewMember(
                agent=coordinator,
                role=CrewRole.COORDINATOR,
                capabilities={"research_planning", "query_decomposition", "synthesis"},
                priority=5,
                max_concurrent_tasks=2,
            ),
            CrewMember(
                agent=analyzer,
                role=CrewRole.ANALYZER,
                capabilities={"data_analysis", "pattern_analysis", "insights_generation"},
                priority=4,
                max_concurrent_tasks=2,
            ),
            CrewMember(
                agent=learner,
                role=CrewRole.LEARNER,
                capabilities={"knowledge_extraction", "pattern_learning", "model_training"},
                priority=4,
                max_concurrent_tasks=1,
            ),
        ]

        if memory_manager:
            members.append(
                CrewMember(
                    agent=memory_manager,
                    role=CrewRole.MEMORY_MANAGER,
                    capabilities={"memory_retrieval", "context_storage", "knowledge_persistence"},
                    priority=3,
                    max_concurrent_tasks=1,
                )
            )

        return members

    @staticmethod
    def create_development_crew(
        coordinator: BaseAgent, analyzer: BaseAgent, improver: BaseAgent, validator: BaseAgent
    ) -> List[CrewMember]:
        """
        Create a software development crew.

        Specializes in code analysis, improvement, and validation.
        """
        return [
            CrewMember(
                agent=coordinator,
                role=CrewRole.COORDINATOR,
                capabilities={"code_planning", "architecture_design", "task_breakdown"},
                priority=5,
                max_concurrent_tasks=2,
            ),
            CrewMember(
                agent=analyzer,
                role=CrewRole.ANALYZER,
                capabilities={"code_analysis", "bug_detection", "performance_analysis"},
                priority=4,
                max_concurrent_tasks=2,
            ),
            CrewMember(
                agent=improver,
                role=CrewRole.IMPROVER,
                capabilities={"code_optimization", "refactoring", "enhancement"},
                priority=4,
                max_concurrent_tasks=2,
            ),
            CrewMember(
                agent=validator,
                role=CrewRole.VALIDATOR,
                capabilities={"code_review", "testing", "quality_assurance"},
                priority=5,
                max_concurrent_tasks=3,
            ),
        ]


class FlowTemplates:
    """Factory for creating predefined Flow templates."""

    @staticmethod
    def create_task_execution_flow() -> List[FlowStep]:
        """
        Create a standard task execution flow.

        Follows CrewAI's sequential dependency pattern with validation gates.
        """
        return [
            FlowStep(
                step_id="observe_initial_state",
                description="Capture initial system state and context",
                required_role=CrewRole.OBSERVER,
                task_type="screen_capture",
                timeout=30.0,
            ),
            FlowStep(
                step_id="decompose_task",
                description="Break down the task into executable steps",
                required_role=CrewRole.COORDINATOR,
                task_type="task_decomposition",
                timeout=60.0,
            ),
            FlowStep(
                step_id="validate_plan",
                description="Validate the execution plan for safety and feasibility",
                required_role=CrewRole.VALIDATOR,
                task_type="safety_check",
                dependencies=["decompose_task"],
                timeout=45.0,
            ),
            FlowStep(
                step_id="execute_actions",
                description="Execute the planned actions",
                required_role=CrewRole.EXECUTOR,
                task_type="command_execution",
                dependencies=["validate_plan"],
                timeout=300.0,  # 5 minutes
            ),
            FlowStep(
                step_id="observe_results",
                description="Observe and capture execution results",
                required_role=CrewRole.OBSERVER,
                task_type="state_observation",
                dependencies=["execute_actions"],
                timeout=30.0,
            ),
            FlowStep(
                step_id="validate_outcome",
                description="Validate that the task was completed successfully",
                required_role=CrewRole.VALIDATOR,
                task_type="validation",
                dependencies=["observe_results"],
                timeout=45.0,
            ),
            FlowStep(
                step_id="analyze_performance",
                description="Analyze execution performance and collect metrics",
                required_role=CrewRole.ANALYZER,
                task_type="performance_monitoring",
                dependencies=["validate_outcome"],
                timeout=30.0,
            ),
            FlowStep(
                step_id="learn_patterns",
                description="Learn from execution patterns for future improvement",
                required_role=CrewRole.LEARNER,
                task_type="pattern_recognition",
                dependencies=["analyze_performance"],
                timeout=60.0,
            ),
        ]

    @staticmethod
    def create_research_flow() -> List[FlowStep]:
        """
        Create a research and analysis flow.

        Parallel processing with synthesis at the end.
        """
        return [
            FlowStep(
                step_id="define_research_scope",
                description="Define the scope and objectives of the research",
                required_role=CrewRole.COORDINATOR,
                task_type="research_planning",
                timeout=60.0,
            ),
            FlowStep(
                step_id="gather_information",
                description="Gather relevant information and data",
                required_role=CrewRole.ANALYZER,
                task_type="data_analysis",
                dependencies=["define_research_scope"],
                timeout=180.0,  # 3 minutes
            ),
            FlowStep(
                step_id="analyze_patterns",
                description="Analyze patterns and extract insights",
                required_role=CrewRole.ANALYZER,
                task_type="pattern_analysis",
                dependencies=["gather_information"],
                timeout=120.0,
            ),
            FlowStep(
                step_id="extract_knowledge",
                description="Extract and store new knowledge patterns",
                required_role=CrewRole.LEARNER,
                task_type="knowledge_extraction",
                dependencies=["analyze_patterns"],
                timeout=90.0,
            ),
            FlowStep(
                step_id="synthesize_findings",
                description="Synthesize all findings into comprehensive results",
                required_role=CrewRole.COORDINATOR,
                task_type="synthesis",
                dependencies=["extract_knowledge"],
                timeout=120.0,
            ),
        ]

    @staticmethod
    def create_code_review_flow() -> List[FlowStep]:
        """
        Create a code review and improvement flow.

        Sequential analysis with improvement suggestions.
        """
        return [
            FlowStep(
                step_id="analyze_codebase",
                description="Perform comprehensive code analysis",
                required_role=CrewRole.ANALYZER,
                task_type="code_analysis",
                timeout=120.0,
            ),
            FlowStep(
                step_id="identify_issues",
                description="Identify bugs, vulnerabilities, and improvement opportunities",
                required_role=CrewRole.ANALYZER,
                task_type="bug_detection",
                dependencies=["analyze_codebase"],
                timeout=90.0,
            ),
            FlowStep(
                step_id="review_code_quality",
                description="Review code quality and adherence to standards",
                required_role=CrewRole.VALIDATOR,
                task_type="code_review",
                dependencies=["identify_issues"],
                timeout=60.0,
            ),
            FlowStep(
                step_id="suggest_improvements",
                description="Suggest specific improvements and optimizations",
                required_role=CrewRole.IMPROVER,
                task_type="code_optimization",
                dependencies=["review_code_quality"],
                timeout=90.0,
            ),
            FlowStep(
                step_id="validate_improvements",
                description="Validate that improvements maintain functionality",
                required_role=CrewRole.VALIDATOR,
                task_type="testing",
                dependencies=["suggest_improvements"],
                timeout=120.0,
            ),
        ]


class CrewManager:
    """
    High-level manager for Crew operations.

    Provides easy setup and execution of predefined Crew configurations.
    """

    def __init__(self, orchestrator: CrewOrchestrator):
        self.orchestrator = orchestrator
        self.templates = CrewTemplates()
        self.flow_templates = FlowTemplates()

    def setup_standard_task_crew(
        self,
        crew_id: str,
        observer: BaseAgent,
        coordinator: BaseAgent,
        validator: BaseAgent,
        executor: BaseAgent,
        analyzer: BaseAgent = None,
        learner: BaseAgent = None,
    ) -> str:
        """Set up a standard task execution crew."""
        members = self.templates.create_task_execution_crew(
            observer, coordinator, validator, executor, analyzer, learner
        )
        self.orchestrator.create_crew(crew_id, members)

        # Set up the standard task execution flow
        flow_steps = self.flow_templates.create_task_execution_flow()
        flow_id = f"{crew_id}_task_execution"
        self.orchestrator.define_flow(flow_id, flow_steps)

        return flow_id

    def setup_research_crew(
        self,
        crew_id: str,
        coordinator: BaseAgent,
        analyzer: BaseAgent,
        learner: BaseAgent,
        memory_manager: BaseAgent = None,
    ) -> str:
        """Set up a research and analysis crew."""
        members = self.templates.create_research_crew(coordinator, analyzer, learner, memory_manager)
        self.orchestrator.create_crew(crew_id, members)

        # Set up the research flow
        flow_steps = self.flow_templates.create_research_flow()
        flow_id = f"{crew_id}_research"
        self.orchestrator.define_flow(flow_id, flow_steps)

        return flow_id

    def setup_development_crew(
        self, crew_id: str, coordinator: BaseAgent, analyzer: BaseAgent, improver: BaseAgent, validator: BaseAgent
    ) -> str:
        """Set up a software development crew."""
        members = self.templates.create_development_crew(coordinator, analyzer, improver, validator)
        self.orchestrator.create_crew(crew_id, members)

        # Set up the code review flow
        flow_steps = self.flow_templates.create_code_review_flow()
        flow_id = f"{crew_id}_code_review"
        self.orchestrator.define_flow(flow_id, flow_steps)

        return flow_id

    async def execute_task_flow(
        self, crew_id: str, task_description: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute a complete task using the appropriate crew and flow.

        Automatically selects the best crew for the task type.
        """
        # Determine task type and select appropriate flow
        task_type = self._classify_task(task_description)
        flow_id = f"{crew_id}_{task_type}"

        if flow_id not in self.orchestrator.active_flows:
            # Try to find a suitable existing flow
            available_flows = [fid for fid in self.orchestrator.active_flows.keys() if fid.startswith(crew_id)]
            if available_flows:
                flow_id = available_flows[0]  # Use first available flow
            else:
                raise ValueError(f"No suitable flow found for crew '{crew_id}' and task type '{task_type}'")

        # Execute the flow
        execution_context = {"task_description": task_description, "task_type": task_type, **(context or {})}

        return await self.orchestrator.execute_flow(crew_id, flow_id, execution_context)

    def _classify_task(self, task_description: str) -> str:
        """Classify task type based on description."""
        description_lower = task_description.lower()

        if any(keyword in description_lower for keyword in ["execute", "run", "perform", "action"]):
            return "task_execution"
        elif any(keyword in description_lower for keyword in ["analyze", "research", "study", "investigate"]):
            return "research"
        elif any(keyword in description_lower for keyword in ["code", "programming", "develop", "implement"]):
            return "code_review"
        else:
            return "task_execution"
