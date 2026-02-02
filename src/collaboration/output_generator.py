"""
Output generator for synthesizing and saving collaboration results.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from src.collaboration.message_models import (
    CollaborationMessage,
    ConsensusSignal,
    FinalPlan,
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
        consensus_signal: ConsensusSignal,
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
            synthesis_parts.append(f"> **Status**: Consensus reached (confidence: {consensus_signal.confidence:.2f})\n")
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
        synthesis_parts.append("Based on the discussion, the following approach synthesizes both perspectives:\n\n")

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

    async def synthesize_multi_provider_plan(
        self, provider_messages: dict, consensus_signal: ConsensusSignal, provider_roles: dict
    ) -> str:
        """
        Synthesize a unified plan from multiple providers' perspectives.

        Args:
            provider_messages: Dict mapping provider_id to list of messages
            consensus_signal: Final consensus analysis
            provider_roles: Dict mapping provider_id to role name

        Returns:
            Unified plan as markdown string
        """
        synthesis_parts = ["# Multi-Provider Unified Implementation Plan\n"]

        # Add consensus status
        if consensus_signal.is_consensus:
            synthesis_parts.append(f"> **Status**: Consensus reached (confidence: {consensus_signal.confidence:.2f})\n")
        else:
            synthesis_parts.append(
                f"> **Status**: Partial agreement (convergence: {consensus_signal.convergence_score:.2f})\n"
            )

        # Add provider summary
        synthesis_parts.append(f"> **Providers**: {len(provider_messages)}\n")
        synthesis_parts.append(f"> **Roles**: {', '.join(provider_roles.values())}\n\n")

        # Extract key sections from latest messages
        synthesis_parts.append("## Key Agreements\n")
        if consensus_signal.agreement_indicators:
            for indicator in consensus_signal.agreement_indicators[:5]:  # Top 5
                synthesis_parts.append(f"- {indicator}\n")
        else:
            synthesis_parts.append("- [Providers did not explicitly signal agreement]\n")

        synthesis_parts.append("\n## Provider Perspectives\n")

        # Add each provider's latest contribution
        for provider_id, messages in provider_messages.items():
            if messages:
                role = provider_roles.get(provider_id, "unknown")
                latest_message = messages[-1].content
                synthesis_parts.append(f"\n### {provider_id.title()} ({role})\n\n")
                synthesis_parts.append(f"{latest_message[:500]}..." if len(latest_message) > 500 else latest_message)
                synthesis_parts.append("\n")

        synthesis_parts.append("\n## Recommended Approach\n")
        synthesis_parts.append(
            "Based on the multi-provider discussion, the following approach synthesizes all perspectives:\n\n"
        )

        # Simple synthesis: Combine key insights from all providers
        synthesis_parts.append("### Synthesized Recommendations\n\n")
        synthesis_parts.append(
            "1. **Review all provider perspectives** above for comprehensive insights\n"
            "2. **Identify common themes** across different roles and capabilities\n"
            "3. **Balance competing priorities** (e.g., innovation vs. reliability)\n"
            "4. **Leverage complementary strengths** of different providers\n"
            "5. **Validate against requirements** and constraints\n"
        )

        synthesis_parts.append("\n### Next Steps\n")
        synthesis_parts.append(
            "1. Consolidate overlapping recommendations\n"
            "2. Resolve any conflicts through additional analysis\n"
            "3. Create detailed implementation specifications\n"
            "4. Begin development with chosen approach\n"
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
            f"```json\n{json.dumps(final_plan.metadata, indent=2)}\n```\n",
        ]

        content = "".join(content_parts)

        # Write to file
        filepath.write_text(content, encoding="utf-8")
        logger.info(f"Saved collaboration plan to {filepath}")

        return filepath
