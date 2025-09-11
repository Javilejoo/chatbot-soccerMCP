from openai import OpenAI
from dotenv import load_dotenv
import os
import asyncio
import json
import time
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from mcp_client import open_session, open_op_session, open_fs_session, open_git_session, list_tools, invoke_tool

# Configuración
load_dotenv()
client = OpenAI()
console = Console()

# Sistema de logging
def log_mcp_call(tool_name, parameters, result, execution_time_ms=None):
    """Registra llamadas al MCP en un archivo de log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Crear directorio logs si no existe
    os.makedirs("logs", exist_ok=True)
    
    log_entry = {
        "timestamp": timestamp,
        "tool": tool_name,
        "parameters": parameters,
        "result": result,
        "execution_time_ms": execution_time_ms
    }
    
    try:
        with open("logs/mcp_calls.txt", "a", encoding="utf-8") as f:
            f.write(f"{json.dumps(log_entry, ensure_ascii=False)}\n")
    except Exception as e:
        console.print(f"[dim red]Error guardando log: {e}[/dim red]")

async def get_all_mcp_tools_as_openai_tools():
    """Obtiene las herramientas de todos los servidores MCP y las formatea para OpenAI"""
    openai_tools = []
    server_availability = {
        "soccer": False,
        "filesystem": False, 
        "git": False,
        "op": False
    }
    
    # Listas separadas para cada servidor para mostrar correctamente
    tools_by_server = {
        "soccer": [],
        "filesystem": [],
        "git": [],
        "op": []
    }
    
    def add_tools_from_server(tools, server_name, server_key, prefix=""):
        """Helper function para agregar herramientas de un servidor con conversión automática"""
        for tool in tools:
            tool_name = tool.get("name")
            tool_description = tool.get("description", f"Herramienta de {server_name}: {tool_name}")
            tool_input_schema = tool.get("inputSchema", {
                "type": "object",
                "properties": {},
                "required": []
            })
            
            # Aplicar prefijo si se especifica
            final_name = f"{prefix}{tool_name}" if prefix else tool_name
            
            tool_dict = {
                "type": "function",
                "function": {
                    "name": final_name,
                    "description": tool_description,
                    "parameters": tool_input_schema
                }
            }
            
            openai_tools.append(tool_dict)
            tools_by_server[server_key].append(tool_dict)
    
    # ==================== SOCCER MCP SERVER ====================
    try:
        console.print("[yellow]🔄 Conectando al servidor Soccer MCP...[/yellow]")
        async with open_session() as session:
            soccer_tools = await list_tools(session)
            console.print(f"[green]✓ Soccer MCP conectado: {len(soccer_tools)} herramientas[/green]")
            server_availability["soccer"] = True
            
            log_mcp_call("SOCCER_CONNECTION", {"action": "list_tools"}, {"tools_count": len(soccer_tools), "tools": [t.get("name") for t in soccer_tools]})
            
            # ✨ CONVERSIÓN AUTOMÁTICA
            add_tools_from_server(soccer_tools, "fútbol", "soccer")
            
    except Exception as e:
        console.print(f"[bold red]⚠️ Error conectando al servidor Soccer MCP: {str(e)}[/bold red]")
        log_mcp_call("SOCCER_CONNECTION_ERROR", {}, {"error": str(e)})

    # ==================== ONE PIECE MCP SERVER ====================
    try:
        console.print("[yellow]🔄 Conectando al servidor One Piece MCP...[/yellow]")
        async with open_op_session() as op_session:
            op_tools = await list_tools(op_session)
            console.print(f"[green]✓ One Piece MCP conectado: {len(op_tools)} herramientas[/green]")
            server_availability["op"] = True
            
            log_mcp_call("ONEPIECE_CONNECTION", {"action": "list_tools"}, {"tools_count": len(op_tools), "tools": [t.get("name") for t in op_tools]})

            # ✨ CONVERSIÓN AUTOMÁTICA
            add_tools_from_server(op_tools, "One Piece", "op")
            
    except Exception as e:
        console.print(f"[bold red]⚠️ Error conectando al servidor One Piece MCP: {str(e)}[/bold red]")
        log_mcp_call("ONEPIECE_CONNECTION_ERROR", {}, {"error": str(e)})
    
    # ==================== FILESYSTEM MCP SERVER ====================
    try:
        console.print("[yellow]🔄 Conectando al servidor Filesystem MCP...[/yellow]")
        async with open_fs_session() as fs_session:
            fs_tools = await list_tools(fs_session)
            console.print(f"[green]✓ Filesystem MCP conectado: {len(fs_tools)} herramientas[/green]")
            server_availability["filesystem"] = True
            
            log_mcp_call("FILESYSTEM_CONNECTION", {"action": "list_tools"}, {"tools_count": len(fs_tools), "tools": [t.get("name") for t in fs_tools]})
            
            # ✨ CONVERSIÓN AUTOMÁTICA con prefijo fs_ para evitar conflictos
            add_tools_from_server(fs_tools, "sistema de archivos", "filesystem", "fs_")
            
    except Exception as e:
        console.print(f"[bold red]⚠️ Error conectando al servidor Filesystem MCP: {str(e)}[/bold red]")
        log_mcp_call("FILESYSTEM_CONNECTION_ERROR", {}, {"error": str(e)})

    # ==================== GIT MCP SERVER ====================
    try:
        async with open_git_session() as git_session:
            git_tools = await list_tools(git_session)
            console.print(f"[green]✓ Git MCP conectado: {len(git_tools)} herramientas[/green]")
            server_availability["git"] = True
            
            log_mcp_call("GIT_CONNECTION", {"action": "list_tools"}, {"tools_count": len(git_tools), "tools": [t.get("name") for t in git_tools]})
            
            # ✨ CONVERSIÓN AUTOMÁTICA
            add_tools_from_server(git_tools, "Git", "git")
            
    except Exception as e:
        console.print(f"[bold red]⚠️ Error conectando al servidor Git MCP: {str(e)}[/bold red]")
        log_mcp_call("GIT_CONNECTION_ERROR", {}, {"error": str(e)})

    # ==================== RESUMEN ====================
    status_parts = []
    if server_availability["soccer"]:
        status_parts.append("⚽ Fútbol")
    if server_availability["filesystem"]:
        status_parts.append("📁 Archivos")
    if server_availability["git"]:
        status_parts.append("🧑‍💻 Git")
    if server_availability["op"]:
        status_parts.append("🏴‍☠️ One Piece")
    
    if status_parts:
        console.print(f"[green]🎯 Servidores MCP activos: {' + '.join(status_parts)}[/green]")
    else:
        console.print(f"[bold red]❌ No se pudo conectar a ningún servidor MCP[/bold red]")
    
    console.print(f"[green]🛠️ Total herramientas disponibles: {len(openai_tools)}[/green]")
    
    # Retornar tanto las herramientas como la disponibilidad individual para compatibilidad
    return openai_tools, server_availability["soccer"], server_availability["filesystem"], server_availability["git"], server_availability["op"], tools_by_server

async def execute_mcp_tool(soccer_session, fs_session, git_session, op_session, tool_name, params=None):
    """Ejecuta una herramienta específica en el servidor MCP correspondiente"""
    start_time = datetime.now()
    try:
        console.print(f"[yellow]→ Ejecutando herramienta: {tool_name}[/yellow]")
        if params:
            console.print(f"[dim yellow]  Parámetros: {params}[/dim yellow]")

        import time
        t0 = time.perf_counter()
        
        # Determinar qué servidor usar basado en el prefijo de la herramienta
        if tool_name.startswith("fs_"):
            # Herramienta de filesystem - usar fs_session
            if fs_session is None:
                raise RuntimeError("Filesystem MCP no está disponible")
            actual_tool_name = tool_name[3:]  # Remover prefijo 'fs_'
            result = await invoke_tool(fs_session, actual_tool_name, params or {})
            console.print(f"[green]✓ Herramienta filesystem ejecutada exitosamente[/green]")
        elif tool_name.startswith("git_") or tool_name in ["git_status", "git_diff_unstaged", "git_diff_staged", "git_diff", "git_commit", "git_add", "git_reset", "git_log", "git_create_branch", "git_checkout", "git_show", "git_init", "git_branch"]:
            # Herramienta de git - usar git_session
            if git_session is None:
                raise RuntimeError("Git MCP no está disponible")
            # No remover prefijo para estas herramientas ya que todas empiezan con git_
            result = await invoke_tool(git_session, tool_name, params or {})
            console.print(f"[green]✓ Herramienta git ejecutada exitosamente[/green]")
        elif tool_name.startswith("op_"):
            # Herramienta de One Piece - usar op_session
            if op_session is None:
                raise RuntimeError("One Piece MCP no está disponible")
            # No remover prefijo para las herramientas de One Piece
            result = await invoke_tool(op_session, tool_name, params or {})
            console.print(f"[green]✓ Herramienta One Piece ejecutada exitosamente[/green]")
        else:
            # Herramienta de soccer - usar soccer_session
            if soccer_session is None:
                raise RuntimeError("Soccer MCP no está disponible")
            result = await invoke_tool(soccer_session, tool_name, params or {})
            console.print(f"[green]✓ Herramienta soccer ejecutada exitosamente[/green]")
        
        execution_time_ms = int((time.perf_counter() - t0) * 1000)
        log_mcp_call(tool_name, params or {}, result, execution_time_ms)
        return result
        
    except Exception as e:
        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        error_result = {"error": str(e)}
        console.print(f"[red]Error ejecutando herramienta {tool_name}: {str(e)}[/red]")
        log_mcp_call(tool_name, params or {}, error_result, execution_time_ms)
        return error_result

async def chat_with_mcp():
    """Función principal para interactuar con el usuario y los servidores MCP"""
    console.print(Panel.fit("⚽📁 [bold blue]Chatbot MCP - Fútbol, Archivos, Git & One Piece[/bold blue]", 
                         subtitle="Pregunta sobre fútbol o realiza operaciones con archivos • Escribe 'salir' para terminar"))
    
    # Obtener herramientas disponibles primero
    mcp_tools, soccer_available, filesystem_available, git_available, op_available, tools_by_server = await get_all_mcp_tools_as_openai_tools()
    if not mcp_tools:
        console.print("[bold red]No se pudieron cargar herramientas MCP. Verificar conexión a servidores.[/bold red]")
        return
    
    # Mostrar herramientas disponibles
    console.print(f"[green]🛠️ Total herramientas disponibles: {len(mcp_tools)}[/green]")
    
    if soccer_available:
        soccer_tools = tools_by_server["soccer"]
        console.print(f"[yellow]⚽ Herramientas de Fútbol ({len(soccer_tools)}):[/yellow]")
        for tool in soccer_tools:
            console.print(f"   • {tool['function']['name']}")
    
    if filesystem_available:
        fs_tools = tools_by_server["filesystem"]
        console.print(f"[blue]📁 Herramientas de Archivos ({len(fs_tools)}):[/blue]")
        for tool in fs_tools:
            console.print(f"   • {tool['function']['name'][3:]}")  # Sin prefijo fs_
    
    if git_available:
        git_tools = tools_by_server["git"]
        console.print(f"[magenta]🧑‍💻 Herramientas de Git ({len(git_tools)}):[/magenta]")
        for tool in git_tools:
            console.print(f"   • {tool['function']['name']}")

    if op_available:
        op_tools = tools_by_server["op"]
        console.print(f"[cyan]🏴‍☠️ Herramientas de One Piece ({len(op_tools)}):[/cyan]")
        for tool in op_tools:
            console.print(f"   • {tool['function']['name']}")
    # Generar capabilities dinámicamente desde las herramientas disponibles
    def generate_capabilities_from_tools(tools_dict):
        capabilities = []
        
        server_names = {
            'soccer': 'INFORMACIÓN DE FÚTBOL',
            'op': 'INFORMACIÓN DE ONE PIECE', 
            'filesystem': 'OPERACIONES CON ARCHIVOS',
            'git': 'OPERACIONES CON GIT'
        }
        
        server_examples = {
            'soccer': 'Ejemplos de IDs de competiciones: "PL" (Premier League), "CL" (Champions League), "DFB" (Bundesliga), "SA" (Serie A), "PD" (La Liga)',
            'filesystem': 'Las rutas pueden ser absolutas o relativas al directorio de trabajo actual',
            'git': 'Recuerda estar en un directorio con repositorio Git inicializado',
            'op': 'Puedes buscar por nombre exacto o usar filtros para búsquedas avanzadas'
        }
        
        for server_key, tools in tools_dict.items():
            if tools:  # Si hay herramientas disponibles para este servidor
                server_name = server_names.get(server_key, f'HERRAMIENTAS DE {server_key.upper()}')
                tool_descriptions = []
                
                for tool in tools:
                    # Generar descripción automática basada en el nombre y descripción de la herramienta
                    tool_name = tool['function']['name']
                    tool_desc = tool['function']['description']
                    
                    # Para filesystem, mostrar sin el prefijo fs_ para mejor legibilidad
                    if server_key == 'filesystem' and tool_name.startswith('fs_'):
                        display_name = tool_name[3:]  # Remover prefijo fs_
                    else:
                        display_name = tool_name
                    
                    tool_descriptions.append(f"- {display_name}: {tool_desc}")
                
                capability_text = f"{server_name}:\n" + "\n".join(tool_descriptions)
                
                # Agregar ejemplos/notas específicas si existen
                if server_key in server_examples:
                    capability_text += f"\n\n{server_examples[server_key]}"
                
                capabilities.append(capability_text)
        
        return capabilities
    
    capabilities = generate_capabilities_from_tools(tools_by_server)
    # Usar context managers para las sesiones MCP
    if soccer_available and filesystem_available and git_available and op_available:
        # Ambos servidores disponibles
        async with open_session() as soccer_session, open_fs_session() as fs_session, open_git_session() as git_session, open_op_session() as op_session:
            console.print("[green]✓ Conexiones a Soccer MCP, Filesystem MCP, Git MCP y One Piece MCP establecidas[/green]")
            await run_chat_loop(soccer_session, fs_session, git_session, op_session, capabilities, mcp_tools)
    elif soccer_available:
        # Solo Soccer MCP disponible
        async with open_session() as soccer_session:
            console.print("[green]✓ Conexión a Soccer MCP establecida[/green]")
            await run_chat_loop(soccer_session, None, None, None, capabilities, mcp_tools)
    elif filesystem_available:
        # Solo Filesystem MCP disponible
        async with open_fs_session() as fs_session:
            console.print("[green]✓ Conexión a Filesystem MCP establecida[/green]")
            await run_chat_loop(None, fs_session, None, None, capabilities, mcp_tools)
    elif git_available:
        # Solo Git MCP disponible
        async with open_git_session() as git_session:
            console.print("[green]✓ Conexión a Git MCP establecida[/green]")
            await run_chat_loop(None, None, git_session, None, capabilities, mcp_tools)
    elif op_available:
        # Solo One Piece MCP disponible
        async with open_op_session() as op_session:
            console.print("[green]✓ Conexión a One Piece MCP establecida[/green]")
            await run_chat_loop(None, None, None, op_session, capabilities, mcp_tools)
    else:
        console.print("[bold red]No hay servidores MCP disponibles[/bold red]")
        return

async def run_chat_loop(soccer_session, fs_session, git_session, op_session, capabilities, mcp_tools):
    """Ejecuta el bucle principal del chat con las sesiones proporcionadas"""
    system_message = {
        "role": "system", 
        "content": f"""Eres un asistente inteligente con acceso a múltiples herramientas MCP. Puedes ayudar con:

