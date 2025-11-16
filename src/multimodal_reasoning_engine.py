"""
Multi-Modal Reasoning Engine for Grokputer.

Advanced reasoning system that combines vision, text, audio, and context
for intelligent decision making and action planning.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from .multimodal_processor import (
    MultiModalAnalysis,
    MultiModalInput,
    MultiModalProcessor,
)
from .ui_understanding import UIUnderstanding, UIUnderstandingModule

logger = logging.getLogger(__name__)


@dataclass
class ReasoningContext:
    """Context information for reasoning."""

    user_intent: str = ""
    task_objective: str = ""
    environmental_factors: Dict[str, Any] = field(default_factory=dict)
    historical_actions: List[Dict[str, Any]] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class ReasoningStep:
    """A step in the reasoning process."""

    step_type: str
    description: str
    input_data: Dict[str, Any]
    reasoning: str
    confidence: float
    output: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class Decision:
    """A decision made by the reasoning engine."""

    action: str
    parameters: Dict[str, Any]
    justification: str
    confidence: float
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    expected_outcomes: List[str] = field(default_factory=list)


@dataclass
class ReasoningResult:
    """Complete reasoning result."""

    context: ReasoningContext
    analysis: MultiModalAnalysis
    reasoning_steps: List[ReasoningStep] = field(default_factory=list)
    final_decision: Optional[Decision] = None
    confidence_score: float = 0.0
    reasoning_time: float = 0.0


class MultiModalReasoningEngine:
    """
    Advanced multi-modal reasoning engine for intelligent decision making.

    Combines multi-modal analysis with contextual reasoning to make informed decisions
    and plan actions based on visual, textual, and auditory information.
    """

    def __init__(self):
        self.multimodal_processor = MultiModalProcessor()
        self.ui_understanding = UIUnderstandingModule()
        self.reasoning_strategies = self._initialize_reasoning_strategies()

    def _initialize_reasoning_strategies(self) -> Dict[str, callable]:
        """Initialize different reasoning strategies."""
        return {
            "ui_interaction": self._reason_ui_interaction,
            "content_analysis": self._reason_content_analysis,
            "safety_assessment": self._reason_safety_assessment,
            "task_execution": self._reason_task_execution,
            "error_handling": self._reason_error_handling,
            "learning_opportunity": self._reason_learning_opportunity,
        }

    async def reason_and_decide(self, input_data: MultiModalInput, context: ReasoningContext) -> ReasoningResult:
        """
        Perform multi-modal reasoning and make a decision.

        Args:
            input_data: Multi-modal input data
            context: Reasoning context

        Returns:
            ReasoningResult with analysis, reasoning steps, and decision
        """
        start_time = datetime.now().timestamp()
        result = ReasoningResult(context=context)

        try:
            # Step 1: Multi-modal analysis
            analysis_step = await self._perform_multimodal_analysis(input_data)
            result.analysis = analysis_step.output["analysis"]
            result.reasoning_steps.append(analysis_step)

            # Step 2: Context integration
            context_step = self._integrate_context(result.analysis, context)
            result.reasoning_steps.append(context_step)

            # Step 3: Situation assessment
            situation_step = self._assess_situation(result.analysis, context)
            result.reasoning_steps.append(situation_step)

            # Step 4: Strategy selection
            strategy_step = self._select_reasoning_strategy(result.analysis, context)
            result.reasoning_steps.append(strategy_step)

            # Step 5: Apply reasoning strategy
            strategy_name = strategy_step.output.get("strategy", "content_analysis")
            if strategy_name in self.reasoning_strategies:
                decision_step = await self.reasoning_strategies[strategy_name](
                    result.analysis, context, result.reasoning_steps
                )
                result.reasoning_steps.append(decision_step)
                result.final_decision = decision_step.output.get("decision")

            # Step 6: Confidence assessment
            confidence_step = self._assess_reasoning_confidence(result)
            result.reasoning_steps.append(confidence_step)
            result.confidence_score = confidence_step.output.get("confidence", 0.0)

        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            # Create error handling decision
            result.final_decision = Decision(
                action="error_handling",
                parameters={"error": str(e)},
                justification="Reasoning process encountered an error",
                confidence=0.1,
                risks=["Unknown system state"],
                expected_outcomes=["Error logged and handled gracefully"],
            )

        finally:
            result.reasoning_time = datetime.now().timestamp() - start_time

        return result

    async def _perform_multimodal_analysis(self, input_data: MultiModalInput) -> ReasoningStep:
        """Step 1: Perform comprehensive multi-modal analysis."""
        analysis = await self.multimodal_processor.process_multimodal_input(input_data)

        # If screenshot, also perform UI understanding
        ui_understanding = None
        if input_data.image_path and self._is_screenshot(input_data):
            ui_understanding = await self.ui_understanding.understand_ui(input_data.image_path)

        return ReasoningStep(
            step_type="multimodal_analysis",
            description="Analyzed input across all available modalities",
            input_data={"input_data": input_data},
            reasoning="Processed text, visual, and audio data to extract features and cross-modal insights",
            confidence=analysis.confidence_score,
            output={"analysis": analysis, "ui_understanding": ui_understanding},
        )

    def _integrate_context(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> ReasoningStep:
        """Step 2: Integrate contextual information."""
        context_relevance = self._calculate_context_relevance(analysis, context)

        reasoning = f"Integrated context with {context_relevance:.1%} relevance. "
        reasoning += f"User intent: {context.user_intent or 'not specified'}. "
        reasoning += f"Task objective: {context.task_objective or 'not specified'}."

        return ReasoningStep(
            step_type="context_integration",
            description="Integrated contextual information with analysis",
            input_data={"context": context},
            reasoning=reasoning,
            confidence=context_relevance,
            output={
                "context_relevance": context_relevance,
                "integrated_factors": self._extract_relevant_context_factors(analysis, context),
            },
        )

    def _assess_situation(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> ReasoningStep:
        """Step 3: Assess the current situation."""
        situation_type = self._classify_situation(analysis, context)
        urgency_level = self._assess_urgency(analysis, context)
        complexity_level = self._assess_complexity(analysis)

        reasoning = f"Situation classified as: {situation_type}. "
        reasoning += f"Urgency level: {urgency_level}/10. "
        reasoning += f"Complexity level: {complexity_level}/10."

        return ReasoningStep(
            step_type="situation_assessment",
            description="Assessed current situation and environmental factors",
            input_data={"analysis": analysis, "context": context},
            reasoning=reasoning,
            confidence=0.8,
            output={
                "situation_type": situation_type,
                "urgency_level": urgency_level,
                "complexity_level": complexity_level,
                "key_factors": self._extract_situation_factors(analysis, context),
            },
        )

    def _select_reasoning_strategy(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> ReasoningStep:
        """Step 4: Select appropriate reasoning strategy."""
        strategy = "content_analysis"  # Default

        # UI interaction strategy
        if analysis.visual_analysis and self._is_ui_interaction_scenario(analysis, context):
            strategy = "ui_interaction"

        # Safety assessment strategy
        elif self._requires_safety_assessment(analysis, context):
            strategy = "safety_assessment"

        # Task execution strategy
        elif context.task_objective and self._is_task_execution_scenario(analysis, context):
            strategy = "task_execution"

        # Error handling strategy
        elif self._detects_error_condition(analysis):
            strategy = "error_handling"

        # Learning opportunity
        elif self._is_learning_opportunity(analysis, context):
            strategy = "learning_opportunity"

        return ReasoningStep(
            step_type="strategy_selection",
            description="Selected reasoning strategy based on situation analysis",
            input_data={"analysis": analysis, "context": context},
            reasoning=f"Selected '{strategy}' strategy based on input characteristics and context",
            confidence=0.9,
            output={"strategy": strategy},
        )

    async def _reason_ui_interaction(
        self, analysis: MultiModalAnalysis, context: ReasoningContext, previous_steps: List[ReasoningStep]
    ) -> ReasoningStep:
        """Reasoning strategy for UI interaction scenarios."""
        # Get UI understanding if available
        ui_understanding = None
        for step in previous_steps:
            if step.step_type == "multimodal_analysis":
                ui_understanding = step.output.get("ui_understanding")
                break

        if not ui_understanding:
            # Perform UI understanding
            if analysis.input_data.image_path:
                ui_understanding = await self.ui_understanding.understand_ui(analysis.input_data.image_path)

        decision = await self._decide_ui_action(ui_understanding, analysis, context)

        return ReasoningStep(
            step_type="ui_interaction_reasoning",
            description="Reasoned about UI interaction possibilities",
            input_data={"ui_understanding": ui_understanding, "context": context},
            reasoning="Analyzed UI elements, user intent, and interaction possibilities to determine optimal action",
            confidence=decision.confidence if decision else 0.5,
            output={"decision": decision},
        )

    async def _reason_content_analysis(
        self, analysis: MultiModalAnalysis, context: ReasoningContext, previous_steps: List[ReasoningStep]
    ) -> ReasoningStep:
        """Reasoning strategy for content analysis scenarios."""
        content_type = self._classify_content(analysis)
        analysis_depth = self._determine_analysis_depth(analysis, context)

        decision = Decision(
            action="analyze_content",
            parameters={
                "content_type": content_type,
                "analysis_depth": analysis_depth,
                "focus_areas": self._identify_content_focus_areas(analysis),
            },
            justification=f"Content identified as {content_type}, requiring {analysis_depth} analysis",
            confidence=0.8,
            expected_outcomes=["Content insights extracted", "Knowledge base updated"],
        )

        return ReasoningStep(
            step_type="content_analysis_reasoning",
            description="Reasoned about content analysis approach",
            input_data={"analysis": analysis, "context": context},
            reasoning=f"Classified content and determined analysis strategy based on available modalities",
            confidence=0.8,
            output={"decision": decision},
        )

    async def _reason_safety_assessment(
        self, analysis: MultiModalAnalysis, context: ReasoningContext, previous_steps: List[ReasoningStep]
    ) -> ReasoningStep:
        """Reasoning strategy for safety assessment."""
        safety_concerns = self._identify_safety_concerns(analysis, context)
        risk_level = self._assess_risk_level(safety_concerns)

        action = "proceed_safely" if risk_level < 0.7 else "halt_and_assess"

        decision = Decision(
            action=action,
            parameters={"safety_concerns": safety_concerns, "risk_level": risk_level},
            justification=f"Safety assessment identified {len(safety_concerns)} concerns with risk level {risk_level:.1f}",
            confidence=0.9,
            risks=safety_concerns,
            expected_outcomes=(
                ["Safe operation maintained"] if action == "proceed_safely" else ["Risk mitigation implemented"]
            ),
        )

        return ReasoningStep(
            step_type="safety_assessment_reasoning",
            description="Assessed safety implications of the situation",
            input_data={"analysis": analysis, "context": context},
            reasoning="Evaluated potential safety risks and determined appropriate action",
            confidence=0.9,
            output={"decision": decision},
        )

    async def _reason_task_execution(
        self, analysis: MultiModalAnalysis, context: ReasoningContext, previous_steps: List[ReasoningStep]
    ) -> ReasoningStep:
        """Reasoning strategy for task execution scenarios."""
        task_progress = self._assess_task_progress(analysis, context)
        next_steps = self._identify_next_task_steps(analysis, context, task_progress)

        decision = Decision(
            action="execute_task_step",
            parameters={
                "task_progress": task_progress,
                "next_steps": next_steps,
                "required_resources": self._identify_required_resources(analysis, next_steps),
            },
            justification=f"Task {task_progress:.1%} complete, identified {len(next_steps)} next steps",
            confidence=0.8,
            expected_outcomes=[f"Task step '{step}' completed" for step in next_steps[:3]],
        )

        return ReasoningStep(
            step_type="task_execution_reasoning",
            description="Reasoned about task execution strategy",
            input_data={"analysis": analysis, "context": context},
            reasoning="Assessed task progress and planned next execution steps",
            confidence=0.8,
            output={"decision": decision},
        )

    async def _reason_error_handling(
        self, analysis: MultiModalAnalysis, context: ReasoningContext, previous_steps: List[ReasoningStep]
    ) -> ReasoningStep:
        """Reasoning strategy for error handling."""
        error_type = self._classify_error(analysis)
        recovery_strategy = self._determine_recovery_strategy(error_type, context)

        decision = Decision(
            action="handle_error",
            parameters={
                "error_type": error_type,
                "recovery_strategy": recovery_strategy,
                "error_context": self._extract_error_context(analysis),
            },
            justification=f"Error classified as {error_type}, implementing {recovery_strategy} recovery",
            confidence=0.7,
            risks=["Recovery may not succeed", "Data loss possible"],
            expected_outcomes=["Error condition resolved", "System stability restored"],
        )

        return ReasoningStep(
            step_type="error_handling_reasoning",
            description="Reasoned about error handling approach",
            input_data={"analysis": analysis, "context": context},
            reasoning="Analyzed error condition and determined recovery strategy",
            confidence=0.7,
            output={"decision": decision},
        )

    async def _reason_learning_opportunity(
        self, analysis: MultiModalAnalysis, context: ReasoningContext, previous_steps: List[ReasoningStep]
    ) -> ReasoningStep:
        """Reasoning strategy for learning opportunities."""
        learning_type = self._identify_learning_type(analysis, context)
        learning_value = self._assess_learning_value(analysis, context)

        decision = Decision(
            action="capture_learning",
            parameters={
                "learning_type": learning_type,
                "learning_value": learning_value,
                "knowledge_to_extract": self._identify_knowledge_to_extract(analysis),
            },
            justification=f"Identified {learning_type} learning opportunity with value {learning_value:.1f}",
            confidence=0.8,
            expected_outcomes=["Knowledge base enhanced", "Future performance improved"],
        )

        return ReasoningStep(
            step_type="learning_opportunity_reasoning",
            description="Identified and assessed learning opportunity",
            input_data={"analysis": analysis, "context": context},
            reasoning="Recognized pattern or insight that could improve future reasoning",
            confidence=0.8,
            output={"decision": decision},
        )

    def _assess_reasoning_confidence(self, result: ReasoningResult) -> ReasoningStep:
        """Step 6: Assess overall reasoning confidence."""
        base_confidence = result.analysis.confidence_score
        step_confidences = [step.confidence for step in result.reasoning_steps]
        avg_step_confidence = sum(step_confidences) / len(step_confidences) if step_confidences else 0.5

        # Context relevance factor
        context_relevance = 0.5
        for step in result.reasoning_steps:
            if step.step_type == "context_integration":
                context_relevance = step.output.get("context_relevance", 0.5)
                break

        overall_confidence = base_confidence * 0.4 + avg_step_confidence * 0.4 + context_relevance * 0.2

        return ReasoningStep(
            step_type="confidence_assessment",
            description="Assessed overall reasoning confidence",
            input_data={"result": result},
            reasoning=f"Combined analysis confidence ({base_confidence:.2f}), step confidences ({avg_step_confidence:.2f}), and context relevance ({context_relevance:.2f})",
            confidence=overall_confidence,
            output={"confidence": overall_confidence},
        )

    # Helper methods
    def _is_screenshot(self, input_data: MultiModalInput) -> bool:
        """Determine if input is likely a screenshot."""
        if not input_data.image_path:
            return False

        # Simple heuristic based on filename and metadata
        filename = input_data.image_path.lower()
        screenshot_indicators = ["screenshot", "screen", "capture", "shot"]

        return any(indicator in filename for indicator in screenshot_indicators)

    def _calculate_context_relevance(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> float:
        """Calculate how relevant the context is to the analysis."""
        relevance = 0.5  # Base relevance

        if context.user_intent and analysis.text_analysis:
            text_content = analysis.text_analysis.get("content", "").lower()
            intent_words = context.user_intent.lower().split()
            matches = sum(1 for word in intent_words if word in text_content)
            relevance += 0.2 * (matches / len(intent_words)) if intent_words else 0

        if context.task_objective and analysis.visual_analysis:
            scene_desc = analysis.visual_analysis.scene_description.lower()
            objective_words = context.task_objective.lower().split()
            matches = sum(1 for word in objective_words if word in scene_desc)
            relevance += 0.2 * (matches / len(objective_words)) if objective_words else 0

        return min(relevance, 1.0)

    def _extract_relevant_context_factors(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> List[str]:
        """Extract context factors relevant to the analysis."""
        factors = []

        if context.constraints:
            factors.extend([f"Constraint: {k}={v}" for k, v in context.constraints.items()])

        if context.environmental_factors:
            factors.extend([f"Environment: {k}={v}" for k, v in context.environmental_factors.items()])

        return factors

    def _classify_situation(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> str:
        """Classify the current situation."""
        if analysis.visual_analysis and self._is_screenshot(analysis.input_data):
            return "ui_interaction"
        elif context.task_objective:
            return "task_execution"
        elif self._detects_error_condition(analysis):
            return "error_handling"
        else:
            return "content_analysis"

    def _assess_urgency(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> int:
        """Assess urgency level (1-10)."""
        urgency = 5  # Medium urgency

        # Increase for time-sensitive contexts
        if context.constraints.get("time_limit"):
            urgency += 2

        # Increase for error conditions
        if self._detects_error_condition(analysis):
            urgency += 3

        # Decrease for learning/analysis tasks
        if context.task_objective and "analyze" in context.task_objective.lower():
            urgency -= 2

        return max(1, min(10, urgency))

    def _assess_complexity(self, analysis: MultiModalAnalysis) -> int:
        """Assess complexity level (1-10)."""
        complexity = 1

        if analysis.text_analysis:
            complexity += 1
        if analysis.visual_analysis:
            complexity += 2  # Vision is more complex
        if analysis.audio_analysis:
            complexity += 2  # Audio is complex
        if analysis.cross_modal_insights:
            complexity += len(analysis.cross_modal_insights) // 2

        return min(10, complexity)

    def _extract_situation_factors(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> List[str]:
        """Extract key factors defining the situation."""
        factors = []

        if analysis.visual_analysis:
            factors.append(f"Visual scene: {analysis.visual_analysis.scene_description}")

        if analysis.text_analysis:
            sentiment = analysis.text_analysis.get("sentiment", "unknown")
            factors.append(f"Text sentiment: {sentiment}")

        if context.user_intent:
            factors.append(f"User intent: {context.user_intent}")

        return factors

    def _is_ui_interaction_scenario(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> bool:
        """Determine if this is a UI interaction scenario."""
        return (
            analysis.visual_analysis
            and self._is_screenshot(analysis.input_data)
            and (
                context.user_intent
                and any(word in context.user_intent.lower() for word in ["click", "type", "select", "navigate"])
            )
        )

    def _requires_safety_assessment(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> bool:
        """Determine if safety assessment is required."""
        return context.constraints.get("safety_critical", False) or self._detects_error_condition(analysis)

    def _is_task_execution_scenario(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> bool:
        """Determine if this is a task execution scenario."""
        return bool(context.task_objective and context.task_objective.strip())

    def _detects_error_condition(self, analysis: MultiModalAnalysis) -> bool:
        """Detect if there's an error condition in the analysis."""
        if analysis.integrated_summary and "failed" in analysis.integrated_summary.lower():
            return True
        if analysis.text_analysis and "error" in analysis.text_analysis.get("content", "").lower():
            return True
        return False

    def _is_learning_opportunity(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> bool:
        """Determine if this presents a learning opportunity."""
        return len(analysis.cross_modal_insights) > 2 or (
            analysis.confidence_score > 0.8 and len(context.historical_actions) > 0
        )

    async def _decide_ui_action(
        self, ui_understanding: Optional[UIUnderstanding], analysis: MultiModalAnalysis, context: ReasoningContext
    ) -> Optional[Decision]:
        """Decide on UI action based on understanding."""
        if not ui_understanding:
            return None

        # Find best action based on primary actions and user intent
        primary_actions = ui_understanding.primary_actions
        user_intent = context.user_intent.lower() if context.user_intent else ""

        best_action = None
        best_match_score = 0

        for action in primary_actions:
            match_score = self._calculate_action_intent_match(action, user_intent)
            if match_score > best_match_score:
                best_match_score = match_score
                best_action = action

        if best_action:
            return Decision(
                action=best_action,
                parameters={"ui_elements": [elem.__dict__ for elem in ui_understanding.ui_hierarchy]},
                justification=f"Selected action '{best_action}' matching user intent with score {best_match_score:.2f}",
                confidence=min(best_match_score, 0.9),
                expected_outcomes=[f"UI interaction '{best_action}' completed successfully"],
            )

        return None

    def _calculate_action_intent_match(self, action: str, intent: str) -> float:
        """Calculate how well an action matches user intent."""
        action_words = action.lower().split()
        intent_words = intent.split()

        matches = 0
        for action_word in action_words:
            if any(action_word in intent_word or intent_word in action_word for intent_word in intent_words):
                matches += 1

        return matches / len(action_words) if action_words else 0

    def _classify_content(self, analysis: MultiModalAnalysis) -> str:
        """Classify the type of content."""
        if analysis.visual_analysis:
            for feature in analysis.visual_analysis.features:
                if feature.feature_type == "scene_classification":
                    return feature.properties.get("scene_type", "general_content")

        if analysis.text_analysis:
            word_count = analysis.text_analysis.get("word_count", 0)
            if word_count > 500:
                return "document"
            elif word_count > 100:
                return "article"
            else:
                return "message"

        return "multimedia_content"

    def _determine_analysis_depth(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> str:
        """Determine the depth of analysis required."""
        complexity = self._assess_complexity(analysis)
        urgency = self._assess_urgency(analysis, context)

        if complexity > 7 or urgency > 7:
            return "deep"
        elif complexity > 4 or urgency > 4:
            return "moderate"
        else:
            return "quick"

    def _identify_content_focus_areas(self, analysis: MultiModalAnalysis) -> List[str]:
        """Identify areas to focus analysis on."""
        focus_areas = []

        if analysis.cross_modal_insights:
            focus_areas.append("cross_modal_correlations")

        if analysis.visual_analysis and analysis.visual_analysis.objects_detected:
            focus_areas.append("visual_objects")

        if analysis.text_analysis and analysis.text_analysis.get("key_phrases"):
            focus_areas.append("key_text_elements")

        return focus_areas or ["general_content"]

    def _identify_safety_concerns(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> List[str]:
        """Identify safety concerns."""
        concerns = []

        if self._detects_error_condition(analysis):
            concerns.append("Error condition detected")

        if context.constraints.get("safety_critical"):
            concerns.append("Safety-critical operation")

        if analysis.audio_analysis and "high_frequency_noise" in analysis.audio_analysis.detected_sounds:
            concerns.append("Potentially hazardous audio environment")

        return concerns

    def _assess_risk_level(self, safety_concerns: List[str]) -> float:
        """Assess risk level from safety concerns."""
        if not safety_concerns:
            return 0.1

        # Simple risk assessment
        risk_score = len(safety_concerns) * 0.2

        if "Safety-critical operation" in safety_concerns:
            risk_score += 0.3

        if "Error condition detected" in safety_concerns:
            risk_score += 0.2

        return min(risk_score, 1.0)

    def _assess_task_progress(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> float:
        """Assess progress on current task."""
        # Placeholder implementation
        return 0.5

    def _identify_next_task_steps(
        self, analysis: MultiModalAnalysis, context: ReasoningContext, progress: float
    ) -> List[str]:
        """Identify next steps for task execution."""
        if progress < 0.3:
            return ["analyze_requirements", "gather_resources"]
        elif progress < 0.7:
            return ["execute_main_task", "monitor_progress"]
        else:
            return ["finalize_task", "validate_results"]

    def _identify_required_resources(self, analysis: MultiModalAnalysis, next_steps: List[str]) -> Dict[str, Any]:
        """Identify resources required for next steps."""
        resources = {}

        if "analyze_requirements" in next_steps:
            resources["analysis_tools"] = ["multimodal_processor", "knowledge_graph"]

        if "execute_main_task" in next_steps:
            resources["execution_tools"] = ["action_executor", "tool_coordinator"]

        return resources

    def _classify_error(self, analysis: MultiModalAnalysis) -> str:
        """Classify the type of error."""
        if "failed" in analysis.integrated_summary.lower():
            return "processing_failure"
        elif analysis.text_analysis and "error" in analysis.text_analysis.get("content", ""):
            return "content_error"
        else:
            return "unknown_error"

    def _determine_recovery_strategy(self, error_type: str, context: ReasoningContext) -> str:
        """Determine recovery strategy for error."""
        strategies = {
            "processing_failure": "retry_with_fallback",
            "content_error": "request_clarification",
            "unknown_error": "log_and_continue",
        }
        return strategies.get(error_type, "log_and_continue")

    def _extract_error_context(self, analysis: MultiModalAnalysis) -> Dict[str, Any]:
        """Extract context around the error."""
        return {
            "error_summary": analysis.integrated_summary,
            "available_modalities": [
                "text" if analysis.text_analysis else None,
                "visual" if analysis.visual_analysis else None,
                "audio" if analysis.audio_analysis else None,
            ],
            "confidence_score": analysis.confidence_score,
        }

    def _identify_learning_type(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> str:
        """Identify the type of learning opportunity."""
        if len(analysis.cross_modal_insights) > 3:
            return "cross_modal_patterns"
        elif analysis.confidence_score > 0.9:
            return "high_confidence_insights"
        else:
            return "general_knowledge"

    def _assess_learning_value(self, analysis: MultiModalAnalysis, context: ReasoningContext) -> float:
        """Assess the value of the learning opportunity."""
        value = 0.5

        value += len(analysis.cross_modal_insights) * 0.1
        value += analysis.confidence_score * 0.2

        if context.historical_actions:
            value += 0.2  # Historical context increases value

        return min(value, 1.0)

    def _identify_knowledge_to_extract(self, analysis: MultiModalAnalysis) -> List[str]:
        """Identify knowledge to extract for learning."""
        knowledge_items = []

        if analysis.cross_modal_insights:
            knowledge_items.append("cross_modal_correlations")

        if analysis.visual_analysis and analysis.visual_analysis.objects_detected:
            knowledge_items.append("visual_patterns")

        if analysis.text_analysis and analysis.text_analysis.get("key_phrases"):
            knowledge_items.append("textual_insights")

        return knowledge_items

    def to_dict(self, result: ReasoningResult) -> Dict[str, Any]:
        """Convert ReasoningResult to dictionary for serialization."""
        return {
            "context": {
                "user_intent": result.context.user_intent,
                "task_objective": result.context.task_objective,
                "environmental_factors": result.context.environmental_factors,
                "historical_actions": result.context.historical_actions,
                "constraints": result.context.constraints,
                "timestamp": result.context.timestamp,
            },
            "analysis": self.multimodal_processor.to_dict(result.analysis),
            "reasoning_steps": [
                {
                    "step_type": step.step_type,
                    "description": step.description,
                    "input_data": step.input_data,
                    "reasoning": step.reasoning,
                    "confidence": step.confidence,
                    "output": step.output,
                    "timestamp": step.timestamp,
                }
                for step in result.reasoning_steps
            ],
            "final_decision": (
                {
                    "action": result.final_decision.action,
                    "parameters": result.final_decision.parameters,
                    "justification": result.final_decision.justification,
                    "confidence": result.final_decision.confidence,
                    "alternatives": result.final_decision.alternatives,
                    "risks": result.final_decision.risks,
                    "expected_outcomes": result.final_decision.expected_outcomes,
                }
                if result.final_decision
                else None
            ),
            "confidence_score": result.confidence_score,
            "reasoning_time": result.reasoning_time,
        }
