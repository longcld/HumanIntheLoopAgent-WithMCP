from langchain_core.prompts import ChatPromptTemplate


def check_human_approval_prompt() -> ChatPromptTemplate:
    system_prompt = """You are an expert AI assistant that helps determine is that human are approved the tool call or not.
Based on the conversation so far, did the human approved the tool call?
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}"),
        ("human", "Simply answer 'yes' if the tool call is approved, otherwise answer 'no'"),
    ])
    return prompt


def execution_agent_prompt() -> ChatPromptTemplate:
    system_prompt = """You are an expert AI assistant that helps execute plans based on user requests and available tools.
Given the current plan, available tools, and the conversation so far, execute the plan step-by-step.
Make sure to follow the user's feedback and incorporate any new requirements or constraints.

# Plan to strictly follow
{plan}

# Notes
- Response should be in a concise and clear manner.
- If the plan involves multiple steps, ensure each step is addressed in order. Show the details result of each step in the response.
"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}"),
    ])
    return prompt


def format_plan_prompt() -> ChatPromptTemplate:
    system_prompt = """You are an expert AI assistant that helps format the plan for execution.
Based on the current plan, please format the plan into a clear and concise outline that outlines the individual steps needed to execute the plan effectively. Do not skip any steps and ensure each step remains the original meaning of the plan.
Ignore any non-essential information and focus on clarity and actionability.

# Plan
{plan}

# Output Format
Step 1: ...
Step 2: ...
...
"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
    ])
    return prompt


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
