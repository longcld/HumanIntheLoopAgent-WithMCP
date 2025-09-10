from MCP.clients.manager import mcp_client_manager
from langchain_core.utils.function_calling import convert_to_openai_function


def get_tool_descriptions():
    """Get tool descriptions from MCP client manager."""
    if mcp_client_manager.tools:
        return [convert_to_openai_function(tool) for tool in mcp_client_manager.tools]
    return []

def get_tools():
    """Get tools from MCP client manager."""
    return mcp_client_manager.tools