from openai import OpenAI
from dotenv import load_dotenv
import os
import asyncio
import json
import time
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from mcp_client import open_session, open_fs_session, open_git_session, list_tools, invoke_tool

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
    """Obtiene las herramientas de ambos servidores MCP (Soccer + Filesystem + Git) y las formatea para OpenAI"""
    openai_tools = []
    soccer_available = False
    filesystem_available = False
    git_available = False
    
    # ==================== SOCCER MCP SERVER ====================
    try:
        console.print("[yellow]🔄 Conectando al servidor Soccer MCP...[/yellow]")
        async with open_session() as session:
            # Obtener lista de herramientas Soccer MCP
            soccer_tools = await list_tools(session)
            console.print(f"[green]✓ Soccer MCP conectado: {len(soccer_tools)} herramientas[/green]")
            soccer_available = True
            
            # Log de la conexión inicial
            log_mcp_call("SOCCER_CONNECTION", {"action": "list_tools"}, {"tools_count": len(soccer_tools), "tools": [t.get("name") for t in soccer_tools]})
            
            # Convertir herramientas Soccer MCP a formato OpenAI
            for tool in soccer_tools:
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
            
    except Exception as e:
        console.print(f"[bold red]⚠️ Error conectando al servidor Soccer MCP: {str(e)}[/bold red]")
        log_mcp_call("SOCCER_CONNECTION_ERROR", {}, {"error": str(e)})
    
    # ==================== FILESYSTEM MCP SERVER ====================
    try:
        console.print("[yellow]🔄 Conectando al servidor Filesystem MCP...[/yellow]")
        async with open_fs_session() as fs_session:
            # Obtener lista de herramientas Filesystem MCP
            fs_tools = await list_tools(fs_session)
            console.print(f"[green]✓ Filesystem MCP conectado: {len(fs_tools)} herramientas[/green]")
            filesystem_available = True
            
            # Log de la conexión al filesystem
            log_mcp_call("FILESYSTEM_CONNECTION", {"action": "list_tools"}, {"tools_count": len(fs_tools), "tools": [t.get("name") for t in fs_tools]})
            
            # Convertir herramientas Filesystem MCP a formato OpenAI
            for tool in fs_tools:
                tool_name = tool.get("name")
                
                if tool_name == "read_file":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_read_file",
                            "description": "Lee el contenido de un archivo del sistema de archivos",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta del archivo a leer"
                                    }
                                },
                                "required": ["path"]
                            }
                        }
                    })
                elif tool_name == "read_text_file":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_read_text_file",
                            "description": "Lee el contenido de un archivo de texto específicamente",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta del archivo de texto a leer"
                                    }
                                },
                                "required": ["path"]
                            }
                        }
                    })
                elif tool_name == "read_media_file":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_read_media_file",
                            "description": "Lee archivos multimedia (imágenes, audio, video) y devuelve información sobre el archivo",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta del archivo multimedia a leer"
                                    }
                                },
                                "required": ["path"]
                            }
                        }
                    })
                elif tool_name == "read_multiple_files":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_read_multiple_files",
                            "description": "Lee múltiples archivos de una vez",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "paths": {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        },
                                        "description": "Lista de rutas de archivos a leer"
                                    }
                                },
                                "required": ["paths"]
                            }
                        }
                    })
                elif tool_name == "write_file":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_write_file",
                            "description": "Escribe contenido en un archivo del sistema de archivos",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta del archivo a escribir"
                                    },
                                    "content": {
                                        "type": "string",
                                        "description": "Contenido a escribir en el archivo"
                                    }
                                },
                                "required": ["path", "content"]
                            }
                        }
                    })
                elif tool_name == "edit_file":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_edit_file",
                            "description": "Edita partes específicas de un archivo existente",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta del archivo a editar"
                                    },
                                    "edits": {
                                        "type": "array",
                                        "description": "Lista de ediciones a realizar",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "oldText": {
                                                    "type": "string",
                                                    "description": "Texto a reemplazar"
                                                },
                                                "newText": {
                                                    "type": "string",
                                                    "description": "Nuevo texto"
                                                }
                                            },
                                            "required": ["oldText", "newText"]
                                        }
                                    }
                                },
                                "required": ["path", "edits"]
                            }
                        }
                    })
                elif tool_name == "create_directory":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_create_directory",
                            "description": "Crea un nuevo directorio",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta del directorio a crear"
                                    }
                                },
                                "required": ["path"]
                            }
                        }
                    })
                elif tool_name == "list_directory":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_list_directory",
                            "description": "Lista el contenido de un directorio",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta del directorio a listar"
                                    }
                                },
                                "required": ["path"]
                            }
                        }
                    })
                elif tool_name == "list_directory_with_sizes":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_list_directory_with_sizes",
                            "description": "Lista el contenido de un directorio incluyendo información de tamaño",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta del directorio a listar"
                                    }
                                },
                                "required": ["path"]
                            }
                        }
                    })
                elif tool_name == "directory_tree":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_directory_tree",
                            "description": "Muestra la estructura de árbol de un directorio",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta del directorio para mostrar como árbol"
                                    },
                                    "depth": {
                                        "type": "integer",
                                        "description": "Profundidad máxima del árbol (opcional)"
                                    }
                                },
                                "required": ["path"]
                            }
                        }
                    })
                elif tool_name == "move_file":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_move_file",
                            "description": "Mueve o renombra un archivo",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "source": {
                                        "type": "string",
                                        "description": "Ruta del archivo origen"
                                    },
                                    "destination": {
                                        "type": "string",
                                        "description": "Ruta del archivo destino"
                                    }
                                },
                                "required": ["source", "destination"]
                            }
                        }
                    })
                elif tool_name == "search_files":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_search_files",
                            "description": "Busca archivos en el sistema de archivos",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "pattern": {
                                        "type": "string",
                                        "description": "Patrón de búsqueda para los archivos"
                                    },
                                    "path": {
                                        "type": "string",
                                        "description": "Directorio donde buscar (opcional)"
                                    }
                                },
                                "required": ["pattern"]
                            }
                        }
                    })
                elif tool_name == "get_file_info":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_get_file_info",
                            "description": "Obtiene información detallada de un archivo o directorio",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta del archivo o directorio"
                                    }
                                },
                                "required": ["path"]
                            }
                        }
                    })
                elif tool_name == "list_allowed_directories":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "fs_list_allowed_directories",
                            "description": "Lista los directorios a los que el servidor MCP tiene acceso",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    })
            
    except Exception as e:
        console.print(f"[bold red]⚠️ Error conectando al servidor Filesystem MCP: {str(e)}[/bold red]")
        log_mcp_call("FILESYSTEM_CONNECTION_ERROR", {}, {"error": str(e)})

    # ==================== GIT MCP SERVER ====================
    try:
        async with open_git_session() as git_session:
            # Obtener lista de herramientas Git MCP
            git_tools = await list_tools(git_session)
            console.print(f"[green]✓ Git MCP conectado: {len(git_tools)} herramientas[/green]")
            git_available = True
            # Log de la conexión al git
            log_mcp_call("GIT_CONNECTION", {"action": "list_tools"}, {"tools_count": len(git_tools), "tools": [t.get("name") for t in git_tools]})
            # Convertir herramientas Git MCP a formato OpenAI
            for tool in git_tools:
                tool_name = tool.get("name")
                if tool_name == "git_status":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_status",
                            "description": "Obtiene el estado actual del repositorio Git",
                            "parameters": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    })
                elif tool_name == "git_diff_unstaged":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_diff_unstaged",
                            "description": "Muestra las diferencias de archivos no añadidos al área de preparación",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta específica del archivo (opcional)"
                                    }
                                },
                                "required": []
                            }
                        }
                    })
                elif tool_name == "git_diff_staged":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_diff_staged",
                            "description": "Muestra las diferencias de archivos en el área de preparación",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta específica del archivo (opcional)"
                                    }
                                },
                                "required": []
                            }
                        }
                    })
                elif tool_name == "git_diff":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_diff",
                            "description": "Muestra las diferencias entre commits, ramas o archivos",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "target": {
                                        "type": "string",
                                        "description": "Commit, rama o archivo para comparar (opcional)"
                                    }
                                },
                                "required": []
                            }
                        }
                    })
                elif tool_name == "git_commit":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_commit",
                            "description": "Realiza un commit con los archivos en el área de preparación",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "message": {
                                        "type": "string",
                                        "description": "Mensaje del commit"
                                    }
                                },
                                "required": ["message"]
                            }
                        }
                    })
                elif tool_name == "git_add":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_add",
                            "description": "Añade archivos al área de preparación",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "paths": {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        },
                                        "description": "Lista de rutas de archivos o directorios a añadir"
                                    }
                                },
                                "required": ["paths"]
                            }
                        }
                    })
                elif tool_name == "git_reset":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_reset",
                            "description": "Resetea archivos del área de preparación o commits",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "paths": {
                                        "type": "array",
                                        "items": {
                                            "type": "string"
                                        },
                                        "description": "Lista de rutas de archivos a resetear (opcional)"
                                    },
                                    "mode": {
                                        "type": "string",
                                        "description": "Modo de reset: soft, mixed, hard (opcional)",
                                        "enum": ["soft", "mixed", "hard"]
                                    }
                                },
                                "required": []
                            }
                        }
                    })
                elif tool_name == "git_log":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_log",
                            "description": "Muestra el historial de commits",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "max_count": {
                                        "type": "integer",
                                        "description": "Número máximo de commits a mostrar (opcional)"
                                    },
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta específica para filtrar el historial (opcional)"
                                    }
                                },
                                "required": []
                            }
                        }
                    })
                elif tool_name == "git_create_branch":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_create_branch",
                            "description": "Crea una nueva rama en el repositorio Git",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Nombre de la nueva rama"
                                    }
                                },
                                "required": ["name"]
                            }
                        }
                    })
                elif tool_name == "git_checkout":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_checkout",
                            "description": "Cambia a una rama o commit específico",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "target": {
                                        "type": "string",
                                        "description": "Nombre de la rama o hash del commit"
                                    }
                                },
                                "required": ["target"]
                            }
                        }
                    })
                elif tool_name == "git_show":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_show",
                            "description": "Muestra información detallada de un commit específico",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "commit": {
                                        "type": "string",
                                        "description": "Hash del commit o referencia (opcional, por defecto HEAD)"
                                    }
                                },
                                "required": []
                            }
                        }
                    })
                elif tool_name == "git_init":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_init",
                            "description": "Inicializa un nuevo repositorio Git",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "Ruta donde inicializar el repositorio (opcional)"
                                    }
                                },
                                "required": []
                            }
                        }
                    })
                elif tool_name == "git_branch":
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": "git_branch",
                            "description": "Lista, crea o elimina ramas",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "Nombre de la rama para crear o eliminar (opcional)"
                                    },
                                    "delete": {
                                        "type": "boolean",
                                        "description": "Si es true, elimina la rama especificada (opcional)"
                                    }
                                },
                                "required": []
                            }
                        }
                    })
    except Exception as e:
        console.print(f"[bold red]⚠️ Error conectando al servidor Git MCP: {str(e)}[/bold red]")
        log_mcp_call("GIT_CONNECTION_ERROR", {}, {"error": str(e)})

    # ==================== RESUMEN ====================
    status_parts = []
    if soccer_available:
        status_parts.append("⚽ Fútbol")
    if filesystem_available:
        status_parts.append("📁 Archivos")
    if git_available:
        status_parts.append("🧑‍💻 Git")
    
    if status_parts:
        console.print(f"[green]🎯 Servidores MCP activos: {' + '.join(status_parts)}[/green]")
    else:
        console.print(f"[bold red]❌ No se pudo conectar a ningún servidor MCP[/bold red]")
    
    console.print(f"[green]🛠️ Total herramientas disponibles: {len(openai_tools)}[/green]")
    return openai_tools, soccer_available, filesystem_available, git_available

