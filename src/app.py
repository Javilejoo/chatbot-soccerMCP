import asyncio
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from mcp_client import open_session, list_tools, invoke_tool

# Configuración
load_dotenv()
client = OpenAI()
console = Console()

async def get_mcp_tools_as_openai_tools():
    """Obtiene las herramientas del servidor MCP y las formatea para OpenAI"""
    try:
        async with open_session() as session:
            # Obtener lista de herramientas con detalles
            tools = await list_tools(session)
            console.print(f"[green]✓ Conectado al servidor MCP. {len(tools)} herramientas disponibles.[/green]")
            
            # Convertir a formato OpenAI Tools con definiciones específicas
            openai_tools = []
            
            for tool in tools:
                tool_name = tool.get("name")
                tool_desc = tool.get("description", "").strip()
                
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
            
            return openai_tools
    except Exception as e:
        console.print(f"[bold red]Error conectando al servidor MCP: {str(e)}[/bold red]")
        return []

async def execute_mcp_tool(tool_name, params=None):
    """Ejecuta una herramienta específica en el servidor MCP"""
    try:
        async with open_session() as session:
            console.print(f"[yellow]→ Ejecutando herramienta MCP: {tool_name}[/yellow]")
            if params:
                console.print(f"[dim yellow]  Parámetros: {params}[/dim yellow]")
            
            result = await invoke_tool(session, tool_name, params or {})
            console.print(f"[green]✓ Herramienta ejecutada exitosamente[/green]")
            return result
    except Exception as e:
        console.print(f"[red]Error ejecutando herramienta {tool_name}: {str(e)}[/red]")
        return {"error": str(e)}

async def main():
    """Función principal del chatbot"""
    console.print(Panel.fit("⚽ [bold blue]Chatbot de Fútbol con MCP[/bold blue]", 
                         subtitle="Pregunta sobre competiciones y equipos • Escribe 'salir' para terminar"))
    
    # Primero mostrar las herramientas disponibles (como antes)
    console.print("[yellow]🔄 Conectando al servidor MCP...[/yellow]")
    async with open_session() as session:
        tools = await list_tools(session)
        if not tools:
            console.print("[red]No se encontraron herramientas en el servidor MCP.[/red]")
            return

        console.print(f"[green]✅ Conectado. Herramientas disponibles:[/green]")
        for i, t in enumerate(tools, 1):
            name = t.get("name")
            desc = (t.get("description") or "").strip()
            console.print(f"  {i}. [bold]{name}[/bold] - {desc}")
    
    # Obtener las herramientas formateadas para OpenAI
    mcp_tools = await get_mcp_tools_as_openai_tools()
    if not mcp_tools:
        console.print("[bold red]No se pudieron cargar herramientas MCP para OpenAI.[/bold red]")
        return
    
    # Mensaje del sistema para guiar a OpenAI
    system_message = {
        "role": "system", 
        "content": """Eres un asistente especializado en información de fútbol. Tienes acceso a herramientas que te permiten:

1. get_competitions: Obtener todas las competiciones de fútbol disponibles
2. get_teams_competitions: Obtener equipos de una competición específica usando su ID

Cuando el usuario pregunte sobre competiciones o equipos, usa estas herramientas para dar información precisa y actualizada. 

Ejemplos de IDs de competiciones comunes:
- "PL": Premier League
- "CL": Champions League  
- "DFB": Bundesliga
- "SA": Serie A
- "PD": La Liga

Siempre usa las herramientas disponibles para obtener información real antes de responder."""
    }
    
    # Mantener historial de la conversación
    messages = [system_message]
    
    console.print("\n[dim]Ejemplos de preguntas:[/dim]")
    console.print("[dim]• ¿Qué competiciones están disponibles?[/dim]")
    console.print("[dim]• ¿Qué equipos juegan en la Premier League?[/dim]")
    console.print("[dim]• Muéstrame los equipos de la Champions League[/dim]")
    
    while True:
        # Obtener entrada del usuario
        user_input = console.input("\n[bold green]Tú:[/bold green] ")
        if user_input.lower() in ['salir', 'exit', 'quit']:
            console.print("[yellow]¡Hasta pronto![/yellow]")
            break
        
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
                    
                    # Ejecutar la herramienta MCP
                    tool_result = await execute_mcp_tool(function_name, function_args)
                    
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
            import traceback
            console.print(f"[dim red]{traceback.format_exc()}[/dim red]")

if __name__ == "__main__":
    asyncio.run(main())