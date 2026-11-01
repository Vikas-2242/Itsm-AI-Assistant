"""Small MCP stdio client. Each tool call opens a short-lived MCP session."""
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent

async def call_tool(tool_name: str, arguments: dict | None = None):
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "mcp_server.py")], env=None)
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments or {})
            if result.isError:
                raise RuntimeError(f"MCP tool {tool_name} failed: {result.content}")
            values = []
            for block in result.content:
                if getattr(block, "text", None):
                    values.append(block.text)
            if not values:
                return None
            import json
            parsed = []
            for value in values:
                try: parsed.append(json.loads(value))
                except json.JSONDecodeError: parsed.append(value)
            return parsed[0] if len(parsed) == 1 else parsed
