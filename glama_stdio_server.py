"""
Entrypoint for Glama container checks: runs the same MCP server over stdio,
so the platform's mcp-proxy wrapper can talk to it directly.
"""
from mcp_oracle_server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
