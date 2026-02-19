import asyncio
import json
import logging
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logger = logging.getLogger(__name__)

server = Server("code-mcp")

CLAUDE_CLI = os.environ.get("CLAUDE_CLI", "claude")
DEFAULT_MODEL = os.environ.get("CODE_MCP_MODEL", "opus")
DEFAULT_MAX_TURNS = int(os.environ.get("CODE_MCP_MAX_TURNS", "60"))

# Session tracking: cwd -> session_id
# Lives for the duration of the MCP server process (= one agent run)
_sessions: dict[str, str] = {}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="code",
            description=(
                "Execute a coding task using Claude Code CLI. "
                "Maintains conversation context per working directory — "
                "subsequent calls resume the same session so Claude remembers "
                "all prior edits, file reads, and context. "
                "Use for: editing files, fixing bugs, refactoring, creating files, "
                "running commands, or any codebase modification."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "The coding task to perform (e.g., 'fix the import error in worker.py', 'add logging to the database module')",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory for the coding task (default: server's working directory)",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model to use: 'sonnet', 'opus', 'haiku' (default: sonnet)",
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Max agentic turns (default: 30)",
                    },
                    "new_session": {
                        "type": "boolean",
                        "description": "Force a fresh session, discarding prior context for this cwd",
                        "default": False,
                    },
                },
                "required": ["task"],
            },
        ),
    ]


async def _run_claude(
    task: str,
    cwd: str,
    model: str,
    max_turns: int,
    session_id: str | None,
) -> dict:
    """Run claude CLI and return parsed JSON result."""
    cmd = [
        CLAUDE_CLI,
        "--dangerously-skip-permissions",
        "-p",
        "--output-format", "json",
        "--model", model,
        "--max-turns", str(max_turns),
    ]

    if session_id:
        cmd.extend(["--resume", session_id])

    logger.info(f"Running claude: cwd={cwd} session={session_id or 'new'} model={model}")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )

    stdout, stderr = await proc.communicate(task.encode())

    if proc.returncode != 0:
        err = stderr.decode().strip()
        logger.error(f"claude exited {proc.returncode}: {err}")
        return {"error": f"claude exited {proc.returncode}: {err}"}

    # Parse the JSON output (single JSON object with --output-format json)
    raw = stdout.decode().strip()
    if not raw:
        return {"error": "empty response from claude"}

    # May have multiple lines if streaming; take the last valid JSON
    result = None
    for line in reversed(raw.split("\n")):
        line = line.strip()
        if not line:
            continue
        try:
            result = json.loads(line)
            break
        except json.JSONDecodeError:
            continue

    if result is None:
        return {"error": f"could not parse JSON from claude output: {raw[:500]}"}

    return result


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "code":
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    task = arguments["task"]
    cwd = arguments.get("cwd", os.getcwd())
    model = arguments.get("model", DEFAULT_MODEL)
    max_turns = arguments.get("max_turns", DEFAULT_MAX_TURNS)
    new_session = arguments.get("new_session", False)

    # Resolve session
    session_id = None if new_session else _sessions.get(cwd)

    try:
        result = await _run_claude(task, cwd, model, max_turns, session_id)
    except Exception as e:
        logger.exception("Error running claude")
        return [TextContent(type="text", text=f"Error: {e}")]

    if "error" in result and "session_id" not in result:
        return [TextContent(type="text", text=result["error"])]

    # Store session for continuity
    if sid := result.get("session_id"):
        _sessions[cwd] = sid
        logger.info(f"Session for {cwd}: {sid}")

    # Build response
    output = result.get("result", "")
    num_turns = result.get("num_turns", 0)
    cost = result.get("total_cost_usd", 0)
    is_error = result.get("is_error", False)

    parts = []
    if is_error:
        parts.append("[ERROR]")
    parts.append(output)
    parts.append(f"\n---\nturns: {num_turns} | cost: ${cost:.4f} | session: {_sessions.get(cwd, 'none')}")

    return [TextContent(type="text", text="\n".join(parts))]


async def run():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
