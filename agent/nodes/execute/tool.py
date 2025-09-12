from langchain_core.messages import ToolMessage, convert_to_openai_messages
from langchain_core.runnables import RunnableConfig

from utils.mcp_helpers import get_tools

import json
import asyncio


async def tool_node(state):

    tool_map = {tool.name: tool for tool in get_tools()}
    tool_calls = []
    if state.get("tool_message"):
        tool_calls = state.get("tool_message").tool_calls.copy()

    async def run_tool(tool_call):
        """Run a single tool call."""
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]
        if tool_name not in tool_map:
            raise ValueError(f"Tool {tool_name} not found.")

        tool_result = await tool_map[tool_name].ainvoke(tool_args)

        return ToolMessage(
            content=json.dumps(tool_result, indent=2, ensure_ascii=False),
            name=tool_name,
            tool_call_id=tool_id,
        )

    tasks = [
        asyncio.create_task(run_tool(tool_call))
        for tool_call in tool_calls
    ]

    outputs = await asyncio.gather(*tasks)

    return {
        "tool_outputs": outputs,
        "previous_node": "ExecuteTool"
    }
