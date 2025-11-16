"""
HyDE (Hypothetical Document Embeddings) Generator for Grokputer Memory System.

Generates hypothetical documents from queries to improve semantic retrieval.
Uses Grok LLM to create relevant hypothetical content that bridges semantic gaps.
"""

import logging
from typing import List

from ..grok_client import FallbackGrokClient

logger = logging.getLogger(__name__)


class HyDEGenerator:
    """
    Generates hypothetical documents for improved vector retrieval.

    HyDE works by:
    1. Taking a query
    2. Using LLM to generate hypothetical relevant documents
    3. Embedding these hypotheticals for better semantic matching
    """

    def __init__(self, num_hypotheticals: int = 3, model: str = "grok-beta"):
        self.num_hypotheticals = num_hypotheticals
        self.model = model
        self.client = FallbackGrokClient()

    async def generate_hypotheticals(self, query: str) -> List[str]:
        """
        Generate hypothetical documents relevant to the query.
        """
        prompt = f"""
        Given the query: "{query}"

        Generate {self.num_hypotheticals} hypothetical documents that would be highly relevant to answer this query.
        Each document should be a realistic, detailed description of content that would contain information relevant to the query.

        Make each hypothetical document:
        - Specific and detailed (200-400 words)
        - Realistic and plausible
        - Directly relevant to the query
        - Written in natural language as if from actual documentation or conversation

        Return only the documents, one per line, separated by ---.
        """

        messages = [{"role": "user", "content": prompt}]

        try:
            response = await self.client.chat(messages)
            if not response or "Error:" in response:
                logger.warning(f"HyDE generation failed: {response}")
                return []

            # Split by separator
            documents = [doc.strip() for doc in response.split("---") if doc.strip()]
            documents = documents[: self.num_hypotheticals]  # Limit to requested number

            logger.debug(f"Generated {len(documents)} hypothetical documents for query: {query[:50]}...")
            return documents

        except Exception as e:
            logger.error(f"HyDE generation error: {e}")
            return []

    def generate_hypotheticals_sync(self, query: str) -> List[str]:
        """
        Synchronous wrapper for generate_hypotheticals.
        Note: This blocks - prefer async version in production.
        """
        import asyncio

        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.generate_hypotheticals(query))
            return result
        finally:
            try:
                loop.close()
            except:
                pass
