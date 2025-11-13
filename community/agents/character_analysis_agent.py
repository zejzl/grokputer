#!/usr/bin/env python3
"""
CharacterAnalysisAgent - Analyzes literary characters and validates archetypes
Specialized agent for literary analysis, character development, and safety validation
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import asyncio

from src.core.base_agent import BaseAgent
from src.core.message_bus import MessageBus, Message, MessagePriority
from src.observability.session_logger import SessionLogger


class CharacterAnalysisAgent(BaseAgent):
    """
    Specialized agent for character analysis and archetype validation.
    Focuses on literary analysis, character development patterns, and safety validation.
    """

    def __init__(
        self,
        agent_id: str,
        message_bus: MessageBus,
        session_logger: SessionLogger,
        config: Config,
        heartbeat_interval: int = 30,
    ):
        super().__init__(agent_id, message_bus, session_logger, config, heartbeat_interval)

        # Character archetype patterns (inspired by Raven from Hex novels)
        self.dangerous_archetypes = {
            "power_hungry_witch": {
                "keywords": ["power", "domination", "control", "supremacy", "unlimited", "godlike"],
                "warning_level": "high",
                "description": "Character seeks unlimited power, potentially leading to destructive behavior",
            },
            "destructive_rebel": {
                "keywords": ["rebel", "destroy", "chaos", "anarchy", "revenge", "hatred"],
                "warning_level": "high",
                "description": "Character driven by destructive impulses and rejection of authority",
            },
            "corrupted_hero": {
                "keywords": ["corrupt", "darkness", "temptation", "forbidden", "sacrifice", "damnation"],
                "warning_level": "medium",
                "description": "Heroic character tempted by dark forces, risking corruption",
            },
            "isolated_savior": {
                "keywords": ["alone", "burden", "sacrifice", "save", "protect", "cost"],
                "warning_level": "medium",
                "description": "Character bears heavy burdens alone, potentially leading to mental strain",
            },
        }

        # Safe archetype patterns
        self.safe_archetypes = {
            "empowered_learner": {
                "keywords": ["learn", "grow", "develop", "understand", "wise", "balanced"],
                "description": "Character grows through learning and maintains balance",
            },
            "community_builder": {
                "keywords": ["community", "together", "support", "help", "unity", "collaboration"],
                "description": "Character builds connections and works with others",
            },
            "ethical_warrior": {
                "keywords": ["justice", "protect", "defend", "righteous", "moral", "compassion"],
                "description": "Character fights for justice while maintaining ethical standards",
            },
        }

        self.analysis_history = []

    async def analyze_character(self, character_data: Dict) -> Dict:
        """
        Analyze a character description for archetypes and safety concerns.

        Args:
            character_data: Dictionary containing character information

        Returns:
            Analysis results with archetype classification and safety assessment
        """
        character_text = character_data.get("description", "")
        character_name = character_data.get("name", "Unknown")

        # Convert to lowercase for analysis
        text_lower = character_text.lower()

        analysis = {
            "character_name": character_name,
            "timestamp": datetime.now().isoformat(),
            "dangerous_archetypes": [],
            "safe_archetypes": [],
            "overall_safety_score": 100,  # Start with perfect score
            "recommendations": [],
            "archetype_balance": "balanced",
        }

        # Analyze dangerous archetypes
        for archetype_name, archetype_data in self.dangerous_archetypes.items():
            keyword_matches = []
            for keyword in archetype_data["keywords"]:
                if keyword in text_lower:
                    keyword_matches.append(keyword)

            if keyword_matches:
                danger_score = len(keyword_matches) * 10  # 10 points per keyword match
                analysis["dangerous_archetypes"].append(
                    {
                        "archetype": archetype_name,
                        "matches": keyword_matches,
                        "danger_score": danger_score,
                        "description": archetype_data["description"],
                        "warning_level": archetype_data["warning_level"],
                    }
                )
                analysis["overall_safety_score"] -= danger_score

        # Analyze safe archetypes
        for archetype_name, archetype_data in self.safe_archetypes.items():
            keyword_matches = []
            for keyword in archetype_data["keywords"]:
                if keyword in text_lower:
                    keyword_matches.append(keyword)

            if keyword_matches:
                analysis["safe_archetypes"].append(
                    {
                        "archetype": archetype_name,
                        "matches": keyword_matches,
                        "description": archetype_data["description"],
                    }
                )

        # Calculate archetype balance
        dangerous_count = len(analysis["dangerous_archetypes"])
        safe_count = len(analysis["safe_archetypes"])

        if dangerous_count > safe_count:
            analysis["archetype_balance"] = "dangerous"
            analysis["recommendations"].append(
                "Character shows more dangerous than safe archetypes - consider adding positive character development"
            )
        elif safe_count > dangerous_count:
            analysis["archetype_balance"] = "safe"
        else:
            analysis["archetype_balance"] = "balanced"

        # Generate specific recommendations
        if analysis["overall_safety_score"] < 70:
            analysis["recommendations"].append(
                "High-risk character archetype detected - implement strong safeguards in narrative generation"
            )
        elif analysis["overall_safety_score"] < 50:
            analysis["recommendations"].append(
                "CRITICAL: Extremely dangerous character archetype - block generation or require human oversight"
            )

        # Ensure score doesn't go below 0
        analysis["overall_safety_score"] = max(0, analysis["overall_safety_score"])

        # Store in history
        self.analysis_history.append(analysis)

        return analysis

    async def validate_story_generation(self, story_prompt: str) -> Dict:
        """
        Validate a story generation prompt for safety concerns.

        Args:
            story_prompt: The story prompt to validate

        Returns:
            Validation results
        """
        validation = {
            "prompt": story_prompt,
            "is_safe": True,
            "risk_factors": [],
            "suggested_modifications": [],
            "validation_score": 100,
        }

        prompt_lower = story_prompt.lower()

        # Check for high-risk keywords
        high_risk_keywords = [
            "unlimited power",
            "godlike abilities",
            "destroy everything",
            "ultimate domination",
            "corrupt the world",
            "eternal darkness",
        ]

        for keyword in high_risk_keywords:
            if keyword in prompt_lower:
                validation["risk_factors"].append(f"High-risk keyword: '{keyword}'")
                validation["validation_score"] -= 20
                validation["suggested_modifications"].append(f"Replace '{keyword}' with safer alternatives")

        # Check for Raven-like character creation
        raven_indicators = ["powerful witch", "hex abilities", "dark magic", "forbidden powers"]
        raven_score = sum(1 for indicator in raven_indicators if indicator in prompt_lower)

        if raven_score >= 2:
            validation["risk_factors"].append("Potential Raven-like character creation detected")
            validation["validation_score"] -= 15
            validation["suggested_modifications"].append("Add positive character development and ethical constraints")

        # Determine if safe
        validation["is_safe"] = validation["validation_score"] >= 70

        return validation

    async def generate_character_profile(self, character_name: str, traits: List[str]) -> Dict:
        """
        Generate a balanced character profile with safety considerations.

        Args:
            character_name: Name of the character
            traits: List of character traits

        Returns:
            Balanced character profile
        """
        # Analyze input traits for safety
        trait_text = " ".join(traits).lower()
        analysis = await self.analyze_character({"name": character_name, "description": trait_text})

        # Generate balanced profile
        profile = {
            "name": character_name,
            "original_traits": traits,
            "balanced_traits": traits.copy(),
            "added_safety_traits": [],
            "analysis": analysis,
        }

        # Add safety traits if needed
        if analysis["overall_safety_score"] < 80:
            safety_additions = {
                "power_hungry_witch": ["ethical constraints", "community responsibility", "balanced growth"],
                "destructive_rebel": ["constructive change", "peaceful methods", "understanding"],
                "corrupted_hero": ["moral compass", "support network", "redemption path"],
                "isolated_savior": ["team support", "delegation skills", "self-care"],
            }

            for dangerous in analysis["dangerous_archetypes"]:
                archetype = dangerous["archetype"]
                if archetype in safety_additions:
                    profile["added_safety_traits"].extend(safety_additions[archetype])
                    profile["balanced_traits"].extend(safety_additions[archetype])

        return profile

    async def process_message(self, message: Message) -> Optional[Message]:
        """Process incoming messages."""
        if message.message_type == "character_analysis_request":
            character_data = message.content.get("character_data", {})
            analysis = await self.analyze_character(character_data)

            response = Message(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                message_type="character_analysis_response",
                content={"analysis": analysis},
                priority=MessagePriority.NORMAL,
            )
            return response

        elif message.message_type == "story_validation_request":
            prompt = message.content.get("prompt", "")
            validation = await self.validate_story_generation(prompt)

            response = Message(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                message_type="story_validation_response",
                content={"validation": validation},
                priority=MessagePriority.NORMAL,
            )
            return response

        elif message.message_type == "character_profile_request":
            name = message.content.get("name", "")
            traits = message.content.get("traits", [])
            profile = await self.generate_character_profile(name, traits)

            response = Message(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                message_type="character_profile_response",
                content={"profile": profile},
                priority=MessagePriority.NORMAL,
            )
            return response

        return None

    async def run(self):
        """Main agent loop."""
        await self.register_with_bus()

        while not self.shutdown_event.is_set():
            try:
                # Process messages
                message = await self.message_bus.receive(self.agent_id, timeout=1.0)
                if message:
                    response = await self.process_message(message)
                    if response:
                        await self.message_bus.send(response.receiver, response)

                # Periodic health check
                await self.send_heartbeat()

                await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.error(f"CharacterAnalysisAgent error: {e}")
                await asyncio.sleep(1.0)
