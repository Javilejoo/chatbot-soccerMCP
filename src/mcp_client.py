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

@asynccontextmanager
async def open_fs_session():
    cmd  = os.getenv("FS_MCP_COMMAND")
    args = (os.getenv("FS_MCP_ARGS") or "").split("|") if os.getenv("FS_MCP_ARGS") else []
    cwd  = os.getenv("FS_MCP_CWD") or None
    if not cmd:
        raise RuntimeError("FS_MCP_COMMAND no está configurado en .env")

    params = StdioServerParameters(command=cmd, args=args, cwd=cwd)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            yield session

@asynccontextmanager
async def open_git_session():
    cmd  = os.getenv("GIT_MCP_COMMAND")
    args = (os.getenv("GIT_MCP_ARGS") or "").split("|") if os.getenv("GIT_MCP_ARGS") else []
    cwd  = os.getenv("GIT_MCP_CWD") or None
    if not cmd:
        raise RuntimeError("GIT_MCP_COMMAND no está configurado en .env")

    params = StdioServerParameters(command=cmd, args=args, cwd=cwd)
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

async def invoke_tool(session: ClientSession, name: str, args: dict = None) -> Dict[str, Any]:
    """
    Invoca una herramienta del servidor MCP y retorna solo el contenido del resultado.
    
    Args:
        session: Sesión activa del cliente MCP
        name: Nombre de la herramienta a invocar
        args: Argumentos para la herramienta (opcional)
        
    Returns:
        Dict con el contenido del resultado de la herramienta
    """
    if args is None:
        args = {}
    
    try:
        # Usar la función call_tool existente
        result, execution_time = await call_tool(session, name, args)
        
        # Extraer el contenido del resultado
        content = result.get("content", [])
        
        # Si el contenido es una lista, intentar extraer el texto o datos
        if isinstance(content, list):
            # Buscar contenido de tipo texto o datos
            extracted_data = []
            for item in content:
                if isinstance(item, dict):
                    if "text" in item:
                        extracted_data.append(item["text"])
                    elif "data" in item:
                        extracted_data.append(item["data"])
                    else:
                        extracted_data.append(item)
                else:
                    extracted_data.append(item)
            
            # Si solo hay un elemento, devolverlo directamente
            if len(extracted_data) == 1:
                try:
                    # Intentar parsear como JSON si es string
                    if isinstance(extracted_data[0], str):
                        return json.loads(extracted_data[0])
                    return extracted_data[0]
                except (json.JSONDecodeError, TypeError):
                    return extracted_data[0]
            
            return extracted_data
        
        # Si el contenido no es una lista, devolverlo directamente
        return content
        
    except Exception as e:
        # Retornar un diccionario con el error
        return {
            "error": f"Error al invocar herramienta '{name}': {str(e)}",
            "tool_name": name,
            "args": args
        }
