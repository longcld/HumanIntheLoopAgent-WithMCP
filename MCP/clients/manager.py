from config import get_settings
import json
import asyncio
from typing import Optional, Dict, List, Any
from contextlib import AsyncExitStack
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from loguru import logger


class MCPClientManager:

    def __init__(self, server_configs: Dict[str, Any]):

        self.exit_stack: Optional[AsyncExitStack] = None
        self.server_configs: Dict[str, Dict] = server_configs
        self.client: Optional[MultiServerMCPClient] = None
        self.sessions: Dict[str, Any] = {}
        self.tools: List[Any] = []

        self.is_initialized = False
        self.init_lock = asyncio.Lock()

    async def start(self, server_names: Optional[List[str]] = None) -> None:
        if self.is_initialized:
            return

        async with self.init_lock:
            if self.is_initialized:
                return

            try:
                self.client = MultiServerMCPClient(self.server_configs)
                logger.info("MCP Client created successfully.")
            except Exception as e:
                logger.error(f"Failed to create MCP client: {e}")
                raise
            self.exit_stack = AsyncExitStack()
            await self.exit_stack.__aenter__()

            names = server_names or list(self.server_configs.keys())
            self.sessions.clear()
            self.tools.clear()

            for name in names:
                # keep session open until shutdown
                sess = await self.exit_stack.enter_async_context(self.client.session(name))
                self.sessions[name] = sess
                try:
                    self.tools.extend(await load_mcp_tools(sess))
                except Exception as e:
                    logger.exception(
                        f"Failed to load tools from MCP server '{name}': {e}"
                    )

            self.is_initialized = True

    async def shutdown(self) -> None:
        if not self.is_initialized:
            return

        logger.info("Starting MCP client shutdown...")

        try:
            # Close all sessions first
            for name, session in self.sessions.items():
                try:
                    logger.debug(f"Closing session for {name}")
                    if hasattr(session, 'close'):
                        await session.close()
                except Exception as e:
                    logger.warning(f"Error closing session {name}: {e}")

            # Close the exit stack
            if self.exit_stack is not None:
                logger.debug("Closing exit stack")
                await self.exit_stack.aclose()

        except Exception as e:
            logger.warning(f"Error during exit stack cleanup: {e}")
        finally:
            self.client = None
            self.exit_stack = None
            self.sessions.clear()
            self.tools.clear()
            self.is_initialized = False
            logger.info("MCP client shutdown completed")


# Load MCP configuration
settings = get_settings()

mcp_server_configs_path = settings.MCP_SERVER_CONFIGS_PATH
with open(mcp_server_configs_path, 'r') as f:
    mcp_server_configs = json.load(f)

# Create global MCP client manager
mcp_client_manager = MCPClientManager(mcp_server_configs)
