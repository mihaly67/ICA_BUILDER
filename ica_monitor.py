import sqlite3
import os
import time
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
import json

DB_PATH = "/home/misi/Jules_ICA_Builder/mcp_telemetry.db"
MEMORY_PATH = "/home/misi/Jules_ICA_Builder/agent_memory.jsonl"

console = Console()

def get_recent_mcp_logs(limit=10):
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT timestamp, tool_name, args, execution_time_ms, status, error_msg FROM mcp_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_mcp_stats():
    if not os.path.exists(DB_PATH):
        return {"total": 0, "avg_time": 0, "error_rate": 0}
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), AVG(execution_time_ms) FROM mcp_logs")
    total, avg_time = c.fetchone()
    c.execute("SELECT COUNT(*) FROM mcp_logs WHERE status='error'")
    errors = c.fetchone()[0]
    conn.close()

    total = total if total else 0
    avg_time = avg_time if avg_time else 0
    error_rate = (errors / total * 100) if total > 0 else 0
    return {"total": total, "avg_time": avg_time, "error_rate": error_rate}

def get_recent_memory(limit=5):
    if not os.path.exists(MEMORY_PATH):
        return []
    with open(MEMORY_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [json.loads(line) for line in lines[-limit:]]

def generate_layout():
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1)
    )
    layout["main"].split_row(
        Layout(name="telemetry", ratio=2),
        Layout(name="memory", ratio=1)
    )
    return layout

def make_telemetry_table():
    stats = get_mcp_stats()
    header_text = f"[bold cyan]Total Calls:[/bold cyan] {stats['total']} | [bold cyan]Avg Time:[/bold cyan] {stats['avg_time']:.1f}ms | [bold red]Error Rate:[/bold red] {stats['error_rate']:.1f}%"

    table = Table(title=header_text, expand=True)
    table.add_column("Time", justify="center", style="cyan", no_wrap=True)
    table.add_column("Tool", style="magenta")
    table.add_column("Dur (ms)", justify="right", style="green")
    table.add_column("Status", justify="center")
    table.add_column("Error", style="red")

    logs = get_recent_mcp_logs(15)



    for row in logs:
        ts_str = time.strftime('%H:%M:%S', time.localtime(row[0]))
        tool_name = row[1]
        args_json = row[2]
        exec_time = row[3]
        status = row[4]
        error_msg = str(row[5])[:40] if row[5] else ""

        status_style = "[bold green]OK[/]" if status == "success" else "[bold red]ERR[/]"

        try:
            args_obj = json.loads(args_json) if args_json else {}
        except:
            args_obj = {}

        if tool_name == "execute_bash":
            cmd = args_obj.get('command', '')
            # Vágjuk le a boilerplate útvonalakat
            cmd = cmd.replace("/home/misi/Jules_mx/venv/bin/python3", "python3")
            cmd = cmd.replace("/home/misi/Jules_ICA_Builder/src/tools/skills/", "skills/")
            cmd = cmd.replace("/home/misi/Jules_ICA_Builder/", "ica/")
            cmd = cmd.replace("tools/skills/mcp_bridge_tool.py --tool", "mcp")

            # Ha idézőjelek miatt túl hosszú a json payload a bash args-ban, takarítsuk
            cmd = re.sub(r'--args \'.*?\'', '--args {...}', cmd)

            # Hagyjunk meg egy kicsit hosszabb részt (pl. 45 karakter)
            tool_name = f"[cyan]bash[/]: {cmd[:45]}..." if len(cmd) > 45 else f"[cyan]bash[/]: {cmd}"
        elif tool_name == "write_file_mcp":
            fp = args_obj.get('filepath', '')
            tool_name = f"[cyan]write[/]: {fp.split('/')[-1]}"
        elif tool_name == "search_graph_semantic" or tool_name == "search_graph_fts":
            tool_name = f"[magenta]search[/]: {args_obj.get('query', '')[:20]}"
        elif tool_name == "execute_python":
            tool_name = "[cyan]python_eval[/]: (script)"
        else:
            tool_name = f"[magenta]{tool_name}[/]"

        table.add_row(ts_str, tool_name, f"{exec_time:.1f}" if isinstance(exec_time, (int, float)) else str(exec_time)[:5], status_style, error_msg)
    return Panel(table, title="[bold yellow]MCP Telemetry (Live)[/bold yellow]")

def make_memory_view():
    memories = get_recent_memory(7)
    content = ""
    for mem in memories:
        cat = mem.get("category", "Unknown")
        ts = mem.get("timestamp", "").split("T")[0]
        text = mem.get("content", "")[:80] + "..."
        content += f"[cyan]{ts}[/] [bold]{cat}[/]\n[white]{text}[/]\n\n"

    return Panel(content, title="[bold blue]Agent Memory Stream[/bold blue]")

def main():
    layout = generate_layout()
    with Live(layout, refresh_per_second=2, screen=True) as live:
        try:
            while True:
                layout["header"].update(Panel(Align.center("[bold white on blue] 🧠 JULES ICA SYSTEM MONITOR [/bold white on blue]")))
                layout["telemetry"].update(make_telemetry_table())
                layout["memory"].update(make_memory_view())
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
