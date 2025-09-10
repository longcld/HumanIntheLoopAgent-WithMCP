from langgraph.graph import StateGraph, END

from ..nodes import (
    orchestate_node,
    plan_node,
    execute_node,
    response_node
)

from ..states import State
from loguru import logger

# define the nodes
workflow = StateGraph(State)
workflow.add_node('Orchestrate', orchestate_node)
workflow.add_node('Plan', plan_node)
workflow.add_node('Execute', execute_node)
workflow.add_node('Response', response_node)

# add entrypoint
workflow.set_entry_point("Orchestrate")

# define the edges
workflow.add_conditional_edges(
    "Orchestrate",
    lambda x: x["next_node"],
    {
        "Plan": "Plan",
        "Response": "Response",
        "Execute": "Execute",
    }
)

workflow.add_conditional_edges(
    "Plan",
    lambda x: x["next_node"],
    {
        "END": END,
        "Execute": "Execute",
        # "Response": "Response",
    }
)

workflow.add_edge("Response", END)
workflow.add_edge("Execute", END)

graph = workflow.compile()
