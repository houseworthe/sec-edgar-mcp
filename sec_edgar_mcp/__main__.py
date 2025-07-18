"""Main entry point for the SEC EDGAR MCP server."""

from .server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")