{chr(10).join(capabilities)}

Siempre usa las herramientas apropiadas para responder con información precisa y actualizada. 
Para operaciones con archivos, las rutas pueden ser absolutas o relativas al directorio de trabajo actual.
Responde de manera clara y útil, organizando la información de forma legible."""
    }

    # Lista de mensajes de la conversación
    messages = [system_message]

    while True:
        # Solicitar entrada del usuario
        try:
            user_input = console.input("\n[bold cyan]Tu pregunta:[/bold cyan] ")
        except KeyboardInterrupt:
            console.print("\n[yellow]Saliendo...[/yellow]")
            break
        except EOFError:
            console.print("\n[yellow]Saliendo...[/yellow]")
            break

        if user_input.lower() in ['salir', 'exit', 'quit']:
            console.print("[yellow]¡Hasta luego![/yellow]")
            break

        # Agregar mensaje del usuario
        messages.append({"role": "user", "content": user_input})

        try:
            # Llamar a OpenAI
            console.print("[dim yellow]🤖 Procesando...[/dim yellow]")
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=mcp_tools,
                tool_choice="auto"
            )

            assistant_message = response.choices[0].message
            messages.append(assistant_message)

            # Procesar llamadas a herramientas
            if assistant_message.tool_calls:
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    # Ejecutar la herramienta MCP correspondiente
                    tool_result = await execute_mcp_tool(soccer_session, fs_session, git_session, op_session, function_name, function_args)

                    # Agregar resultado de la herramienta a los mensajes
                    tool_message = {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(tool_result, ensure_ascii=False, indent=2)
                    }
                    messages.append(tool_message)

                # Obtener respuesta final de OpenAI después de usar las herramientas
                final_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages
                )
                
                final_message = final_response.choices[0].message
                messages.append(final_message)
                
                console.print(f"\n[bold green]Asistente:[/bold green] {final_message.content}")
            else:
                # Respuesta directa sin herramientas
                console.print(f"\n[bold green]Asistente:[/bold green] {assistant_message.content}")

        except Exception as e:
            console.print(f"[bold red]Error procesando respuesta: {str(e)}[/bold red]")
            # No rompemos el bucle, permitimos que el usuario continúe
