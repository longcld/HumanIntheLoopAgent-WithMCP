
from utils.llm import llm, non_streaming_llm
from .prompts import get_is_need_plan_prompt

from loguru import logger


def node(state):
    logger.debug('*** Entered Orchestrate Node ***')
    logger.info(state)
    previous_node = state['previous_node']

    if previous_node == None:
        need_plan_chain = get_is_need_plan_prompt() | non_streaming_llm
        response = need_plan_chain.invoke({
            'messages': state['messages']
        })

        need_plan = response.content.strip().lower() == 'yes'
        if need_plan:
            logger.debug('Need Plan Detected *** Routing to Plan Node ***')
            return {'next_node': 'Plan'}
        else:
            logger.debug('No Plan Needed *** Routing to Response Node ***')
            return {'next_node': 'Response'}
    elif previous_node == 'Plan':
        logger.debug('Continuing in Plan Node')
        return {'next_node': 'Plan'}
    else:
        logger.debug(
            f'Unhandled previous node: {previous_node}. Routing to Response Node by default.'
        )
        return {'next_node': 'Response'}
