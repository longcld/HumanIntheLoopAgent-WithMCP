
from agent.states.state import State
from utils import extract_tag_text
from utils.llm import llm, non_streaming_llm
from utils.mcp_helpers import get_tool_descriptions
from loguru import logger

from .prompts import initial_plan_prompt, refine_plan_prompt, is_need_to_refine_plan_prompt
from ...states import PlanState as State
from langgraph.graph import StateGraph, END


def check_initial_plan_node(state):

    logger.debug('*** Checking if Initial Plan is Needed ***')

    current_plan = state.get('current_plan', '')
    if not current_plan:
        logger.debug('No Existing Plan Found *** Creating Initial Plan ***')
        return {
            "next_node": "Initial"
        }
    else:
        logger.debug(
            'Existing Plan Found *** Skipping Initial Plan Creation ***')
        return {
            "next_node": "CheckRefinement"
        }


def check_refinement_node(state):

    logger.debug('*** Checking if Plan Refinement is Needed ***')

    current_plan = state.get('current_plan', '')
    need_refine_chain = (
        is_need_to_refine_plan_prompt() | non_streaming_llm
    ).with_config({"run_name": "Check Plan Refinement"})

    response = need_refine_chain.invoke({
        'messages': state['messages'],
        'current_plan': current_plan
    })

    need_refine = response.content.strip().lower() == 'yes'
    if need_refine:
        logger.debug('Plan Refinement Needed *** Refining Plan ***')
        return {
            "next_node": "Refine",
            "is_approved": False
        }
    else:
        logger.debug('No Plan Refinement Needed *** Ending Plan Node ***')
        return {
            "next_node": "END",
            "is_approved": True
        }


def initial_plan_node(state):

    logger.debug('*** Entered Initial Plan Node ***')

    initial_plan_chain = initial_plan_prompt() | llm
    response = initial_plan_chain.invoke({
        'messages': state['messages'],
        'tools': get_tool_descriptions()
    })
    plan = extract_tag_text(response.content.strip(), "plan", first=True)
    logger.debug(f'Initial Plan Created:\n{plan}')

    return {
        'current_plan': plan,
        'previous_node': 'Plan',
        'next_node': 'END'
    }


def refine_plan_node(state):

    logger.debug('*** Entered Plan Refinement Node ***')

    current_plan = state.get('current_plan', '')
    refine_plan_chain = refine_plan_prompt() | llm
    response = refine_plan_chain.invoke({
        'messages': state['messages'],
        'tools': get_tool_descriptions(),
        'current_plan': current_plan
    })
    refined_plan = response.content.strip()
    refined_plan = extract_tag_text(refined_plan, "plan", first=True)
    logger.debug(f'Plan Refined:\n{refined_plan}')

    return {
        'current_plan': refined_plan,
        'previous_node': 'Plan',
        'next_node': 'END'
    }


def get_plan_graph():

    # define the nodes
    workflow = StateGraph(State)

    # add the nodes to the graph
    workflow.add_node("CheckInitial", check_initial_plan_node)
    workflow.add_node("CheckRefinement", check_refinement_node)
    workflow.add_node("Initial", initial_plan_node)
    workflow.add_node("Refine", refine_plan_node)

    # add entrypoint
    workflow.set_entry_point("CheckInitial")

    # define the edges
    workflow.add_conditional_edges(
        "CheckInitial",
        lambda x: x["next_node"],
        {
            "Initial": "Initial",
            "CheckRefinement": "CheckRefinement",
        }
    )

    workflow.add_conditional_edges(
        "CheckRefinement",
        lambda x: x["next_node"],
        {
            "Refine": "Refine",
            "END": END,
        }
    )

    workflow.add_edge("Initial", END)
    workflow.add_edge("Refine", END)

    graph = workflow.compile()

    return graph.with_config({"run_name": "Planning Graph"})


def node(state):
    logger.debug('*** Entered Plan Node ***')

    plan_graph = get_plan_graph()
    response = plan_graph.invoke(state)

    current_plan = response.get("current_plan", "")
    is_approved = response.get("is_approved", False)
    if is_approved:
        logger.debug(
            'Plan Approved *** Ending Plan Node *** Routing to Execute Node ***'
        )
        return {
            'current_plan': current_plan,
            'previous_node': 'Plan',
            'next_node': 'Execute'
        }
    return {
        'current_plan': current_plan,
        'previous_node': 'Plan',
        'next_node': 'END'
    }
