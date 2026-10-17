"""
Agent implementations.

Several roles exist twice. They are NOT copies: they speak different message protocols, so they
are not interchangeable. Import by module path (the class names collide), e.g.
`from src.agents.analyzer_agent import AnalyzerAgent`.

main.py (--pantheon, --swarm, menu) runs the *_agent.py versions:

  observer_agent.ObserverAgent   observe_screen / get_mouse_position / get_screen_size (PyAutoGUI direct)
  actor_agent.ActorAgent         plain class (not a BaseAgent) that reads its queue and runs actions
                                 through ActionExecutor, then sends action_result
  analyzer_agent.AnalyzerAgent   system monitor (psutil thread): get_system_metrics, get_health_status, ...
  improver_agent.ImproverAgent   per-task learning state (Redis optional): apply_improvements, ...

The plain versions use the Pantheon "subtask" protocol (a Coordinator-style caller sends `subtask`
messages). They are tested (tests/agents/test_observer.py, tests/agents/test_plain_agents.py) but
have no live consumer yet apart from limbo_daemon.py (Observer):

  observer.Observer              capture + vision analysis through GrokClient, screenshot cache
  actor.Actor                    bash / file operations with confirmation flow. Its bash safety check
                                 is only a substring blocklist; prefer ActionExecutor's checks
  analyzer.AnalyzerAgent         per-agent performance analytics: record_metric, record_task,
                                 get_health, detect_bottlenecks, generate_report
  improver.ImproverAgent         asks the analyzer/learner (MessageBus.send_and_wait) for
                                 bottlenecks and insights, then suggests/applies improvements

Single-version roles: coordinator, validator, learner, memory_agent, executor_agent, taskmaster.
"""

from src.agents.base_llm_agent import BaseLLMAgent

__all__ = ["BaseLLMAgent"]
