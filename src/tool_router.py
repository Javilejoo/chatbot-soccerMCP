from openai import OpenAI
from dotenv import load_dotenv
import os
import asyncio
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from mcp_client import open_session, list_tools, invoke_tool

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

async def get_mcp_tools_as_openai_tools():
    """Obtiene las herramientas del servidor MCP y las formatea para OpenAI"""
    try:
        async with open_session() as session:
            # Obtener lista de herramientas con detalles
            tools = await list_tools(session)
            console.print(f"[green]✓ Conectado al servidor MCP. {len(tools)} herramientas disponibles.[/green]")
            
            # Log de la conexión inicial
            log_mcp_call("CONNECTION", {"action": "list_tools"}, {"tools_count": len(tools), "tools": [t.get("name") for t in tools]})
            
            # Convertir a formato OpenAI Tools con definiciones específicas
            openai_tools = []
            
            for tool in tools:
                tool_name = tool.get("name")
                
                if tool_name == "get_competitions":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "get_competitions",
                            "description": "Obtiene todas las competiciones de fútbol disponibles con sus IDs y nombres",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    })
                elif tool_name == "get_teams_competitions":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "get_teams_competitions",
                            "description": "Obtiene los equipos de una competición específica de fútbol",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "competition_id": {
                                        "type": "string",
                                        "description": "ID de la competición (ej: 'PL' para Premier League, 'CL' para Champions League)"
                                    }
                                },
                                "required": ["competition_id"]
                            }
                        }
                    })
                elif tool_name == "get_teams_by_competition":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "get_teams_by_competition",
                            "description": "Obtiene todos los equipos de una competición específica",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "competition_id": {
                                        "type": "string",
                                        "description": "ID de la competición (ej: 'PL' para Premier League, 'CL' para Champions League)"
                                    }
                                },
                                "required": ["competition_id"]
                            }
                        }
                    })
                elif tool_name == "get_matches_by_competition":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "get_matches_by_competition",
                            "description": "Obtiene todos los partidos de una competición específica",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "competition_id": {
                                        "type": "string",
                                        "description": "ID de la competición (ej: 'PL' para Premier League, 'CL' para Champions League)"
                                    }
                                },
                                "required": ["competition_id"]
                            }
                        }
                    })
                elif tool_name == "get_team_by_id":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "get_team_by_id",
                            "description": "Obtiene información detallada de un equipo específico",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "team_id": {
                                        "type": "string",
                                        "description": "ID del equipo"
                                    }
                                },
                                "required": ["team_id"]
                            }
                        }
                    })
                elif tool_name == "get_top_scorers_by_competitions":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "get_top_scorers_by_competitions",
                            "description": "Obtiene los máximos goleadores de una competición específica",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "competition_id": {
                                        "type": "string",
                                        "description": "ID de la competición (ej: 'PL' para Premier League, 'CL' para Champions League)"
                                    }
                                },
                                "required": ["competition_id"]
                            }
                        }
                    })
                elif tool_name == "get_player_by_id":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "get_player_by_id",
                            "description": "Obtiene información detallada de un jugador específico",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "player_id": {
                                        "type": "string",
                                        "description": "ID del jugador"
                                    }
                                },
                                "required": ["player_id"]
                            }
                        }
                    })
                elif tool_name == "get_info_matches_of_a_player":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "get_info_matches_of_a_player",
                            "description": "Obtiene todos los partidos en los que ha participado un jugador específico",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "player_id": {
                                        "type": "string",
                                        "description": "ID del jugador"
                                    }
                                },
                                "required": ["player_id"]
                            }
                        }
                    })
            
            return openai_tools
    except Exception as e:
        console.print(f"[bold red]Error conectando al servidor MCP: {str(e)}[/bold red]")
        # Log de error
        log_mcp_call("CONNECTION_ERROR", {}, {"error": str(e)})
        return []

async def execute_mcp_tool(session, tool_name, params=None):
    """Ejecuta una herramienta específica en el servidor MCP usando una sesión existente"""
    start_time = datetime.now()
    try:
        console.print(f"[yellow]→ Ejecutando herramienta MCP: {tool_name}[/yellow]")
        if params:
            console.print(f"[dim yellow]  Parámetros: {params}[/dim yellow]")

        import time
        t0 = time.perf_counter()
        result = await invoke_tool(session, tool_name, params or {})
        execution_time_ms = int((time.perf_counter() - t0) * 1000)
        console.print(f"[green]✓ Herramienta ejecutada exitosamente[/green]")

        log_mcp_call(tool_name, params or {}, result, execution_time_ms)

        return result
    except Exception as e:
        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        error_result = {"error": str(e)}
        console.print(f"[red]Error ejecutando herramienta {tool_name}: {str(e)}[/red]")
        # Log del error
        log_mcp_call(tool_name, params or {}, error_result, execution_time_ms)
        return error_result

