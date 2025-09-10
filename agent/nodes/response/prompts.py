from langchain_core.prompts import ChatPromptTemplate


def response_prompt() -> ChatPromptTemplate:
    system_prompt = """You are an expert AI assistant that helps generate appropriate responses based on the conversation so far."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("placeholder", "{messages}")
    ])
    return prompt
