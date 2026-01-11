with open('main.py', 'r', encoding='utf-8') as f: content = f.read()

# Fix the def main line
old_def = 'def main('
new_def = 'def main(task, max_iterations, max_rounds, debug, skip_boot, provider, model, swarm, agent_roles, messagebus, pantheon, providers, maf_config, review_mode, analytics, agent_name, limit, performance, list_models, syntax_check, quick_check, mcp, todo_daemon: bool = False, distributed: bool = False, process_id: str = "main", connect_to: Optional[str] = None, grok4git: bool = False, archetype_mode: str = "thoth"):'
content = content.replace(old_def + 'task, max_iterations, max_rounds, debug, skip_boot, provider, model, swarm, agent_roles, messagebus, pantheon, providers, maf_config, review_mode, analytics, agent_name, limit, performance, list_models, syntax_check, quick_check, mcp, todo_daemon: bool = False, distributed: bool = False, process_id: str = "main", connect_to: Optional[str] = None, grok4git: bool = False):', new_def)

# Add the click option if not present
if '@click.option("--archetype-mode"' not in content:
    command_line = '@click.command()'
    option_line = '@click.option("--archetype-mode", default="thoth", help="Archetype mode for visionary agent (nobody/thoth)")'
    content = content.replace(command_line, command_line + '\n' + option_line)

# Fix _run_swarm_mode def
old_swarm_def = 'async def _run_swarm_mode(task: str, agent_roles: list, debug: bool, analytics: bool = False):'
new_swarm_def = 'async def _run_swarm_mode(task: str, agent_roles: list, debug: bool, analytics: bool = False, archetype_mode: str = "thoth"):'
content = content.replace(old_swarm_def, new_swarm_def)

# Fix the call in main
old_call = 'asyncio.run(_run_swarm_mode(task, roles, debug, analytics))'
new_call = 'asyncio.run(_run_swarm_mode(task, roles, debug, analytics, archetype_mode))'
content = content.replace(old_call, new_call)

# Add visionary agent creation
agent_section = '        if role == "coordinator":\n            agent = Coordinator(\n                message_bus=message_bus,\n                session_logger=session_logger,\n                config=None,  # Use default config with decomposition_prompt\n            )\n        else:\n            logger.warning(f"[SWARM] Unknown agent role: {role}, using stub")\n            agent_task = asyncio.create_task(\n                _stub_agent(\n                    agent_id=role,\n                    task=task,\n                    message_bus=message_bus,\n                    action_executor=action_executor,\n                    deadlock_detector=deadlock_detector,\n                    session_logger=session_logger,\n                )\n            )\n            agent_tasks.append(agent_task)\n            continue'
new_agent_section = '        if role == "coordinator":\n            agent = Coordinator(\n                message_bus=message_bus,\n                session_logger=session_logger,\n                config=None,  # Use default config with decomposition_prompt\n            )\n        elif role == "visionary":\n            agent = VisionaryAgent(\n                agent_id=role, message_bus=message_bus, session_logger=session_logger, config=agent_config, archetype_mode=archetype_mode\n            )\n        else:\n            logger.warning(f"[SWARM] Unknown agent role: {role}, using stub")\n            agent_task = asyncio.create_task(\n                _stub_agent(\n                    agent_id=role,\n                    task=task,\n                    message_bus=message_bus,\n                    action_executor=action_executor,\n                    deadlock_detector=deadlock_detector,\n                    session_logger=session_logger,\n                )\n            )\n            agent_tasks.append(agent_task)\n            continue'
content = content.replace(agent_section, new_agent_section)

with open('main.py', 'w', encoding='utf-8') as f: f.write(content)

print('Fixed main.py')