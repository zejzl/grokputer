"""Regression test: ActorAgent must register itself on the MessageBus when constructed."""
from unittest.mock import Mock

from src.agents.actor_agent import ActorAgent
from src.core.message_bus import MessageBus
from src.observability.deadlock_detector import DeadlockDetector


def test_actor_registers_on_bus_and_detector():
    bus = MessageBus()
    detector = DeadlockDetector()
    actor = ActorAgent(agent_id="actor", message_bus=bus, session_logger=Mock(), deadlock_detector=detector)

    assert "actor" in bus.queues
    assert "actor" in detector.agent_states
    assert actor.is_healthy() is True


def test_actor_does_not_double_register():
    bus = MessageBus()
    bus.register_agent("actor")
    ActorAgent(agent_id="actor", message_bus=bus, session_logger=Mock())
    assert list(bus.queues).count("actor") == 1
