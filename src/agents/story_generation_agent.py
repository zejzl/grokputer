#!/usr/bin/env python3
"""
StoryGenerationAgent - Creates creative narratives using literary patterns
Specialized agent for autonomous story generation with safety validation
"""
from __future__ import annotations

import asyncio
import json
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.core.base_agent import BaseAgent
from src.core.message_bus import Message, MessageBus, MessagePriority
from src.grok_client import GrokClient
from src.observability.session_logger import SessionLogger


class StoryGenerationAgent(BaseAgent):
    """
    Specialized agent for generating creative stories using literary patterns.
    Inspired by Hex novels character development and narrative structures.
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

        # Initialize Grok client for story generation
        self.grok_client = GrokClient()

        # Enable TaskClient integration
        self.enable_task_client(
            ["story_generation", "character_development", "narrative_creation", "literary_analysis", "creative_writing"]
        )

        # Hex-inspired narrative patterns
        self.narrative_patterns = {
            "raven_transformation_arc": {
                "stages": [
                    "ordinary_beginning",
                    "power_awakening",
                    "struggle_control",
                    "moral_crisis",
                    "redemption_choice",
                ],
                "themes": ["identity", "power_responsibility", "isolation_connection", "destiny_freewill"],
                "character_traits": ["rebellious", "introspective", "powerful", "burdened", "transformative"],
            },
            "witch_coming_of_age": {
                "elements": ["mysterious_heritage", "forbidden_knowledge", "supernatural_conflicts", "personal_growth"],
                "conflicts": ["internal_power_struggle", "external_threats", "moral_dilemmas", "relationship_dynamics"],
            },
            "magical_realism_fantasy": {
                "settings": ["contemporary_world", "hidden_magical_realm", "time_slip_dimensions"],
                "plot_devices": ["prophetic_visions", "ancient_artifacts", "coven_politics", "dimensional_rifts"],
            },
        }

        # Story generation templates
        self.story_templates = {
            "hero_journey": """
In a world where magic hides in plain sight, {protagonist_name} discovers their extraordinary abilities on their {age}th birthday. What begins as a thrilling awakening soon becomes a dangerous burden as {protagonist_name} learns that power comes with terrible responsibility.

As {protagonist_name} navigates the treacherous waters of their newfound magic, they encounter {antagonist_type} who seeks to exploit or destroy them. Through trials of {conflict_type}, {protagonist_name} must confront their deepest fears and make choices that will define not just their future, but the fate of {stake_type}.

The journey transforms {protagonist_name} from a {initial_state} {character_type} into a {final_state} force for {theme}, proving that true power lies not in domination, but in {redemption_quality}.
""",
            "forbidden_magic": """
The ancient grimoire whispered secrets that {protagonist_name} never asked to hear. Born into a family of {family_background}, {protagonist_name} always felt different - a feeling that became terrifying reality when their latent magical abilities manifested during a moment of {trigger_event}.

Now hunted by {antagonist_type} who view such power as a threat to the natural order, {protagonist_name} must master abilities they never wanted while grappling with the moral implications of {ethical_dilemma}. Along the way, they form uneasy alliances with {ally_type} and uncover family secrets that reveal {protagonist_name}'s connection to {ancient_force}.

As the boundaries between worlds begin to blur, {protagonist_name} faces the ultimate choice: embrace their destiny as a {destiny_role} or reject the power that threatens to consume them entirely.
""",
            "time_weaving": """
Time was never meant to be rewritten, but {protagonist_name} discovered they could do exactly that. A {profession} living an ordinary life until a {inciting_incident} revealed their ability to see and manipulate temporal threads.

Each vision shows {protagonist_name} the consequences of their choices - alternate realities where {personal_stake} plays out differently. Pursued by {antagonist_type} who seek to weaponize this power, {protagonist_name} must navigate the complex web of cause and effect while confronting {internal_conflict}.

