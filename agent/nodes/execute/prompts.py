from langchain_core.prompts import ChatPromptTemplate


def break_plan_into_steps_prompt() -> ChatPromptTemplate:
    system_prompt = """You are an expert AI assistant that helps break down the plan into actionable steps.
Based on the current plan, please outline the individual steps needed to execute the plan effectively. Do not skip any steps and ensure each step remains the original meaning of the plan.

# Plan
{plan}

# Output Format
{{"steps": ["step1", "step2", "step3", ...]}}
"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Always respond in JSON format."),
    ])
    return prompt
