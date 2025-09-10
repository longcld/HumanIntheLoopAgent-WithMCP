from MCP.clients.manager import mcp_client_manager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
import uvicorn
from loguru import logger
import asyncio
from config import get_settings

settings = get_settings()


async def startup_event():
    try:
        await mcp_client_manager.start()
        logger.info(
            f"MCP Client started with {len(mcp_client_manager.server_configs)} servers and {len(mcp_client_manager.tools)} tools"
        )
    except Exception as e:
        logger.error(f"Failed to start MCP client: {e}")


async def shutdown_event():
    try:
        logger.info("Shutting down MCP Client...")
        await asyncio.wait_for(mcp_client_manager.shutdown(), timeout=10.0)
        logger.info("MCP Client shut down successfully")
    except asyncio.TimeoutError:
        logger.warning("MCP Client shutdown timed out after 10 seconds")
    except Exception as e:
        logger.error(f"Error during MCP client shutdown: {e}")


def create_app():

    application = FastAPI(
        debug=settings.DEBUG,
        title=settings.APP_NAME,
        version=settings.APP_VERSION
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix="/api/v1")

    # Add startup and shutdown event handlers
    application.add_event_handler("startup", startup_event)
    application.add_event_handler("shutdown", shutdown_event)

    logger.info("Create app completed")
    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