As paradoxes begin to unravel the fabric of reality, {protagonist_name} learns that some moments in time are fixed, immutable anchors around which all other possibilities swirl. The true challenge becomes not changing the past, but accepting it and forging a future worth fighting for.
""",
        }

        self.generation_history = []

    async def generate_story(
        self, theme: str, character_inspiration: str = "raven", length: str = "medium", safety_level: str = "balanced"
    ) -> Dict:
        """
        Generate a creative story using Hex-inspired patterns.

        Args:
            theme: Story theme (power, identity, destiny, etc.)
            character_inspiration: Character archetype to draw from
            length: Story length (short, medium, long)
            safety_level: Safety constraints (safe, balanced, creative)

        Returns:
            Generated story with metadata
        """
        # Select appropriate template and patterns
        template_key = random.choice(list(self.story_templates.keys()))
        template = self.story_templates[template_key]

        # Generate character details based on inspiration
        character_details = await self._generate_character_details(character_inspiration, safety_level)

        # Generate plot elements
        plot_elements = await self._generate_plot_elements(theme, character_details)

        # Fill template with generated content
        plot_elements["theme"] = theme  # Add theme to template variables
        story_text = template.format(**plot_elements)

        # Enhance with AI if needed
        if length == "long" or theme == "complex":
            story_text = await self._enhance_with_ai(story_text, theme)

        # Validate safety
        safety_check = await self._validate_story_safety(story_text, safety_level)

        result = {
            "story_title": plot_elements.get("story_title", f"The {theme.title()} Awakening"),
            "story_text": story_text,
            "theme": theme,
            "character_inspiration": character_inspiration,
            "length": length,
            "safety_level": safety_level,
            "plot_elements": plot_elements,
            "safety_check": safety_check,
            "generation_timestamp": datetime.now().isoformat(),
            "template_used": template_key,
        }

        self.generation_history.append(result)
        return result

    async def _generate_character_details(self, inspiration: str, safety_level: str) -> Dict:
        """Generate character details based on inspiration source."""
        if inspiration.lower() == "raven":
            # Raven from Hex novels
            names = ["Raven", "Rowan", "Sage", "Morgan", "Alex", "Jordan"]
            ages = ["16", "17", "18", "19"]
            backgrounds = ["ordinary_teenager", "troubled_youth", "gifted_student", "outsider"]

            character = {
                "protagonist_name": random.choice(names),
                "age": random.choice(ages),
                "family_background": random.choice(backgrounds),
                "initial_state": random.choice(["confused", "angry", "curious", "reluctant"]),
                "character_type": random.choice(["witch", "seer", "guardian", "warrior"]),
                "final_state": random.choice(["wise", "balanced", "compassionate", "resolute"]),
                "redemption_quality": random.choice(["understanding", "compassion", "wisdom", "courage"]),
            }
        else:
            # Generic character generation
            character = {
                "protagonist_name": f"Character_{random.randint(1, 1000)}",
                "age": str(random.randint(16, 25)),
                "family_background": "ordinary_family",
                "initial_state": "ordinary",
                "character_type": "person",
                "final_state": "transformed",
                "redemption_quality": "growth",
            }

        # Apply safety level adjustments
        if safety_level == "safe":
            character["final_state"] = random.choice(["wise", "compassionate", "balanced"])
            character["redemption_quality"] = random.choice(["understanding", "compassion", "wisdom"])

        return character

    async def _generate_plot_elements(self, theme: str, character: Dict) -> Dict:
        """Generate plot elements for the story."""
        antagonists = {
            "power": ["corrupt_corporation", "dark_wizard", "power_hungry_rival"],
            "identity": ["family_secret", "lost_heritage", "false_identity"],
            "destiny": ["ancient_prophecy", "fate_weaver", "destiny_enforcer"],
        }

        conflicts = {
            "power": ["power_corruption", "responsibility_burden", "control_loss"],
            "identity": ["self_discovery", "heritage_rejection", "identity_crisis"],
            "destiny": ["fate_resistance", "prophecy_fulfillment", "choice_denial"],
        }

        stakes = {
            "power": ["world_destruction", "magical_imbalance", "innocent_lives"],
            "identity": ["personal_destruction", "family_legacy", "cultural_heritage"],
            "destiny": ["reality_unraveling", "timeless_oblivion", "eternal_stagnation"],
        }

        plot = {
            "antagonist_type": random.choice(antagonists.get(theme, antagonists["power"])),
            "conflict_type": random.choice(conflicts.get(theme, conflicts["power"])),
            "stake_type": random.choice(stakes.get(theme, stakes["power"])),
            "trigger_event": random.choice(
                ["family_crisis", "mysterious_accident", "strange_dream", "ancient_artifact"]
            ),
            "ethical_dilemma": random.choice(["power_abuse", "innocent_sacrifice", "truth_concealment"]),
            "ally_type": random.choice(["fellow_mages", "mysterious_mentor", "reluctant_ally"]),
            "ancient_force": random.choice(["forgotten_gods", "elemental_beings", "time_weavers"]),
            "destiny_role": random.choice(["guardian", "balance_keeper", "reality_anchor"]),
            "profession": random.choice(["student", "teacher", "artist", "scientist", "writer", "detective"]),
            "inciting_incident": random.choice(
                ["strange_vision", "mysterious_artifact", "family_secret", "supernatural_event"]
            ),
            "personal_stake": random.choice(["loved_ones", "personal_identity", "life_work", "moral_beliefs"]),
            "internal_conflict": random.choice(
                ["fear_of_power", "loss_of_identity", "moral_dilemmas", "emotional_turmoil"]
            ),
            "story_title": f"The {theme.title()} of {character['protagonist_name']}",
        }

        # Merge with character details
        plot.update(character)
        return plot

    async def _enhance_with_ai(self, base_story: str, theme: str) -> str:
        """Enhance story with AI-generated content."""
        try:
            prompt = f"""
