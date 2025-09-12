from langgraph.graph import StateGraph, END
from langgraph.config import get_stream_writer
from langchain_core.messages import AIMessage

from ...states import ExecutionState as State
from .prompts import execution_agent_prompt, check_human_approval_prompt
from .tool import tool_node
from agent.llms import llm
from utils.mcp_helpers import get_tools

from loguru import logger
import json


async def execute_node(state):

    current_step = state.get("current_step", 0)
    human_approval = state.get("human_approval", False)

    previous_node = state.get("previous_node", None)
    if "CheckHumanApproval" in previous_node:
        return {
            "next_node": "CheckHumanApproval",
        }

    # Normal execution flow
    chain = execution_agent_prompt() | llm.bind_tools(get_tools())

    input_messages = state.get("messages", [])
    if state.get("is_tool_calling", False) and state.get("tool_outputs", []):
        input_messages += [state["tool_message"]]
        input_messages += [msg for msg in state["tool_outputs"]]

    response = await chain.ainvoke(
        {
            **state,
            "messages": input_messages,
        }
    )

    if response.tool_calls:
        return {
            "is_tool_calling": True,
            "tool_message": response,
            "next_node": "CheckHumanApproval",
        }
    else:
        return {
            "is_tool_calling": False,
            "tool_message": None,
            "next_node": "END",
        }


def human_approval_node(state):
    logger.debug('*** Entered Human Approval Node ***')

    approval_status = state.get("approval_status", "not_requested")
    # If we don't have human approval yet, we yield the tool call details for review
    if approval_status == "not_requested":
        tool_message = state.get("tool_message", None).tool_calls.copy()

        # tool_calls = "\n".join([tool_call["name"] for tool_call in tool_message.tool_calls]) if tool_message and tool_message.tool_calls else "No tool calls."

        request_approval_messages = [
            json.dumps(tool_message, indent=2),
            "\nDo you approve the above tool call? (yes/no)"
        ]

        writer = get_stream_writer()
        for char in "\n".join(request_approval_messages):
            writer(AIMessage(content=char))

        return {
            "approval_status": "pending",
            "previous_node": "CheckHumanApproval",
            "next_node": "END"
        }
    elif approval_status == "pending":
        logger.debug("Human Approval Pending *** Checking Approval Status ***")
        human_approval_chain = check_human_approval_prompt() | llm
        response = human_approval_chain.invoke({
            'messages': state['messages']
        })
        approval = response.content.strip().lower() == 'yes'
        if approval:
            logger.debug(
                'Human Approval Granted *** Proceeding with Tool Execution ***')
            return {
                "approval_status": "approved",
                "previous_node": "CheckHumanApproval",
                "next_node": "ExecuteTool"
            }
        else:
            logger.debug('Human Approval Denied *** Ending Execution ***')
            return {
                "approval_status": "rejected",
                "previous_node": "CheckHumanApproval",
                "next_node": "LLM"
            }


def check_approval(state):
    if state.get("need_approval", False):
        return "yes"
    else:
        return "no"


def is_tool_calling(state):
    if state.get("is_tool_calling", False):
        return "yes"
    else:
        return "no"


def get_execute_graph():
    """Get execute graph with lazy loading."""

    workflow = StateGraph(State)

    workflow.add_node("LLM", execute_node)
    workflow.add_node("CheckHumanApproval", human_approval_node)
    workflow.add_node("ExecuteTool", tool_node)

    workflow.set_entry_point("LLM")

    # We now add conditional edges
    workflow.add_conditional_edges(
        "LLM",
        lambda x: x["next_node"],
        {
            "CheckHumanApproval": "CheckHumanApproval",
            "END": END
        }
    )

    workflow.add_conditional_edges(
        "CheckHumanApproval",
        lambda x: x["next_node"],
        {
            "ExecuteTool": "ExecuteTool",
            "LLM": "LLM",
            "END": END
        },
    )
    workflow.add_edge("ExecuteTool", "LLM")

    graph = workflow.compile(checkpointer=True)

    return graph.with_config({"run_name": "Execution Agent Graph"})


async def node(state):
    logger.debug('*** Entered Execute Node ***')

    execute_graph = get_execute_graph()
    response = await execute_graph.ainvoke({
        "plan": state.get("current_plan", ""),
        **state
    })

    logger.debug(f"Execution Response: {response}")
    previous_subnode = response.get("previous_node", "")
    previous_node = "Execute"
    if previous_subnode:
        previous_node = f"Execute->{previous_subnode}"
    return {
        'previous_node': previous_node,
        'next_node': 'END'
    }
