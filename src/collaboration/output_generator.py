"""
Output generator for synthesizing and saving collaboration results.
"""

from datetime import datetime
from pathlib import Path
from typing import List
import logging
import json

from src.collaboration.message_models import (
    CollaborationMessage,
    ConsensusSignal,
    FinalPlan
)

logger = logging.getLogger(__name__)


class OutputGenerator:
    """Generates and saves collaboration output."""

    def __init__(self, output_dir: str = "docs"):
        """
        Initialize output generator.

        Args:
            output_dir: Directory to save collaboration plans
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"OutputGenerator initialized (output_dir: {self.output_dir})")

    async def synthesize_plan(
        self,
        claude_messages: List[CollaborationMessage],
        grok_messages: List[CollaborationMessage],
        consensus_signal: ConsensusSignal
    ) -> str:
        """
        Synthesize a unified plan from both agents' perspectives.

        For v1, this is a simple merge. For v2, consider using a third
        LLM call to synthesize (meta-reasoning).

        Args:
            claude_messages: All messages from Claude
            grok_messages: All messages from Grok
            consensus_signal: Final consensus analysis

        Returns:
            Unified plan as markdown string
        """
        # Simple synthesis: Combine key points from both
        synthesis_parts = ["# Unified Implementation Plan\n"]

        # Add consensus status
        if consensus_signal.is_consensus:
            synthesis_parts.append(
                f"> **Status**: Consensus reached (confidence: {consensus_signal.confidence:.2f})\n"
            )
        else:
            synthesis_parts.append(
                f"> **Status**: Partial agreement (convergence: {consensus_signal.convergence_score:.2f})\n"
            )

        # Extract key sections from latest messages
        latest_claude = claude_messages[-1].content if claude_messages else ""
        latest_grok = grok_messages[-1].content if grok_messages else ""

        synthesis_parts.append("\n## Key Agreements\n")
        if consensus_signal.agreement_indicators:
            for indicator in consensus_signal.agreement_indicators[:5]:  # Top 5
                synthesis_parts.append(f"- {indicator}\n")
        else:
            synthesis_parts.append("- [Agents did not explicitly signal agreement]\n")

        synthesis_parts.append("\n## Recommended Approach\n")
        synthesis_parts.append(
            "Based on the discussion, the following approach synthesizes both perspectives:\n\n"
        )

        # Simple merge (v1): Take last round from both agents
        synthesis_parts.append("### From Claude's Perspective\n\n")
        synthesis_parts.append(latest_claude)
        synthesis_parts.append("\n\n### From Grok's Perspective\n\n")
        synthesis_parts.append(latest_grok)

        synthesis_parts.append("\n\n### Next Steps\n")
        synthesis_parts.append(
            "1. Review both perspectives above\n"
            "2. Identify overlapping recommendations\n"
            "3. Resolve any conflicts manually if needed\n"
            "4. Proceed with implementation\n"
        )

        return "".join(synthesis_parts)

    def save_to_file(self, final_plan: FinalPlan) -> Path:
        """
        Save FinalPlan to markdown file.

        Args:
            final_plan: Final plan to save

        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"collaboration_plan_{timestamp}.md"
        filepath = self.output_dir / filename

        # Build markdown content
        content_parts = [
            f"# Collaboration Plan: {final_plan.task_description[:80]}...\n\n",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
            f"**Correlation ID**: {final_plan.metadata.get('correlation_id', 'N/A')}\n",
            f"**Rounds**: {final_plan.total_rounds}\n",
            f"**Consensus**: {'Yes' if final_plan.consensus_reached else 'Partial'}\n",
            f"**Convergence Score**: {final_plan.metadata.get('convergence_score', 0):.2f}\n",
            f"**Confidence**: {final_plan.metadata.get('confidence', 0):.2f}\n\n",
            "---\n\n",
            "## Task Description\n\n",
            f"{final_plan.task_description}\n\n",
            "---\n\n",
            final_plan.unified_plan,
            "\n\n---\n\n",
            "## Full Conversation\n\n",
            "### Claude's Contributions\n\n",
            final_plan.claude_perspective,
            "\n\n### Grok's Contributions\n\n",
            final_plan.grok_perspective,
            "\n\n---\n\n",
            "## Metadata\n\n",
            f"```json\n{json.dumps(final_plan.metadata, indent=2)}\n```\n"
        ]

        content = "".join(content_parts)

        # Write to file
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Saved collaboration plan to {filepath}")

        return filepath
