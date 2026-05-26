#!/usr/bin/env python3
import os
import sys
import json
import argparse
import asyncio
import shlex
import shutil
import re
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# -- BIZTONSÁGI SZABÁLYOK (A "PALACK NYAKA") --
# A Builder csak itt garázdálkodhat:
BUILDER_JAIL_DIR = "/home/misi/Jules_ICA_Builder"

# Tiltott bash parancsok regex (szóhatárokkal, hogy ne blokkolja a "success"-t a s u miatt)
BANNED_COMMANDS_REGEX = re.compile(r'\b(sudo|su|systemctl|reboot|shutdown|kill|pkill|killall|mkfs)\b')

def is_path_safe(path_str):
    """Ellenőrzi, hogy a cél útvonal a jail-en belül van-e."""
    if not path_str:
        return False
    try:
        clean_path = os.path.normpath(path_str)
        # Csak abszolút útvonalakat fogadunk el, amik a jailen belül vannak.
        # Ha relatív útvonalat ad meg, a VPS szerver a saját munkakönyvtárából oldaná fel,
        # ami egy jail-törést (path traversal) tenne lehetővé.
        if not os.path.isabs(clean_path):
            return False

        if not clean_path.startswith(BUILDER_JAIL_DIR):
            return False
        return True
    except Exception:
        return False

def check_security(tool_name, args_dict):
    """Ellenőrzi a kérést a biztonsági szabályok alapján."""

    # 1. Fájlműveletek ellenőrzése
    if tool_name in ["read_file", "write_file", "list_files"]:
        path = args_dict.get("filepath") or args_dict.get("path")
        if not is_path_safe(path):
            return False, f"SECURITY BLOCK: Hozzáférés megtagadva a következőhöz: {path}. Kérlek használj abszolút útvonalakat, és csak a {BUILDER_JAIL_DIR} könyvtárban dolgozhatsz!"

    # 2. Bash futtatás ellenőrzése
    elif tool_name == "execute_bash":
        command = args_dict.get("command", "")

        # Regex alapú tiltott szó keresés
        match = BANNED_COMMANDS_REGEX.search(command)
        if match:
            return False, f"SECURITY BLOCK: A '{match.group(1)}' parancs használata tiltott a Builder számára!"

        if "rm -rf /" in command:
             return False, "SECURITY BLOCK: A gyökérkönyvtár törlése tiltott!"

    return True, "OK"


async def run_builder_client(tool_name, args_dict):
    # Biztonsági ellenőrzés
    is_safe, msg = check_security(tool_name, args_dict)
    if not is_safe:
        return msg

    server_params = StdioServerParameters(
        command="ssh",
        args=[
            "-o", "StrictHostKeyChecking=no",
            f"misi@{os.environ.get('VPS_HOST', '5.189.163.88')}",
            "/home/misi/Jules_ICA_Builder/venv/bin/python3",
            "/home/misi/Jules_ICA_Builder/tools/skills/vps_mcp_server.py"
        ],
        env=os.environ.copy()
    )

    if os.environ.get("VPS_PWD"):
        if shutil.which("sshpass"):
            server_params.command = "sshpass"
            server_params.args = ["-p", os.environ.get("VPS_PWD"), "ssh"] + server_params.args
        else:
            print("⚠️ sshpass nem található, a jelszavas belépés nem fog működni! Próbálj kulcsot beállítani.", file=sys.stderr)

    elif os.environ.get("VPS_SSH_KEY"):
        with open("temp_mcp_key", "w") as f:
            f.write(os.environ.get("VPS_SSH_KEY") + "\n")
        os.chmod("temp_mcp_key", 0o600)
        server_params.args = ["-i", "temp_mcp_key"] + server_params.args

    print(f"🛡️ Csatlakozás a VPS MCP Szerverhez (BUILDER MÓD)...", file=sys.stderr)

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Meghívjuk a toolt
                result = await session.call_tool(tool_name, arguments=args_dict)

                outputs = []
                if hasattr(result, "content"):
                    for content in result.content:
                        if content.type == "text":
                            outputs.append(content.text)
                return "\n".join(outputs)
    finally:
        if os.path.exists("temp_mcp_key"):
            os.remove("temp_mcp_key")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Builder MCP Kliens Híd (Biztonsági Szűréssel)")
    parser.add_argument("--tool", type=str, required=True, help="Az MCP tool neve")
    parser.add_argument("--args", type=str, required=True, help="JSON argumentumok")

    args = parser.parse_args()
    try:
        args_dict = json.loads(args.args)
    except Exception as e:
        print(f"Érvénytelen JSON argumentum: {e}")
        sys.exit(1)

    try:
        result = asyncio.run(run_builder_client(args.tool, args_dict))
        print(result)
    except Exception as e:
        print(f"❌ Builder Kliens hiba: {e}")
