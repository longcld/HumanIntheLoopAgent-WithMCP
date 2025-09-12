from loguru import logger
from agent.llms import llm
from .prompts import response_prompt


def node(state):
    logger.debug('*** Entered Response Node ***')

    response_chain = response_prompt() | llm
    response = response_chain.invoke({
        'messages': state['messages']
    })

    logger.info(f'Final Response Generated:\n{response.content.strip()}')
    return {
        'previous_node': None,
        'next_node': 'END'
    }
