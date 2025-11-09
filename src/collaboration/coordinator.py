"""
Collaboration coordinator for orchestrating dual-agent dialogue via MessageBus.
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from src.core.message_bus import MessageBus, MessagePriority
from src.agents.claude_agent import ClaudeAgent
from src.agents.grok_agent import GrokAgent
from src.collaboration.message_models import (
    CollaborationMessage,
    MessageType,
    AgentRole,
    FinalPlan
)
from src.collaboration.consensus import ConsensusDetector
from src.collaboration.output_generator import OutputGenerator

logger = logging.getLogger(__name__)


class CollaborationCoordinator:
    """Orchestrates dual-agent collaboration via MessageBus."""

    def __init__(
        self,
        claude_api_key: str,
        grok_api_key: str,
        max_rounds: int = 5,
        convergence_threshold: float = 0.6
    ):
        """
        Initialize collaboration coordinator.

        Args:
            claude_api_key: Anthropic API key
            grok_api_key: xAI API key
            max_rounds: Maximum conversation rounds
            convergence_threshold: Minimum convergence score for consensus (0-1)
        """
        self.max_rounds = max_rounds

        # Initialize agents
        self.claude = ClaudeAgent(api_key=claude_api_key)
        self.grok = GrokAgent(api_key=grok_api_key)

        # Initialize infrastructure
        self.message_bus = MessageBus()
        self.consensus_detector = ConsensusDetector(convergence_threshold=convergence_threshold)
        self.output_generator = OutputGenerator()

        # Collaboration state
        self.correlation_id = f"collab_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.message_history: List[CollaborationMessage] = []

        logger.info(f"Collaboration initialized: {self.correlation_id}")

    async def run_collaboration(self, task_prompt: str) -> FinalPlan:
        """
        Main collaboration loop.

        Args:
            task_prompt: User's task/prompt for collaboration

        Returns:
            FinalPlan with synthesized output
        """
        logger.info(f"Starting collaboration on task: {task_prompt[:100]}...")

        try:
            # Run conversation rounds
            for round_num in range(1, self.max_rounds + 1):
                logger.info(f"Round {round_num}/{self.max_rounds}")

                # Both agents respond in parallel
                await self._run_round(task_prompt, round_num)

                # Analyze for consensus
                consensus_signal = self.consensus_detector.analyze_round(
                    self.message_history,
                    round_num
                )

                logger.info(
                    f"Consensus check: {consensus_signal.recommendation} "
                    f"(confidence: {consensus_signal.confidence:.2f}, "
                    f"convergence: {consensus_signal.convergence_score:.2f})"
                )

                # Check if we should finalize
                if consensus_signal.recommendation == "FINALIZE":
                    logger.info(f"Consensus reached in round {round_num}")
                    break
                elif consensus_signal.recommendation == "MEDIATE":
                    logger.warning(
                        f"Mediation recommended: {consensus_signal.reasoning}"
                    )
                    # Continue anyway (human can review output)

            # Generate final plan
            final_plan = await self._finalize_collaboration(
                task_prompt,
                consensus_signal
            )

            # Save to disk
            output_path = self.output_generator.save_to_file(final_plan)
            logger.info(f"Collaboration complete. Saved to: {output_path}")

            return final_plan

        except Exception as e:
            logger.error(f"Collaboration failed: {e}", exc_info=True)
            raise

    async def _run_round(self, task_prompt: str, round_number: int) -> None:
        """Execute a single conversation round."""

        # Create trigger message (broadcast to both agents)
        trigger = CollaborationMessage(
            message_id=f"msg_{round_number:03d}_trigger",
            correlation_id=self.correlation_id,
            message_type=MessageType.PROPOSAL if round_number == 1 else MessageType.FEEDBACK,
            sender=AgentRole.COORDINATOR,
            recipient=None,  # Broadcast
            round_number=round_number,
            content=task_prompt if round_number == 1 else "Continue discussion based on previous messages"
        )

        # Both agents process in parallel
        claude_task = self.claude.process_message(trigger, task_prompt)
        grok_task = self.grok.process_message(trigger, task_prompt)

        # Wait for both responses
        claude_response, grok_response = await asyncio.gather(
            claude_task,
            grok_task,
            return_exceptions=True
        )

        # Handle errors gracefully
        if isinstance(claude_response, Exception):
            logger.error(f"Claude failed in round {round_number}: {claude_response}")
            claude_response = CollaborationMessage(
                message_id=f"msg_{round_number:03d}_claude_error",
                correlation_id=self.correlation_id,
                message_type=MessageType.FEEDBACK,
                sender=AgentRole.CLAUDE,
                round_number=round_number,
                content="[Error: Claude API failed. See logs.]"
            )

        if isinstance(grok_response, Exception):
            logger.error(f"Grok failed in round {round_number}: {grok_response}")
            grok_response = CollaborationMessage(
                message_id=f"msg_{round_number:03d}_grok_error",
                correlation_id=self.correlation_id,
                message_type=MessageType.FEEDBACK,
                sender=AgentRole.GROK,
                round_number=round_number,
                content="[Error: Grok API failed. See logs.]"
            )

        # Add to history
        self.message_history.append(claude_response)
        self.message_history.append(grok_response)

        # TODO: Integrate with MessageBus for monitoring (use broadcast() method)
        # For now, just log the completion
        logger.debug(f"Round {round_number} messages: Claude={claude_response.message_id}, Grok={grok_response.message_id}")

        logger.info(f"Round {round_number} complete. Messages: {len(self.message_history)}")

    async def _finalize_collaboration(
        self,
        task_prompt: str,
        final_consensus: ConsensusSignal
    ) -> FinalPlan:
        """Generate final plan from message history."""

        # Extract perspectives
        claude_messages = [m for m in self.message_history if m.sender == AgentRole.CLAUDE]
        grok_messages = [m for m in self.message_history if m.sender == AgentRole.GROK]

        # Synthesize unified plan
        unified_plan = await self.output_generator.synthesize_plan(
            claude_messages=claude_messages,
            grok_messages=grok_messages,
            consensus_signal=final_consensus
        )

        final_plan = FinalPlan(
            task_description=task_prompt,
            consensus_reached=final_consensus.is_consensus,
            total_rounds=max(m.round_number for m in self.message_history) if self.message_history else 0,
            claude_perspective="\n\n".join(m.content for m in claude_messages),
            grok_perspective="\n\n".join(m.content for m in grok_messages),
            unified_plan=unified_plan,
            key_agreements=final_consensus.agreement_indicators,
            key_disagreements=final_consensus.disagreement_indicators,
            metadata={
                "correlation_id": self.correlation_id,
                "convergence_score": final_consensus.convergence_score,
                "confidence": final_consensus.confidence,
                "total_messages": len(self.message_history)
                # TODO: Add API cost tracking
            }
        )

        return final_plan