async def execute_mcp_tool(soccer_session, fs_session, git_session, tool_name, params=None):
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
    console.print(Panel.fit("⚽📁 [bold blue]Chatbot MCP - Fútbol & Archivos[/bold blue]", 
                         subtitle="Pregunta sobre fútbol o realiza operaciones con archivos • Escribe 'salir' para terminar"))
    
    # Obtener herramientas disponibles primero
    mcp_tools, soccer_available, filesystem_available, git_available = await get_all_mcp_tools_as_openai_tools()
    if not mcp_tools:
        console.print("[bold red]No se pudieron cargar herramientas MCP. Verificar conexión a servidores.[/bold red]")
        return
    
    # Mostrar herramientas disponibles
    console.print(f"[green]🛠️ Total herramientas disponibles: {len(mcp_tools)}[/green]")
    
    if soccer_available:
        soccer_tools = [tool for tool in mcp_tools if not tool['function']['name'].startswith('fs_')]
        console.print(f"[yellow]⚽ Herramientas de Fútbol ({len(soccer_tools)}):[/yellow]")
        for tool in soccer_tools:
            console.print(f"   • {tool['function']['name']}")
    
    if filesystem_available:
        fs_tools = [tool for tool in mcp_tools if tool['function']['name'].startswith('fs_')]
        console.print(f"[blue]📁 Herramientas de Archivos ({len(fs_tools)}):[/blue]")
        for tool in fs_tools:
            console.print(f"   • {tool['function']['name'][3:]}")  # Sin prefijo fs_
    
    if git_available:
        git_tools = [tool for tool in mcp_tools if tool['function']['name'].startswith('git_')]
        console.print(f"[magenta]🧑‍💻 Herramientas de Git ({len(git_tools)}):[/magenta]")
        for tool in git_tools:
            console.print(f"   • {tool['function']['name']}")  # Sin remover prefijo ya que todas empiezan con git_

    # Preparar capabilities antes de las conexiones
    capabilities = []
    if soccer_available:
        capabilities.append("""INFORMACIÓN DE FÚTBOL:
- get_competitions: Obtener todas las competiciones de fútbol disponibles
- get_teams_competitions: Obtener equipos de una competición específica usando su ID
- get_teams_by_competition: Obtener todos los equipos de una competición específica
- get_matches_by_competition: Obtener todos los partidos de una competición específica
- get_team_by_id: Obtener información detallada de un equipo específico usando su ID
- get_top_scorers_by_competitions: Obtener los máximos goleadores de una competición específica
- get_player_by_id: Obtener información detallada de un jugador específico usando su ID
- get_info_matches_of_a_player: Obtener todos los partidos en los que ha participado un jugador específico

Ejemplos de IDs de competiciones: "PL" (Premier League), "CL" (Champions League), "DFB" (Bundesliga), "SA" (Serie A), "PD" (La Liga)""")
    
    if filesystem_available:
        capabilities.append("""OPERACIONES CON ARCHIVOS:
- fs_read_file: Leer el contenido de un archivo
- fs_read_text_file: Leer archivos de texto específicamente
- fs_read_media_file: Leer archivos multimedia (imágenes, audio, video)
- fs_read_multiple_files: Leer múltiples archivos de una vez
- fs_write_file: Escribir contenido a un archivo (crear o sobrescribir)
- fs_edit_file: Editar partes específicas de un archivo existente
- fs_create_directory: Crear un nuevo directorio
- fs_list_directory: Listar archivos y directorios en una ruta
- fs_list_directory_with_sizes: Listar directorio con información de tamaño
- fs_directory_tree: Mostrar estructura de árbol de directorios
- fs_move_file: Mover o renombrar archivos/directorios
- fs_search_files: Buscar archivos por nombre o patrón
- fs_get_file_info: Obtener información detallada de un archivo (tamaño, fecha, etc.)
- fs_list_allowed_directories: Listar directorios accesibles por el servidor MCP""")
        
    if git_available:
        capabilities.append("""OPERACIONES CON GIT:
- git_status: Obtener el estado actual del repositorio Git
- git_diff_unstaged: Mostrar diferencias de archivos no añadidos al área de preparación
- git_diff_staged: Mostrar diferencias de archivos en el área de preparación
- git_diff: Mostrar diferencias entre commits, ramas o archivos
- git_commit: Realizar un commit con los archivos en el área de preparación
- git_add: Añadir archivos al área de preparación
- git_reset: Resetear archivos del área de preparación o commits
- git_log: Mostrar el historial de commits
- git_create_branch: Crear una nueva rama en el repositorio Git
- git_checkout: Cambiar a una rama o commit específico
- git_show: Mostrar información detallada de un commit específico
- git_init: Inicializar un nuevo repositorio Git
- git_branch: Listar, crear o eliminar ramas""")

    # Usar context managers para las sesiones MCP
    if soccer_available and filesystem_available and git_available:
        # Ambos servidores disponibles
        async with open_session() as soccer_session, open_fs_session() as fs_session, open_git_session() as git_session:
            console.print("[green]✓ Conexiones a Soccer MCP, Filesystem MCP y Git MCP establecidas[/green]")
            await run_chat_loop(soccer_session, fs_session, git_session, capabilities, mcp_tools)
    elif soccer_available:
        # Solo Soccer MCP disponible
        async with open_session() as soccer_session:
            console.print("[green]✓ Conexión a Soccer MCP establecida[/green]")
            await run_chat_loop(soccer_session, None, None, capabilities, mcp_tools)
    elif filesystem_available:
        # Solo Filesystem MCP disponible
        async with open_fs_session() as fs_session:
            console.print("[green]✓ Conexión a Filesystem MCP establecida[/green]")
            await run_chat_loop(None, fs_session, None, capabilities, mcp_tools)
    elif git_available:
        # Solo Git MCP disponible
        async with open_git_session() as git_session:
            console.print("[green]✓ Conexión a Git MCP establecida[/green]")
            await run_chat_loop(None, None, git_session, capabilities, mcp_tools)
    else:
        console.print("[bold red]No hay servidores MCP disponibles[/bold red]")
        return

async def run_chat_loop(soccer_session, fs_session, git_session, capabilities, mcp_tools):
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
                    tool_result = await execute_mcp_tool(soccer_session, fs_session, git_session, function_name, function_args)

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
