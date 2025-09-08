import os, json, shlex, time
from contextlib import asynccontextmanager
from typing import Tuple, List, Dict, Any

from dotenv import load_dotenv
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

load_dotenv()

def _from_env() -> StdioServerParameters | None:
    cmd = os.getenv("SOCCER_MCP_COMMAND")
    if not cmd:
        return None
    args = shlex.split(os.getenv("SOCCER_MCP_ARGS", ""))
    cwd = os.getenv("SOCCER_MCP_CWD") or None
    return StdioServerParameters(command=cmd, args=args, cwd=cwd)

def _from_claude_config(preferred_key: str = "soccer-mcp") -> StdioServerParameters | None:
    appdata = os.getenv("APPDATA")
    if not appdata:
        return None
    cfg_path = os.path.join(appdata, "Claude", "claude_desktop_config.json")
    if not os.path.exists(cfg_path):
        return None
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    servers = cfg.get("mcpServers", {})
    if not servers:
        return None
    key = preferred_key if preferred_key in servers else next(iter(servers))
    s = servers[key]
    return StdioServerParameters(
        command=s["command"],
        args=s.get("args", []),
        cwd=s.get("cwd")
    )

def server_params() -> StdioServerParameters:
    return _from_env() or _from_claude_config() or (
        (_ for _ in ()).throw(RuntimeError(
            "No MCP launch config found. Set SOCCER_MCP_COMMAND / SOCCER_MCP_ARGS / SOCCER_MCP_CWD in .env "
            "or add a server in Claude Desktop."
        ))
    )

def dump(obj: Any):
    """Convierte modelos Pydantic del SDK a dict JSON-friendly."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, list):
        return [dump(x) for x in obj]
    if isinstance(obj, dict):
        return {k: dump(v) for k, v in obj.items()}
    return obj

@asynccontextmanager
async def open_session():
    params = server_params()
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session

async def list_tools(session: ClientSession) -> List[Dict]:
    listing = await session.list_tools()
    listing_dict = dump(listing)          # ← convierte ListToolsResult a dict
    return listing_dict.get("tools", [])

async def call_tool(session: ClientSession, name: str, args: dict) -> Tuple[dict, int]:
    t0 = time.perf_counter()
    result = await session.call_tool(name, args)
    ms = int((time.perf_counter() - t0) * 1000)
    return dump(result), ms               # ← convierte CallToolResult a dict
