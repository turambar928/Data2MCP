import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from mcp.server.fastmcp import Context, FastMCP

from data2mcp_v2.config import Data2McpConfig
from data2mcp_v2.server.router import Router
from data2mcp_v2.utils.clogger import _set_logger

_set_logger(Path("./logs"), logging_level=logging.INFO, file_name="data2mcp.log")


def serve(config: Data2McpConfig) -> None:
    """Run the data2mcp server."""

    @asynccontextmanager
    async def data2mcp_lifespan(server: FastMCP) -> AsyncIterator[dict]:
        """Lifespan context manager for the data2mcp server."""
        async with Router(config) as router:
            yield {"router": router}

    server = FastMCP("data2mcp", lifespan=data2mcp_lifespan)

    @server.tool(
        name="route",
        description=(""""""),
    )
    async def route(
        query: str,
        ctx: Context,
    ):
        """Route query to appropriate retriever."""
        router: Router = ctx.request_context.lifespan_context["router"]
        final_text, messages = await router.route(query)
        return final_text

    server.run(transport="stdio")
