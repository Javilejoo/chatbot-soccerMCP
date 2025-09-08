import asyncio
from mcp_client import open_session, list_tools

async def main():
    print("Connecting to local MCP server…")
    async with open_session() as session:
        print("✅ Connected")
        print()

        tools = await list_tools(session)
        if not tools:
            print("No tools returned by the server.")
            return

        print("Available MCP tools:")
        for i, t in enumerate(tools, 1):
            name = t.get("name")
            desc = (t.get("description") or "").strip()
            print(f"{i}. {name} - {desc}")

if __name__ == "__main__":
    asyncio.run(main())
