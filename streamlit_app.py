import streamlit as st
import os
from langchain_core.messages import AIMessage, HumanMessage
import json
import time
import requests
import sseclient
from loguru import logger
from uuid import uuid4

from config import get_settings
settings = get_settings()


class ControlledSpinner:
    def __init__(self, text="In progress..."):
        self.text = text
        self._spinner = None

    def _start(self):
        with st.spinner(self.text):
            yield

    def start(self):
        self._spinner = iter(self._start())
        next(self._spinner)  # Start the spinner

    def stop(self):
        if self._spinner:
            next(self._spinner, None)


# Configure Streamlit page
st.set_page_config(
    page_title="Graph Agent Chat UI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = f"session_{int(time.time())}"
if "user_id" not in st.session_state:
    st.session_state.user_id = f"user_{int(time.time())}"
if "current_plan" not in st.session_state:
    st.session_state.current_plan = ""
if "previous_node" not in st.session_state:
    st.session_state.previous_node = None

# Sidebar for configuration
with st.sidebar:
    st.title("⚙️ Configuration")

    # API Configuration
    st.write("**API Configuration:**")
    api_base_url = st.text_input(
        "API Base URL",
        value="http://localhost:8000",
        help="Base URL for the API server"
    )

    st.divider()

    # Reset conversation button
    if st.button("🔄 Reset Conversation", type="secondary"):
        st.session_state.messages = []
        st.session_state.session_id = f"session_{int(time.time())}"
        st.session_state.user_id = f"user_{int(time.time())}"
        st.session_state.current_plan = ""
        st.session_state.previous_node = None
        st.rerun()

    st.divider()

    # Environment status
    st.write("**Environment Status:**")
    openai_key = settings.OPENAI_API_KEY
    if openai_key:
        st.success("✅ OPENAI_API_KEY is set")
        st.write(
            f"Key: {openai_key[:8]}...{openai_key[-4:] if len(openai_key) > 12 else '****'}")
    else:
        st.error("❌ OPENAI_API_KEY not found")

    st.divider()

    # Display current session info
    st.write("**Session Info:**")
    st.write(f"User ID: `{st.session_state.user_id}`")
    st.write(f"Session ID: `{st.session_state.session_id}`")
    st.write(f"Messages: {len(st.session_state.messages)}")

    st.divider()

    # Current state display
    st.write("**Current State:**")
    if st.session_state.current_plan:
        st.write("**Current Plan:**")
        st.code(st.session_state.current_plan, language="text")
    else:
        st.write("**Current Plan:** _No plan set_")

    if st.session_state.previous_node:
        st.write(f"**Previous Node:** {st.session_state.previous_node}")
    else:
        st.write("**Previous Node:** _None_")


def call_api_stream(message: str):
    """Call the API streaming endpoint"""
    url = f"{api_base_url}/api/v1/astream"

    payload = {
        "user_id": st.session_state.user_id,
        "session_id": st.session_state.session_id,
        "message": message,
        "messages": st.session_state.messages,  # Include full conversation history
        "previous_node": st.session_state.previous_node,
        "current_plan": st.session_state.current_plan,
        "params": {}
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=60
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None


# Main chat interface
st.title("🤖 Graph Agent Chat Interface (API Version)")
st.write("Chat with your LangGraph agent via API. The agent can orchestrate, plan, and respond to your queries.")

# Display chat messages
chat_container = st.container()

with chat_container:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").markdown(msg["content"])
        else:
            st.chat_message("assistant").markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to session state
    user_message = {"role": "user", "content": prompt}
    st.session_state.messages.append(user_message)

    # Display user message
    st.chat_message("user").markdown(prompt)

    # Process with API
    response = call_api_stream(prompt)

    if response:
        # Create SSE client
        client = sseclient.SSEClient(response)

        with st.chat_message("assistant"):
            thinking_spinner = ControlledSpinner("Agent is thinking...")
            thinking_container = st.empty()
            response_container = st.empty()

            full_response = ""
            thinking_content = "THINKING...\n\n"
            current_node = ""

            # Process events
            for event in client.events():
                data = json.loads(event.data)
                content = data.get("content", "")
                response_type = data.get("type", "")
                node = data.get("node", "")

                if content:
                    if response_type in ["think", "thinking", "status", "node_change", "plan"]:
                        # Handle thinking content
                        # if response_type == "node_change":
                        #     thinking_content += f"\n**[{node}]**\n"
                        #     current_node = node
                        #     thinking_spinner.start()
                        #     thinking_container.write(thinking_content)
                        if response_type == "plan":
                            st.session_state.current_plan = content.replace(
                                "Plan updated: ", ""
                            )
                            # Don't add plan updates to the chat message thinking content
                            # Just update the session state and sidebar will show it
                        else:
                            thinking_content += content
                            thinking_spinner.start()
                            # thinking_container.write(thinking_content)

                        # Update previous node if available
                        if node:
                            st.session_state.previous_node = node

                    elif response_type in ["message", "msg"]:
                        # Handle final response
                        thinking_spinner.stop()
                        thinking_container.empty()

                        full_response += content
                        response_container.markdown(full_response)

                        # Update state
                        if node:
                            st.session_state.previous_node = node

                    elif response_type == "complete":
                        # Handle completion
                        thinking_spinner.stop()
                        thinking_container.empty()

                        final_response = data.get(
                            "full_response", full_response)
                        if final_response:
                            full_response = final_response
                            response_container.markdown(full_response)
                        break

                    elif response_type == "error":
                        thinking_spinner.stop()
                        thinking_container.empty()
                        response_container.error(f"❌ {content}")
                        break

        # Add AI response to session state
        if full_response:
            ai_message = {"role": "assistant", "content": full_response}
            st.session_state.messages.append(ai_message)
        else:
            st.error("No response received from the agent.")
    else:
        st.error("Failed to connect to API server.")

# Footer with additional information
st.divider()
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Messages", len(st.session_state.messages))

with col2:
    if st.session_state.messages:
        last_message_type = st.session_state.messages[-1].get(
            "role", "Unknown")
        st.metric("Last Message", last_message_type.title())
    else:
        st.metric("Last Message", "None")

with col3:
    st.metric("Session ID", st.session_state.session_id[-4:])

with col4:
    st.metric("Current Node", st.session_state.previous_node or "None")

# Debug section (collapsible)
with st.expander("🔍 Debug Information"):
    st.write("**Current Session State:**")

    # Show current plan prominently
    if st.session_state.current_plan:
        st.write("**Current Plan:**")
        st.code(st.session_state.current_plan, language="text")
    else:
        st.write("**Current Plan:** _No plan set_")

    # Show previous node
    if st.session_state.previous_node:
        st.write(f"**Previous Node:** {st.session_state.previous_node}")
    else:
        st.write("**Previous Node:** _None_")

    st.divider()

    debug_info = {
        "user_id": st.session_state.user_id,
        "session_id": st.session_state.session_id,
        "total_messages": len(st.session_state.messages),
        "current_plan": st.session_state.current_plan,
        "previous_node": st.session_state.previous_node,
        "api_base_url": api_base_url,
        "messages": [
            {
                "role": msg.get("role", "unknown"),
                "content": msg.get("content", "")[:100] + "..." if len(msg.get("content", "")) > 100 else msg.get("content", "")
            }
            for msg in st.session_state.messages
        ]
    }
    st.json(debug_info)

    if st.button("Export Chat History"):
        chat_export = {
            "user_id": st.session_state.user_id,
            "session_id": st.session_state.session_id,
            "current_plan": st.session_state.current_plan,
            "previous_node": st.session_state.previous_node,
            "messages": st.session_state.messages
        }
        st.download_button(
            label="Download Chat History",
            data=json.dumps(chat_export, indent=2),
            file_name=f"chat_history_{st.session_state.session_id}.json",
            mime="application/json"
        )

    # Test API connection
    st.divider()
    st.write("**API Connection Test:**")
    if st.button("Test API Connection"):
        try:
            test_response = requests.get(f"{api_base_url}/docs", timeout=5)
            if test_response.status_code == 200:
                st.success("✅ API server is reachable")
            else:
                st.warning(
                    f"⚠️ API server responded with status {test_response.status_code}")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Cannot reach API server: {str(e)}")
