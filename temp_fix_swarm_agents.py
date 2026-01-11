with open('main.py', 'r', encoding='utf-8') as f: content = f.read()

# Find the agent creation section in _run_swarm_mode
section_start = 'for role in agent_roles:'
section_end = '        agent_task = asyncio.create_task('

agent_block = content.split(section_start)[1].split(section_end)[0]

# Replace the if-elif chain with added visionary
old_chain = '''
        if role == "observer":
            agent = ObserverAgent(
                agent_id=role, message_bus=message_bus, session_logger=session_logger, config=agent_config
            )
        elif role == "actor":
            agent = ActorAgent(
                agent_id=role, message_bus=message_bus, session_logger=session_logger, config=agent_config
            )
        elif role == "coordinator":
            agent = Coordinator(
                message_bus=message_bus,
                session_logger=session_logger,
                config=None,  # Use default config with decomposition_prompt
            )
        else:
            logger.warning(f"[SWARM] Unknown agent role: {role}, using stub")
            agent_task = asyncio.create_task(
'''

new_chain = '''
        if role == "observer":
            agent = ObserverAgent(
                agent_id=role, message_bus=message_bus, session_logger=session_logger, config=agent_config
            )
        elif role == "actor":
            agent = ActorAgent(
                agent_id=role, message_bus=message_bus, session_logger=session_logger, config=agent_config
            )
        elif role == "coordinator":
            agent = Coordinator(
                message_bus=message_bus,
                session_logger=session_logger,
                config=None,  # Use default config with decomposition_prompt
            )
        elif role == "visionary":
            agent = VisionaryAgent(
                agent_id=role, message_bus=message_bus, session_logger=session_logger, config=agent_config, archetype_mode=archetype_mode
            )
        else:
            logger.warning(f"[SWARM] Unknown agent role: {role}, using stub")
            agent_task = asyncio.create_task(
'''

content = content.replace(old_chain, new_chain)

with open('main.py', 'w', encoding='utf-8') as f: f.write(content)

print('Swarm agent creation fixed')