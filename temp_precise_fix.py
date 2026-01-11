lines = []
with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if line.strip().startswith('def main('):
        # Replace the entire def line
        new_line = 'def main(task, max_iterations, max_rounds, debug, skip_boot, provider, model, swarm, agent_roles, messagebus, pantheon, providers, maf_config, review_mode, analytics, agent_name, limit, performance, list_models, syntax_check, quick_check, mcp, todo_daemon: bool = False, distributed: bool = False, process_id: str = "main", connect_to: Optional[str] = None, grok4git: bool = False, archetype_mode: str = "thoth"):\n'
        lines[i] = new_line
        break

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Precise fix applied')