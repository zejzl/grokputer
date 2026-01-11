with open('main.py', 'r', encoding='utf-8') as f: content = f.read()

# Add --archetype-mode option to main click command
if '--archetype-mode' not in content:
    new_click = content.split('@click.command()')[0] + '@click.command()\n@click.option("--archetype-mode", default="thoth", help="Archetype mode for visionary agent (nobody/thoth)")\n'
    content = new_click + content.split('@click.command()')[1]

# Update main function def to include archetype_mode
def_pattern = 'def main('
if 'archetype_mode' not in content.split(def_pattern)[1].split('):')[0]:
    def_line = def_pattern + ', archetype_mode: str = "thoth"'
    content = content.split(def_pattern)[0] + def_line + content.split(def_pattern)[1]

# Update _run_swarm_mode call in main
if 'await asyncio.run(_run_swarm_mode(' in content:
    swarm_call = '_run_swarm_mode(task, roles, debug, analytics, archetype_mode)'
    content = content.replace('_run_swarm_mode(task, roles, debug, analytics)', swarm_call)

# Update _run_swarm_mode def to include archetype_mode param
swarm_def = 'async def _run_swarm_mode(task: str, agent_roles: list, debug: bool, analytics: bool = False):'
new_swarm_def = swarm_def.replace('):', ', archetype_mode: str = "thoth"):')
content = content.replace(swarm_def, new_swarm_def)

# In agent creation for visionary
visionary_pattern = 'elif role == "visionary":'
if visionary_pattern in content:
    after = content.split(visionary_pattern)[1].split('\n')[0]
    new_visionary = f'{visionary_pattern}\n            agent = VisionaryAgent(\n                agent_id=role, message_bus=message_bus, session_logger=session_logger, config=agent_config, archetype_mode=archetype_mode\n            )'
    content = content.replace(visionary_pattern + '\n            agent = VisionaryAgent(\n                agent_id=role, message_bus=message_bus, session_logger=session_logger, config=agent_config\n            )', new_visionary)
else:
    # Add if visionary role
    agent_if = '        if role == "observer":\n            agent = ObserverAgent(\n'
    new_agent_if = agent_if + '        elif role == "visionary":\n            agent = VisionaryAgent(\n                agent_id=role, message_bus=message_bus, session_logger=session_logger, config=agent_config, archetype_mode=archetype_mode\n            )\n' + agent_if
    content = content.replace(agent_if, new_agent_if)

with open('main.py', 'w', encoding='utf-8') as f: f.write(content)