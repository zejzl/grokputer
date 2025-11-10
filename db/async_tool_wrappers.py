# Async wrappers for analytics_query and performance_monitor tools
# Add these to src/tools.py for async integration

import asyncio
from analytics_performance_tools import analytics_query, performance_monitor  # Import the sync functions

# Async wrapper for analytics_query
async def analytics_query_tool(params: dict) -> str:
    """
    Async tool for database analytics queries.

    Params:
        query_type: str ('summary', 'top_agents', 'agent_stats', 'roll_distribution')
        agent_name: str (optional, for 'agent_stats')
        limit: int (optional, default 10)

    Returns:
        str: Formatted query results
    """
    query_type = params.get('query_type')
    agent_name = params.get('agent_name')
    limit = params.get('limit', 10)

    if not query_type:
        return "Error: 'query_type' parameter required"

    # Run sync query in thread to avoid blocking
    result = await asyncio.to_thread(analytics_query, query_type, agent_name, limit)
    return result

# Async wrapper for performance_monitor
async def performance_monitor_tool(params: dict) -> str:
    """
    Async tool for performance monitoring.

    Params:
        mode: str ('snapshot' or 'reset', default 'snapshot')

    Returns:
        str: Formatted performance metrics
    """
    mode = params.get('mode', 'snapshot')

    # Run sync monitoring in thread
    result = await asyncio.to_thread(performance_monitor, mode)
    return result

# Example of how to add to src/config.py TOOLS dict:
# TOOLS = {
#     ...
#     "analytics_query": analytics_query_tool,
#     "performance_monitor": performance_monitor_tool,
#     ...
# }

# Also, ensure analytics_performance_tools.py is imported or the functions are available