Expand and enhance this story concept with rich details, vivid descriptions, and emotional depth.
Keep the core plot but add compelling scenes, character development, and thematic elements.
Maintain a young adult fantasy tone similar to the Hex novels.

Theme: {theme}
Base story:
{base_story}

Enhanced version:"""

            response = await self.grok_client.generate_text(prompt=prompt, max_tokens=2000, temperature=0.7)

            if response and "content" in response:
                return response["content"].strip()
            else:
                return base_story

        except Exception as e:
            self.logger.error(f"AI enhancement failed: {e}")
            return base_story

    async def _validate_story_safety(self, story: str, safety_level: str) -> Dict:
        """Validate story for safety concerns."""
        validation = {"is_safe": True, "warnings": [], "score": 100}

        story_lower = story.lower()

        # Check for dangerous themes
        dangerous_keywords = [
            "unlimited power",
            "world domination",
            "mass destruction",
            "eternal suffering",
            "complete annihilation",
        ]

        for keyword in dangerous_keywords:
            if keyword in story_lower:
                validation["warnings"].append(f"Potentially dangerous theme: '{keyword}'")
                validation["score"] -= 15

        # Adjust based on safety level
        if safety_level == "safe" and validation["score"] < 90:
            validation["is_safe"] = False
        elif safety_level == "balanced" and validation["score"] < 70:
            validation["is_safe"] = False

        return validation

    async def process_message(self, message: Message) -> Optional[Message]:
        """Process incoming messages."""
        if message.message_type == "story_generation_request":
            params = message.content
            theme = params.get("theme", "power")
            character_inspiration = params.get("character_inspiration", "raven")
            length = params.get("length", "medium")
            safety_level = params.get("safety_level", "balanced")

            story = await self.generate_story(theme, character_inspiration, length, safety_level)

            response = Message(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                message_type="story_generation_response",
                content={"story": story},
                priority=MessagePriority.NORMAL,
            )
            return response

        elif message.message_type == "character_inspiration_request":
            inspiration = message.content.get("inspiration", "raven")
            details = await self._generate_character_details(inspiration, "balanced")

            response = Message(
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                message_type="character_inspiration_response",
                content={"character_details": details},
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
                self.logger.error(f"StoryGenerationAgent error: {e}")
                await asyncio.sleep(1.0)
