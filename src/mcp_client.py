import os, json, shlex, time
from contextlib import asynccontextmanager
from typing import Tuple, List, Dict, Any
import httpx

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

def _from_env_op() -> StdioServerParameters | None:
    cmd = os.getenv("OP_MCP_COMMAND")
    if not cmd:
        return None
    args = shlex.split(os.getenv("OP_MCP_ARGS", ""))
    cwd = os.getenv("OP_MCP_CWD") or None
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

def server_params_op() -> StdioServerParameters:
    return _from_env_op() or (
        (_ for _ in ()).throw(RuntimeError(
            "No OP MCP launch config found. Set OP_MCP_COMMAND / OP_MCP_ARGS / OP_MCP_CWD in .env "
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
async def open_op_session():
    """
    Abre una sesión con el servidor One Piece MCP usando HTTP.
    Lee la URL del servidor desde la variable de entorno OP_MCP_URL.
    """
    op_url = os.getenv("OP_MCP_URL")
    if not op_url:
        raise RuntimeError("OP_MCP_URL no está configurado en .env. Debe ser algo como: http://localhost:8080/mcp")
    
    # Crear un cliente HTTP que simule la interfaz MCP
    yield HTTPMCPClient(op_url)

class HTTPMCPClient:
    """Cliente HTTP para conectar con servidores MCP usando streamable-http transport"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session_id = None
        self.initialized = False
        
    def parse_sse_response(self, sse_text: str):
        """Parse Server-Sent Events response"""
        try:
            lines = sse_text.strip().split('\n')
            for line in lines:
                if line.startswith('data: '):
                    json_str = line[6:]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
            return json.loads(sse_text)
        except Exception:
            return None
    
    async def ensure_session(self):
        """Asegura que tenemos una sesión válida e inicializada"""
        if self.initialized:
            return True
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Paso 1: Obtener session ID
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                }
                
                response = await client.post(
                    self.base_url,
                    json={},
                    headers=headers
                )
                
                # Extraer session ID de headers
                self.session_id = response.headers.get('mcp-session-id')
                
                if not self.session_id:
                    print(f"No se encontró session ID en headers. Headers: {list(response.headers.keys())}")
                    return False
                
                # Paso 2: Inicializar con session ID
                session_headers = headers.copy()
                session_headers['mcp-session-id'] = self.session_id
                
                initialize_request = {
                    "jsonrpc": "2.0",
                    "id": "init-1",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "clientInfo": {
                            "name": "chatbot-client",
                            "version": "1.0.0"
                        }
                    }
                }
                
                response = await client.post(
                    self.base_url,
                    json=initialize_request,
                    headers=session_headers
                )
                
                if response.status_code != 200:
                    print(f"Error en inicialización: {response.status_code} - {response.text}")
                    return False
                
                result = self.parse_sse_response(response.text)
                if not result or "error" in result:
                    print(f"Error en resultado de inicialización: {result}")
                    return False
                
                # Paso 3: Enviar notificación initialized
                initialized_request = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                
                await client.post(
                    self.base_url,
                    json=initialized_request,
                    headers=session_headers
                )
                
                self.initialized = True
                print(f"✅ Sesión MCP establecida correctamente con session ID: {self.session_id}")
                return True
                
            except Exception as e:
                print(f"Error estableciendo sesión MCP: {e}")
                return False
        
    async def list_tools(self) -> List[Dict]:
        """Lista las herramientas disponibles en el servidor MCP"""
        if not await self.ensure_session():
            return []
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "mcp-session-id": self.session_id
                }
                
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": "tools-1",
                    "method": "tools/list",
                    "params": {}
                }
                
                response = await client.post(
                    self.base_url,
                    json=tools_request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = self.parse_sse_response(response.text)
                    
                    if result and "error" not in result:
                        # Extraer tools del resultado MCP
                        tools = []
                        if isinstance(result, dict):
                            if "result" in result and "tools" in result["result"]:
                                tools = result["result"]["tools"]
                            elif "tools" in result:
                                tools = result["tools"]
                        
                        print(f"✅ Se encontraron {len(tools)} herramientas en el servidor MCP de One Piece")
                        return tools if isinstance(tools, list) else []
                    else:
                        print(f"Error en respuesta de tools/list: {result}")
                else:
                    print(f"Error HTTP en tools/list: {response.status_code} - {response.text}")
                
                return []
                
            except Exception as e:
                print(f"Error listando herramientas HTTP: {e}")
                return []

    async def call_tool(self, name: str, arguments: dict = None) -> Dict:
        """Ejecuta una herramienta en el servidor MCP"""
        if not await self.ensure_session():
            return {
                "content": [{"type": "text", "text": "Error: No se pudo establecer sesión MCP"}],
                "isError": True
            }
            
        if arguments is None:
            arguments = {}
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "mcp-session-id": self.session_id
                }
                
                tool_call_request = {
                    "jsonrpc": "2.0",
                    "id": f"call-{name}",
                    "method": "tools/call",
                    "params": {
                        "name": name,
                        "arguments": arguments
                    }
                }
                
                response = await client.post(
                    self.base_url,
                    json=tool_call_request,
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = self.parse_sse_response(response.text)
                    
                    if result and "error" not in result:
                        # Extraer contenido del resultado MCP
                        if isinstance(result, dict) and 'result' in result:
                            mcp_result = result['result']
                            return {
                                "content": mcp_result.get("content", []),
                                "isError": mcp_result.get("isError", False)
                            }
                    else:
                        print(f"Error en respuesta de tools/call: {result}")
                else:
                    print(f"Error HTTP en tools/call: {response.status_code} - {response.text}")
                
                return {
                    "content": [{"type": "text", "text": f"Error ejecutando herramienta: {response.text[:200]}"}],
                    "isError": True
                }
                
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"Error ejecutando herramienta HTTP: {str(e)}"}],
                    "isError": True
                }

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

async def list_tools(session) -> List[Dict]:
    """Lista herramientas, compatible con sesiones STDIO y HTTP"""
    if isinstance(session, HTTPMCPClient):
        return await session.list_tools()
    else:
        # Sesión STDIO tradicional
        listing = await session.list_tools()
        listing_dict = dump(listing)          # ← convierte ListToolsResult a dict
        return listing_dict.get("tools", [])

async def call_tool(session, name: str, args: dict) -> Tuple[dict, int]:
    """Ejecuta herramientas, compatible con sesiones STDIO y HTTP"""
    t0 = time.perf_counter()
    
    if isinstance(session, HTTPMCPClient):
        result = await session.call_tool(name, args)
        ms = int((time.perf_counter() - t0) * 1000)
        return result, ms
    else:
        # Sesión STDIO tradicional
        result = await session.call_tool(name, args)
        ms = int((time.perf_counter() - t0) * 1000)
        return dump(result), ms               # ← convierte CallToolResult a dict

async def invoke_tool(session, name: str, args: dict = None) -> Dict[str, Any]:
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
