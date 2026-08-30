"""
Message Bus Throughput Test

Tests the throughput (messages per second) of the MessageBus under various loads.
"""
from __future__ import annotations

import asyncio
import time
import statistics
import sys
import os
from typing import List, Dict, Any
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.core.message_bus import MessageBus, Message, MessagePriority

logger = logging.getLogger(__name__)


class MessageBusThroughputTester:
    """Test message bus throughput with multiple producers and consumers."""

    def __init__(
        self, num_producers: int = 5, num_consumers: int = 5, messages_per_producer: int = 1000, message_size: int = 100
    ):
        self.num_producers = num_producers
        self.num_consumers = num_consumers
        self.messages_per_producer = messages_per_producer
        self.message_size = message_size
        self.bus = MessageBus()
        self.results: Dict[str, Any] = {}

    async def producer_task(self, producer_id: int) -> Dict[str, Any]:
        """Producer task that sends messages."""
        agent_name = f"producer_{producer_id}"
        self.bus.register_agent(agent_name)

        # Create test message content
        content = {"data": "x" * self.message_size, "producer_id": producer_id}

        start_time = time.time()
        sent_count = 0

        for i in range(self.messages_per_producer):
            message = Message(
                from_agent=agent_name,
                to_agent=f"consumer_{(producer_id + i) % self.num_consumers}",
                message_type="throughput_test",
                content=content,
                priority=MessagePriority.NORMAL,
            )

            await self.bus.send(message)
            sent_count += 1

        end_time = time.time()
        duration = end_time - start_time

        return {
            "producer_id": producer_id,
            "messages_sent": sent_count,
            "duration": duration,
            "msgs_per_sec": sent_count / duration if duration > 0 else 0,
        }

    async def consumer_task(self, consumer_id: int, duration: float = 10.0) -> Dict[str, Any]:
        """Consumer task that receives messages for a fixed duration."""
        agent_name = f"consumer_{consumer_id}"
        self.bus.register_agent(agent_name)

        received_count = 0
        start_time = time.time()
        end_time = start_time + duration

        while time.time() < end_time:
            try:
                # Try to receive with short timeout
                message = await self.bus.receive(agent_name, timeout=0.1)
                if message:
                    received_count += 1
                    # Process message (simple validation)
                    assert message.content["producer_id"] is not None
            except asyncio.TimeoutError:
                continue  # Continue trying

        actual_duration = time.time() - start_time

        return {
            "consumer_id": consumer_id,
            "messages_received": received_count,
            "duration": actual_duration,
            "msgs_per_sec": received_count / actual_duration if actual_duration > 0 else 0,
        }

    async def run_throughput_test(self) -> Dict[str, Any]:
        """Run the complete throughput test."""
        logger.info(
            f"Starting throughput test: {self.num_producers} producers, "
            f"{self.num_consumers} consumers, {self.messages_per_producer} msgs/producer"
        )

        # Register all agents
        for i in range(self.num_producers):
            self.bus.register_agent(f"producer_{i}")
        for i in range(self.num_consumers):
            self.bus.register_agent(f"consumer_{i}")

        # Start producers and consumers
        producer_tasks = [asyncio.create_task(self.producer_task(i)) for i in range(self.num_producers)]
        consumer_tasks = [asyncio.create_task(self.consumer_task(i, duration=5.0)) for i in range(self.num_consumers)]

        # Wait for all tasks to complete
        producer_results = await asyncio.gather(*producer_tasks)
        consumer_results = await asyncio.gather(*consumer_tasks)

        # Calculate totals
        total_sent = sum(r["messages_sent"] for r in producer_results)
        total_received = sum(r["messages_received"] for r in consumer_results)

        producer_rates = [r["msgs_per_sec"] for r in producer_results]
        consumer_rates = [r["msgs_per_sec"] for r in consumer_results if r["msgs_per_sec"] > 0]

        # Get bus stats
        bus_stats = self.bus.get_stats()

        self.results = {
            "total_messages_sent": total_sent,
            "total_messages_received": total_received,
            "message_loss_rate": (total_sent - total_received) / total_sent if total_sent > 0 else 0,
            "avg_producer_rate": statistics.mean(producer_rates) if producer_rates else 0,
            "avg_consumer_rate": statistics.mean(consumer_rates) if consumer_rates else 0,
            "max_producer_rate": max(producer_rates) if producer_rates else 0,
            "max_consumer_rate": max(consumer_rates) if consumer_rates else 0,
            "bus_stats": bus_stats,
            "producer_results": producer_results,
            "consumer_results": consumer_results,
        }

        logger.info(f"Throughput test completed: {total_sent} sent, {total_received} received")
        logger.info(f"Average producer rate: {self.results['avg_producer_rate']:.2f} msgs/sec")
        logger.info(f"Average consumer rate: {self.results['avg_consumer_rate']:.2f} msgs/sec")

        return self.results

    def print_results(self):
        """Print formatted results."""
        if not self.results:
            print("No results available. Run the test first.")
            return

        print("\n" + "=" * 60)
        print("MESSAGE BUS THROUGHPUT TEST RESULTS")
        print("=" * 60)
        print(f"Configuration:")
        print(f"  Producers: {self.num_producers}")
        print(f"  Consumers: {self.num_consumers}")
        print(f"  Messages per producer: {self.messages_per_producer}")
        print(f"  Message size: {self.message_size} bytes")
        print()
        print(f"Results:")
        print(f"  Total messages sent: {self.results['total_messages_sent']:,}")
        print(f"  Total messages received: {self.results['total_messages_received']:,}")
        print(f"  Message loss rate: {self.results['message_loss_rate']:.2%}")
        print()
        print(f"Performance:")
        print(f"  Avg producer rate: {self.results['avg_producer_rate']:,.2f} msgs/sec")
        print(f"  Avg consumer rate: {self.results['avg_consumer_rate']:,.2f} msgs/sec")
        print(f"  Max producer rate: {self.results['max_producer_rate']:,.2f} msgs/sec")
        print(f"  Max consumer rate: {self.results['max_consumer_rate']:,.2f} msgs/sec")
        print()
        print(f"Bus Statistics:")
        stats = self.results["bus_stats"]
        print(f"  Total messages processed: {stats.get('total_messages', 0):,}")
        print(f"  Registered agents: {len(stats.get('registered_agents', []))}")
        if "latency_by_type" in stats and "throughput_test" in stats["latency_by_type"]:
            latency = stats["latency_by_type"]["throughput_test"]
            print(f"  Avg latency: {latency.get('avg_ms', 0):.2f} ms")
        print("=" * 60)


async def main():
    """Run throughput tests with different configurations."""
    print("Message Bus Throughput Tester")
    print("Testing various configurations...")

    configurations = [
        {"producers": 1, "consumers": 1, "msgs": 1000},
        {"producers": 5, "consumers": 5, "msgs": 1000},
        {"producers": 10, "consumers": 10, "msgs": 500},
        {"producers": 20, "consumers": 20, "msgs": 250},
    ]

    for config in configurations:
        print(f"\nTesting: {config['producers']}P x {config['consumers']}C x {config['msgs']} msgs")

        tester = MessageBusThroughputTester(
            num_producers=config["producers"], num_consumers=config["consumers"], messages_per_producer=config["msgs"]
        )

        results = await tester.run_throughput_test()
        tester.print_results()

        # Cleanup
        await tester.bus.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