async def chat_with_mcp():
    """Función principal para interactuar con el usuario y el servidor MCP"""
    console.print(Panel.fit("⚽ [bold blue]Chatbot de Fútbol con MCP[/bold blue]", 
                         subtitle="Pregunta sobre competiciones y equipos • Escribe 'salir' para terminar"))
    
    # Abrir UNA SOLA sesión MCP para toda la conversación
    async with open_session() as mcp_session:
        # Obtener las herramientas disponibles del servidor MCP
        mcp_tools = await get_mcp_tools_as_openai_tools()
        if not mcp_tools:
            console.print("[bold red]No se pudieron cargar herramientas MCP. Verificar conexión al servidor.[/bold red]")
            return
        
        console.print(f"[green]🛠️ Herramientas MCP disponibles: {len(mcp_tools)}[/green]")
        for tool in mcp_tools:
            console.print(f"   • {tool['function']['name']}")
        
        # Mensaje del sistema para guiar a OpenAI
        system_message = {
            "role": "system", 
            "content": """Eres un asistente especializado en información de fútbol. Tienes acceso a herramientas que te permiten:

1. get_competitions: Obtener todas las competiciones de fútbol disponibles
2. get_teams_competitions: Obtener equipos de una competición específica usando su ID
3. get_teams_by_competition: Obtener todos los equipos de una competición específica
4. get_matches_by_competition: Obtener todos los partidos de una competición específica
5. get_team_by_id: Obtener información detallada de un equipo específico usando su ID
6. get_top_scorers_by_competitions: Obtener los máximos goleadores de una competición específica
7. get_player_by_id: Obtener información detallada de un jugador específico usando su ID
8. get_info_matches_of_a_player: Obtener todos los partidos en los que ha participado un jugador específico

Cuando el usuario pregunte sobre competiciones, equipos, jugadores, partidos o estadísticas, usa estas herramientas para dar información precisa y actualizada. 

Ejemplos de IDs de competiciones comunes:
- "PL": Premier League
- "CL": Champions League  
- "DFB": Bundesliga
- "SA": Serie A
- "PD": La Liga

Puedes responder preguntas sobre:
- Competiciones disponibles
- Equipos de competiciones específicas
- Información detallada de equipos
- Partidos de competiciones
- Máximos goleadores
- Información de jugadores específicos
- Historial de partidos de jugadores

Siempre usa las herramientas disponibles para obtener información real antes de responder."""
        }
        
        # Mantener historial de la conversación
        messages = [system_message]
        
        console.print("\n[dim]Ejemplos de preguntas:[/dim]")
        console.print("[dim]• ¿Qué competiciones están disponibles?[/dim]")
        console.print("[dim]• ¿Qué equipos juegan en la Premier League?[/dim]")
        console.print("[dim]• Muéstrame los equipos de la Champions League[/dim]")
        console.print("[dim]• ¿Cuáles son los partidos de la Premier League?[/dim]")
        console.print("[dim]• ¿Quiénes son los máximos goleadores de La Liga?[/dim]")
        console.print("[dim]• Dame información del equipo con ID 86 (Real Madrid)[/dim]")
        console.print("[dim]• ¿Qué información tienes del jugador con ID 44 (Cristiano Ronaldo)?[/dim]")
        console.print(f"[dim cyan]📝 Los logs se guardan en: logs/mcp_calls.txt[/dim cyan]")
        
        while True:
            # Obtener entrada del usuario
            user_input = console.input("\n[bold green]Tú:[/bold green] ")
            if user_input.lower() in ['salir', 'exit', 'quit']:
                console.print("[yellow]¡Hasta pronto![/yellow]")
                # Log del final de sesión
                log_mcp_call("SESSION_END", {"user_action": "quit"}, {"message": "Usuario terminó la sesión"})
                break
            
            # Log de la pregunta del usuario
            log_mcp_call("USER_QUESTION", {"question": user_input}, {"status": "received"})
            
            # Agregar mensaje del usuario al historial
            messages.append({"role": "user", "content": user_input})
            
            try:
                # Primera llamada a OpenAI con las herramientas MCP disponibles
                response = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=messages,
                    tools=mcp_tools,
                    tool_choice="auto"
                )
                
                assistant_message = response.choices[0].message
                messages.append(assistant_message)
                
                # Verificar si el modelo quiere usar alguna herramienta
                if assistant_message.tool_calls:
                    console.print("[dim cyan]🔧 OpenAI está usando herramientas MCP...[/dim cyan]")
                    
                    for tool_call in assistant_message.tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                        
                        # Ejecutar la herramienta MCP usando la sesión existente
                        tool_result = await execute_mcp_tool(mcp_session, function_name, function_args)
                        
                        # Agregar la respuesta de la herramienta
                        tool_response = {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": json.dumps(tool_result, ensure_ascii=False)
                        }
                        messages.append(tool_response)
                    
                    # Segunda llamada con los resultados de las herramientas
                    second_response = client.chat.completions.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        messages=messages
                    )
                    
                    final_response = second_response.choices[0].message
                    messages.append(final_response)
                    console.print(f"\n[bold blue]⚽ Asistente:[/bold blue] {final_response.content}")
                else:
                    # Si no se usaron herramientas, mostrar la respuesta directa
                    console.print(f"\n[bold blue]⚽ Asistente:[/bold blue] {assistant_message.content}")
                    
            except Exception as e:
                console.print(f"[bold red]Error: {str(e)}[/bold red]")
                # Log del error
                log_mcp_call("CHAT_ERROR", {"user_input": user_input}, {"error": str(e)})
