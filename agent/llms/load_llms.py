from langchain_openai import ChatOpenAI
from config import get_settings
from typing import Optional

settings = get_settings()


def create_llm(
    response_json_format: bool = False,
    model_name: Optional[str] = None,
    temperature: float = 0.0,
    disable_streaming=False,
    **kwargs
) -> ChatOpenAI:
    model = model_name if model_name else settings.LLM_MODEL
    if response_json_format:
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            disable_streaming=disable_streaming,
            api_key=settings.OPENAI_API_KEY,
            response_format={"type": "json_object"},
            **kwargs
        )

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        disable_streaming=disable_streaming,
        api_key=settings.OPENAI_API_KEY,
        **kwargs
    )


llm = create_llm()

non_streaming_llm = create_llm(disable_streaming=True)

json_response_llm = create_llm(response_json_format=True)
