from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from langchain_core.messages import AIMessage, HumanMessage

from langfuse.langchain import CallbackHandler

from agent.graphs.orchestrator import graph

from app.schemas.chat_request import ChatRequest
from app.schemas.message import Message

import uuid
from utils import convert_to_sse_format
from loguru import logger

# Create a router instance
router = APIRouter()


# Define routes within the router
@router.post("/astream")
async def astream(
    request: ChatRequest
):
    logger.debug(f"Received request: {request}")

    # Prepare inputs similar to the Streamlit app
    messages = []

    # Convert conversation history to LangChain messages
    if request.messages:
        for msg in request.messages:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))

    # Add the current message if it's not already in the history
    current_message = HumanMessage(content=request.message)
    if not messages or messages[-1].content != request.message:
        messages.append(current_message)

    inputs = {
        "messages": messages,
        "session_id": request.session_id,
        "previous_node": request.previous_node,
        "current_plan": request.current_plan or ""
    }

    langfuse_handler = CallbackHandler()

    async def wrapped_streaming_tokens():
        full_response = ""
        current_node = None

        # Send initial status
        yield convert_to_sse_format({
            "content": "Agent is thinking...",
            "type": "status",
            "node": "starting"
        })

        try:
            # Stream response from graph similar to Streamlit app
            async for subgraph, mode, state in graph.astream(
                inputs,
                subgraphs=True,
                stream_mode=["messages", "values"],
                config={"callbacks": [langfuse_handler]}
            ):

                if mode == "values":
                    # Handle state updates
                    current_plan = state.get("current_plan", "")
                    if current_plan:
                        yield convert_to_sse_format({
                            "content": f"Plan updated: {current_plan}",
                            "type": "plan",
                            "node": "Plan"
                        })

                    # Update previous_node
                    previous_node = state.get("previous_node", None)
                    if previous_node:
                        current_node = previous_node

                elif mode == "messages":
                    msg, metadata = state

                    node = metadata.get("langgraph_node", "Unknown")

                    # # Send node change notification
                    # if current_node != node:
                    #     yield convert_to_sse_format({
                    #         "content": f"**[{node}]**",
                    #         "type": "node_change",
                    #         "node": node
                    #     })
                    #     current_node = node

                    is_stream = "check" not in node.lower()
                    is_stream = is_stream and node.lower() != "orchestrate"
                    if is_stream:
                        # Send message content
                        if msg.content:
                            if isinstance(msg, AIMessage):
                                full_response += msg.content
                                yield convert_to_sse_format({
                                    "content": msg.content,
                                    "type": "message",
                                    "node": node,
                                    "full_response": full_response
                                })
                            else:
                                yield convert_to_sse_format({
                                    "content": msg.content,
                                    "type": "thinking",
                                    "node": node
                                })

            # Send completion signal
            yield convert_to_sse_format({
                "content": "Response complete",
                "type": "complete",
                "full_response": full_response
            })

        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            yield convert_to_sse_format({
                "content": f"Error: {str(e)}",
                "type": "error"
            })

    return StreamingResponse(
        wrapped_streaming_tokens(),
        media_type="text/event-stream",
        headers={
            "X-Content-Type-Options": "nosniff",
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive"
        }
    )
