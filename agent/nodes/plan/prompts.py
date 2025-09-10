from langchain_core.prompts import ChatPromptTemplate

def is_need_to_refine_plan_prompt() -> ChatPromptTemplate:
    system_prompt = """You are an expert AI assistant that helps determine if the current plan needs refinement based on the conversation so far.
Based on the conversation so far and the existing plan, do you need to refine or update the plan? Answer with a simple 'yes' or 'no'.
"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}"),
        ("human", "Simply answer 'yes' if the plan needs refinement, otherwise answer 'no'"),
    ])
    return prompt


def initial_plan_prompt() -> ChatPromptTemplate:
    system_prompt = """You are an expert AI assistant that helps create detailed plans based on user requests.
Given the user's request, available tools, and the conversation so far, create a comprehensive plan outlining the steps needed to fulfill the request.
Ensure the plan is clear, actionable, and considers the context of the conversation. Specify the tools to be used in each step.

# Tools
{tools}

Then, after created the plan, ask the user for confirmation and feedback.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}"),
    ])

    return prompt


def refine_plan_prompt() -> ChatPromptTemplate:
    system_prompt = """You are an expert AI assistant that helps refine and improve existing plans based on new information or changes in the conversation.
Given the current plan, available tools, and the conversation so far, update and enhance the plan to ensure it remains relevant and effective.
Make sure to follow the user's feedback and incorporate any new requirements or constraints. Specify the tools to be used in each step.

# Tools
{tools}

Then, after created the plan, ask the user for confirmation and feedback.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}"),
    ])

    return prompt
