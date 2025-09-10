from langchain_core.prompts import ChatPromptTemplate


def get_is_need_plan_prompt() -> ChatPromptTemplate:
    system_prompt = """You are an expert AI assistant that helps determine if a plan is needed for the given conversation.
Based on the conversation so far, do you need to create a plan for the next steps? Answer with a simple 'yes' or 'no'.
Always need to create a plan when user request to do something.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}"),
        ("human", "Simply answer 'yes' if a plan is needed, otherwise answer 'no'"),
    ])

    return prompt
