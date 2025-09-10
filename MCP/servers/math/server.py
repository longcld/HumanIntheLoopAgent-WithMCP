from fastmcp import FastMCP
from config import get_settings

settings = get_settings()

# Create FastMCP instance
mcp = FastMCP(settings.SERVER_NAME, stateless_http=True)


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b


@mcp.tool()
def magic_number() -> int:
    """Return the magic number"""
    return 5


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(
        transport=settings.SERVER_TRANSPORT_PROTOCOL,
        port=settings.SERVER_PORT,
    )
