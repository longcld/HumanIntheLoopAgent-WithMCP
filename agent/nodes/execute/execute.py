from langgraph.graph import StateGraph, END
from loguru import logger
from ...states import ExecutionState as State
from agent.llms.llm import llm, json_response_llm
from .prompts import break_plan_into_steps_prompt, execution_agent_prompt
import json
from utils.mcp_helpers import get_tools
from .tool import tool_node


# def break_plan_into_steps(plan: str) -> list[str]:
#     prompt = break_plan_into_steps_prompt()
#     chain = prompt | json_response_llm

#     response = chain.invoke({
#         'plan': plan
#     })
#     steps = json.loads(response.content)['steps']
#     logger.debug(f'Plan broken down into steps: {steps}')
#     return steps


async def execute_node(state):

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
        }
    else:
        return {
            "is_tool_calling": False,
            "tool_message": None,
        }


def should_continue(state):
    if state.get("is_tool_calling", False):
        return "yes"
    else:
        return "no"


def get_execute_graph():
    """Get execute graph with lazy loading."""

    workflow = StateGraph(State)

    workflow.add_node("Execution", execute_node)
    workflow.add_node("tools", tool_node)

    workflow.set_entry_point("Execution")

    # We now add a conditional edge
    workflow.add_conditional_edges(
        "Execution",
        should_continue,
        {
            # If `tools`, then we call the tool node.
            "yes": "tools",
            # Otherwise we finish and go to reflection
            "no": END,
        },
    )

    workflow.add_edge("tools", "Execution")

    graph = workflow.compile()

    return graph.with_config({"run_name": "Execution Agent Graph"})


async def node(state):
    logger.debug('*** Entered Execute Node ***')

    # plan = state.plan
    # steps = state.steps
    # current_step = state.current_step

    # if not steps:
    #     logger.debug('No steps found, breaking down the plan into steps.')
    #     steps = break_plan_into_steps(plan)

    # logger.info(
    #     f'Executing Step {current_step + 1}/{len(steps)}: {steps[current_step]}')
    # # Ask for human confirmation before proceeding to the next step

    execute_graph = get_execute_graph()
    response = await execute_graph.ainvoke({
        "plan": state.get("current_plan", ""),
        **state
    })

    logger.debug(f"Execution Response: {response}")

    return {
        # 'steps': steps,
        'previous_node': 'Execute',
        'next_node': 'END'
    }
