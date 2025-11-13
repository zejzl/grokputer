# Magic Module Documentation - Grokputer (Artemis Fowl Inspired)

## Overview
`src/magic.py` simulates fairy \"magic\" from the *Artemis Fowl* series, reimagined as \"forgotten science.\" It integrates with Grokputer's agents for error recovery, performance boosts, and thematic rituals. Core elements:
- **Blue Spark**: Holly Short's healing energy – fixes errors (e.g., API failures) with DPO learning.
- **Acorn Vitality**: Herbal \"želod\" boosts (from Slovenian lore) – enhances agent params (e.g., lower temperature for focus).
- **Fairy Shield**: LEP protection – activates security/mesmerization.
- **Rituals**: Performative invocations for luck, oaths, and maintenance.
- **Daemon Mode**: Background loop for periodic rituals (recharge, shield, blessings) – runs indefinitely in Docker for persistent \"magic maintenance.\"

Magic depletes/recharges like fairy energy (max 100%). Acorns provide herbal tie-ins for vitality (5 reserves by default). Logs to console for transparency.

**Inspiration**: Holly's blue sparks (healing/mesmer), acorn/oak folklore (strength, protection), and fairy tech-magic hybrid. Enhances self-improvement (DPO prefs from outcomes).

## FairyMagic Class
Central class for magic operations. Instantiate: `magic = FairyMagic(energy_level=100.0)`.

### Key Methods
- **`recharge_magic(acorn_boost=False) -> float`**: Restores energy (10-20 base +15 from acorn). Simulates post-heal recovery. Returns new energy level.
- **`blue_spark_heal(target: str, issue: str) -> bool`**: Heals errors (85%+ success based on energy). Costs 15 energy. Collects DPO preferences if coordinator target. E.g., `magic.blue_spark_heal("coordinator", "Claude API error")`.
- **`acorn_vitality_boost(agent: Coordinator) -> Dict`**: Boosts agent (1.1-1.5x factor, tweaks params like temperature/max_tokens). Costs 1 acorn. Logs infusion.
- **`fairy_shield(activate=True) -> bool`**: Toggles protection (costs 10 to activate, +5 recharge on deactivate). Protects against \"Mud People\" (humans/threats).
- **`perform_ritual(ritual_type: str, target_file: Optional[str]=None) -> str`**: Executes themed rituals. Enhances vault files if specified (e.g., \"enchanted with oak magic\").

### Rituals List
- **`acorn_divination`**: Random prophecy (e.g., \"Luck ahead!\" or \"Beware trolls!\").
- **`holly_blessing`**: \"Blue spark blesses task - 100% success aura!\"
- **`fairy_oath`**: \"By the Book, I swear loyalty to the People.\"
- **`daemon_recharge`** (new): \"Periodic recharge: Magic energy restored to full via acorn vitality.\" – Calls `recharge_magic(acorn_boost=True)`.
- **`shield_maintenance`** (new): \"Fairy shield patrolled - protections renewed against Mud threats.\" – Calls `fairy_shield(True)`.

Unknown rituals return: \"Unknown ritual. Consult the Book.\"

- **`daemon_ritual_loop(interval: int=300)`** (async): Infinite background loop. Randomly picks from `["daemon_recharge", "shield_maintenance", "holly_blessing"]`, logs/performs, sleeps (default 5 min). For daemon mode.

## Integration with Grokputer
- **Hook Function**: `integrate_magic_with_coordinator(coordinator: Coordinator)` – Pre-task acorn boost + error handling (heal/retry or recharge).
- **In main.py**:
  - Imports: `from src.magic import FairyMagic, integrate_magic_with_coordinator`.
  - On boot: Initializes `magic = FairyMagic()`, calls integration.
  - Post-task: `magic.recharge_magic(acorn_boost=True)`.
- **NLI/Coordinator Tie-In**: Use in agents for auto-heal (e.g., on Claude errors). DPO learns from heals (preferred: healed_state).

## Daemon Mode
Persistent background execution for system maintenance – like a fairy \"daemon\" (Mulch Diggums vibe?).
- **Flag**: `--daemon` in `main.py`. Starts `asyncio.create_task(magic.daemon_ritual_loop())`. Supports `--task --daemon` (task first, then loop).
- **Behavior**: Cycles rituals every `interval` seconds (env: `DAEMON_INTERVAL`). Keeps energy high, shields active. Graceful shutdown on SIGTERM.
- **Logs Example**:
  ```
  Daemon ritual: Periodic recharge: Magic energy restored to full via acorn vitality.
  Acorn vitality infused - extra spark!
  Energy: 100.0%
  Daemon ritual: Fairy shield patrolled - protections renewed against Mud threats.
  Fairy shield activated.
  ```
- **Customization**: Override interval via env var. Add more rituals to loop list.

## Usage Examples
- **Single Ritual**: 
  ```python
  from src.magic import FairyMagic
  magic = FairyMagic()
  print(magic.perform_ritual("holly_blessing", "noisy_image.png"))  # "Blue spark blesses task - 100% success aura! Enchanted noisy_image.png with oak magic."
  ```
- **Local Daemon**:
  ```bash
  python main.py --daemon --debug  # Runs forever; Ctrl+C stops.
  python main.py --task "OCR vault" --daemon  # Task + daemon.
  ```
- **With Task**:
  ```python
  # In coordinator or NLI
  if error: magic.blue_spark_heal("tool_call", str(error))
  boost = magic.acorn_vitality_boost(coordinator)
  coordinator.update_params(boost["new_params"])
  ```

## Docker Setup for Daemon Instance
- **Dockerfile**: Default CMD: `["python", "main.py", "--daemon"]`. ENTRYPOINT `entrypoint.sh` passes args (`exec "$@"`).
- **docker-compose.yml** (daemon service):
  ```yaml
  daemon:
    build: .
    command: python main.py --daemon
    restart: always
    ports: ["8080:8080"]  # Logs/dashboard
    volumes: ["./logs:/app/logs", "./vault:/app/vault"]
    environment: {DAEMON_INTERVAL: "300"}
  ```
- **Run**:
  ```bash
  docker-compose up daemon  # Persistent rituals.
  docker logs <container>  # Monitor cycles.
  docker-compose down  # Stop.
  ```
- **Build/Test**: `docker build -t grokputer-daemon .` then run. Volumes persist logs/vault state.

## Limitations & Future
- **Energy/Acorns**: Finite; daemon recharges but monitor reserves (forage via vault tasks?).
- **Async**: Loop is non-blocking; integrate with event loop in multi-agent.
- **Extensions**: Add MCP tool calls in rituals (e.g., bash for \"divination\"). Tie to OCR for \"enchanting\" images. LoRA fine-tune on ritual outcomes.
- **Cautions**: Rituals are fun/simulated – no real magic! For production, add metrics (Prometheus).

Updated: Nov 12, 2024 (Daemon mode added). See `src/magic.py` for code. Questions? Invoke a ritual!"
