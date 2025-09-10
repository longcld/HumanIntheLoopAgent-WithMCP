from loguru import logger
from utils.llm import json_response_llm as llm
from .prompts import break_plan_into_steps_prompt
import json


def break_plan_into_steps(plan: str) -> list[str]:
    prompt = break_plan_into_steps_prompt()
    chain = prompt | llm

    response = chain.invoke({
        'plan': plan
    })
    steps = json.loads(response.content)['steps']
    logger.debug(f'Plan broken down into steps: {steps}')
    return steps


def node(state):
    logger.debug('*** Entered Execute Node ***')

    plan = state.plan
    steps = state.steps
    current_step = state.current_step

    if not steps:
        logger.debug('No steps found, breaking down the plan into steps.')
        steps = break_plan_into_steps(plan)

    logger.info(
        f'Executing Step {current_step + 1}/{len(steps)}: {steps[current_step]}')
    # Ask for human confirmation before proceeding to the next step

    return {
        'steps': steps,
        'previous_node': 'Execute',
        'next_node': 'END'
    }
