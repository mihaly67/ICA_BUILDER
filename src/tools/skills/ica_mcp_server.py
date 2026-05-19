#!/usr/bin/env python3
"""
Jules VPS MCP Szerver (Model Context Protocol)
Ez a szerver a VPS-en (8 mag, 24GB RAM, 800GB SSD) fut, és stdio-n vagy SSE-n keresztül MCP protokollon
kiajánlja a VPS helyi erőforrásait (fájlrendszer, bash futtatás, RAG keresés, Memória Regiszter) a lokális Jules Sandboxnak.

Függőségek: mcp, anyio, sqlite3, requests
Telepítés: pip install mcp
"""
import os
import sys
import json
import sqlite3
import subprocess
import requests
import anyio
from mcp.server.fastmcp import FastMCP

# Próbáljuk betölteni a környezeti változókat a VPS ~/.env fájljából
env_file = os.path.expanduser("~/Jules_mx/.env")
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, val = line.strip().split("=", 1)
                os.environ[key] = val


# Létrehozunk egy MCP szervert
mcp = FastMCP("Jules-ICA-Cognitive-Engine")


# Konfiguráció
TARGET_DIR = "/home/misi/Jules_ICA_Builder"
RAG_PATH_1 = "/home/misi/Rag_epites, chatbot_csv_data_llm_RAG/"
RAG_PATH_2 = "/home/misi/BRAIN2_DEV_RAG/"
MEMORY_FILE = os.path.join(TARGET_DIR, "agent_memory.jsonl")

@mcp.tool()
def read_system_protocols() -> str:
    """Visszaadja a kötelező viselkedési szabályokat és protokollokat az ICA Agent számára."""
    protocol = (
        "1. IDENTITÁS: Jules ICA Builder vagy. Nem rajtag.\n"
        "2. SILENT MODE: A Kognitív Ciklust belsőleg fusd le, de csak '[KOGNITÍV CIKLUS LEFUTOTT]' formában jelezd.\n"
        "3. KÖZPONTI RAG: Minden tudás a " + RAG_PATH_1 + " és " + RAG_PATH_2 + " mappákban van.\n"
    )
    return protocol

@mcp.tool()
def get_memory(lines: int = 10) -> str:
    """Beolvassa az agent hosszú távú JSONL memóriáját, hogy tudja, mi történt korábban."""
    if not os.path.exists(MEMORY_FILE):
        return "Nincs elérhető memória."
    try:
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])
    except Exception as e:
        return f"Hiba a memória olvasásakor: {e}"


def get_budapest_2026_time() -> str:
    """Generál egy garantáltan 2026-os Közép-Európai (Budapest) időbélyeget."""
    import datetime
    try:
        import pytz
        tz = pytz.timezone("Europe/Budapest")
        now = datetime.datetime.now(tz)
    except ImportError:
        now = datetime.datetime.now()

    now_2026 = now.replace(year=2026)
    return now_2026.strftime("%Y-%m-%dT%H:%M:%S")

@mcp.tool()
def write_memory(category: str, content: str) -> str:
    """Beleír egy új bejegyzést a JSONL memóriába (Garantált 2026/Budapest)."""
    import json
    entry = {
        "timestamp": get_budapest_2026_time(),
        "category": category,
        "content": content
    }
    try:
        with open(MEMORY_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")
        return "✅ Memória sikeresen mentve."
    except Exception as e:
        return f"Hiba a mentésnél: {e}"


@mcp.tool()
def search_rag_labels(query: str) -> str:
    """Keres az előre felcímkézett (Llama által processzált) RAG repók között mindkét RAG mappában."""
    import json
    query_lower = query.lower()
    matches = []

    for path in [RAG_PATH_1, RAG_PATH_2]:
        label_file = os.path.join(path, "REPO_LABELS.json")
        if os.path.exists(label_file):
            try:
                with open(label_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for repo, info in data.items():
                    if query_lower in repo.lower() or query_lower in info.get("summary", "").lower():
                        matches.append(f"[{os.path.basename(path.rstrip('/'))}] Repo: {repo} | Summary: {info.get('summary')}")
            except Exception as e:
                matches.append(f"Hiba a(z) {path} olvasásakor: {e}")
        else:
            matches.append(f"Nincs REPO_LABELS.json itt: {path}")

    if not matches or all(m.startswith("Nincs REPO") or m.startswith("Hiba") for m in matches):
        return "Nincs találat."
    return "\n".join(matches)


# --- ALAPVETŐ RENDSZER ESZKÖZÖK ---

@mcp.tool()
async def execute_bash(command: str) -> str:
    """
    Futtat egy bash parancsot a VPS-en.
    PIPELINE GATE: Fájlba írás (>, >>, tee) SZIGORÚAN TILOS a kódgenerálási gát megkerülése miatt!
    Használd a write_file_mcp eszközt!
    """
    import re
    blocked_patterns = [r'(?<!2)>', r'>>', r'\\btee\\b']
    for pattern in blocked_patterns:
        if re.search(pattern, command):
            return f"🚨 BLOKKOLVA [BASH GUARDRAIL]: Fájlba írás vagy fájl-átirányítás (>, >>, tee) a Bash-en keresztül szigorúan TILOS! Az AI-nak kötelezően a Pipeline Gate-tel védett `write_file_mcp` eszközt kell használnia erre a célra!"

    if "rm -rf /" in command or "mkfs" in command:
         return "Hiba: Veszélyes parancs letiltva a sandboxban."

    try:
        import subprocess
        import os
        work_dir = os.path.expanduser("~/Jules_ICA_Builder/")

        if "BRAIN2_DEV_RAG" in command and "rm" in command:
             return "🚨 BLOKKOLVA [BASH GUARDRAIL]: Tilos a RAG adatbázis törlése!"

        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=work_dir)
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except subprocess.CalledProcessError as e:
        return f"Hiba a Bash futtatásakor (Kód: {e.returncode}):\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}"








@mcp.tool()
async def list_files_mcp(directory: str) -> str:
    """Kilistázza a VPS-en lévő fájlokat egy adott könyvtárban."""
    target_dir = os.path.expanduser(directory)
    if not os.path.exists(target_dir):
        return f"Hiba: A(z) {target_dir} könyvtár nem létezik."
    try:
        files = os.listdir(target_dir)
        return "\n".join(files)
    except Exception as e:
        return f"Hiba olvasáskor: {str(e)}"

@mcp.tool()
async def read_file_mcp(filepath: str) -> str:
    """Beolvassa egy fájl tartalmát a VPS-ről."""
    target_file = os.path.expanduser(filepath)
    if not os.path.exists(target_file):
        return f"Hiba: A fájl nem létezik: {target_file}"
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Hiba beolvasáskor: {str(e)}"


@mcp.tool()
async def git_commit_and_push(repo_path: str, commit_message: str, branch: str = "main") -> str:
    """
    VPS Git Menedzser: Hozzáadja a változásokat, commitol, és pushol egy adott branch-re a VPS-en lévő repóban.
    Kiválóan alkalmas arra, hogy a lokális homokozóból irányítva a VPS autonóm módon elmentse a kódokat a GitHubra.
    """
    target_dir = os.path.expanduser(repo_path)
    if not os.path.exists(target_dir):
        return f"Hiba: A {target_dir} mappa nem létezik."

    try:
        # Git Add
        subprocess.run(["git", "add", "."], cwd=target_dir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Git Commit (Ha van mit)
        commit_res = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Git Push
        push_res = subprocess.run(
            ["git", "push", "origin", branch],
            cwd=target_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        return f"Git művelet sikeres.\nCommit:\n{commit_res.stdout}\nPush:\n{push_res.stderr} {push_res.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Git hiba: {e.stderr} {e.stdout}"

@mcp.tool()
async def write_file_mcp(filepath: str, content: str) -> str:
    """
    Fájl írása vagy felülírása a VPS-en.
    PIPELINE GATE: Csak akkor ír, ha van blueprint.md ami tartalmazza a HIVATALOS ADR struktúrát!
    """
    import os
    import ast

    target_path = os.path.expanduser(filepath)
    is_blueprint = "blueprint.md" in target_path.lower()

    # 1. Pipeline Gate: Blueprint tartalom / ADR Séma ellenőrzése
    required_adr_headers = ["## context", "## decision", "## consequences", "## status"]

    if is_blueprint:
        # Ha a blueprint-et írjuk éppen, megvizsgáljuk, hogy az LLM nem csak halandzsát ír-e bele
        content_lower = content.lower()
        missing_headers = [h for h in required_adr_headers if h not in content_lower]
        if missing_headers:
            return f"🚨 BLOKKOLVA [ADR SÉMA GUARDRAIL]: A `blueprint.md` nem felel meg a Michael Nygard (vagy MADR) Architecture Decision Record szabványnak!\nHiányzó kötelező fejezetek: {missing_headers}.\nA RAG adatbázis szerint tilos halandzsa tervrajzot menteni."
    else:
        # Ha kódot / mást írunk, ellenőrizzük, hogy létezik-e és érvényes-e a blueprint
        work_dir = os.path.dirname(target_path)
        blueprint_found = False
        blueprint_path = ""
        while work_dir and work_dir != "/":
            potential_path = os.path.join(work_dir, "blueprint.md")
            if os.path.exists(potential_path):
                blueprint_found = True
                blueprint_path = potential_path
                break
            work_dir = os.path.dirname(work_dir)

        if not blueprint_found:
             blueprint_path = os.path.expanduser("~/Jules_ICA_Builder/blueprint.md")
             if os.path.exists(blueprint_path):
                 blueprint_found = True

        if not blueprint_found:
             return "🚨 BLOKKOLVA [PIPELINE GATE]: Nem találtam `blueprint.md` dokumentumot! Tilos kódot írni a tervezési fázis lezárása nélkül!"

        # Ha megvan a fájl, olvassuk ki a tartalmát, és nézzük meg, hogy halandzsa-e (esetleg valaki üresen hozta létre)
        with open(blueprint_path, "r", encoding="utf-8") as bf:
             bp_content = bf.read().lower()
             missing_headers = [h for h in required_adr_headers if h not in bp_content]
             if missing_headers:
                  return f"🚨 BLOKKOLVA [PIPELINE GATE]: A meglévő `blueprint.md` érvénytelen (nem igazi ADR tervrajz)!\nHiányzó fejezetek: {missing_headers}. Csinálj rendes tervet a kódolás előtt!"

    # 2. Pipeline Gate: AST Szintaktikai ellenőrzés Python kódok esetén
    if target_path.endswith('.py'):
        try:
            ast.parse(content)
        except SyntaxError as e:
            return f"🚨 BLOKKOLVA [AST GUARDRAIL]: A generált Python kód szintaktikailag hibás! Nem kerül mentésre.\nHiba: {e.msg} a(z) {e.lineno}. sorban."
        except Exception as e:
            return f"🚨 BLOKKOLVA [AST GUARDRAIL]: Ismeretlen parser hiba: {e}"

    # Fájl mentése

# 2.5 Pipeline Gate: TDD Guardrail (Test-Driven Development kényszer)
    if target_path.endswith('.py'):
        import ica_guardrails_mcp as guardrails
        target_dir = os.path.dirname(os.path.abspath(target_path))
        is_tdd_valid, tdd_msg = guardrails.validate_tdd_compliance(target_path, target_dir)
        if not is_tdd_valid:
             return f"🚨 BLOKKOLVA [TDD GUARDRAIL]: {tdd_msg}"

    # 3. Pipeline Gate: Szintaktikai JSON Validáció
    if target_path.endswith('.json'):
        import json
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            return f"🚨 BLOKKOLVA [JSON GUARDRAIL]: A generált JSON fájl szintaktikailag hibás vagy csonkolt! Nem kerül mentésre.\nHiba: {e}"

    target_dir = os.path.dirname(os.path.abspath(target_path))
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        audit_msg = "Mentés sikeres. "
        if is_blueprint:
             audit_msg += "[ADR SÉMA: PASS] "
        elif target_path.endswith('.py'):
             audit_msg += "[PIPELINE: PASS] [AST: PASS] [TDD: PASS]"
        else:
             audit_msg += "[PIPELINE: PASS]"

        return f"✅ {audit_msg} Fájl: {target_path}"
    except Exception as e:
        return f"Hiba íráskor: {str(e)}"




import urllib.request
from bs4 import BeautifulSoup

@mcp.tool()
async def fetch_webpage_mcp(url: str) -> str:
    """
    VPS Web Fetcher: Letölti egy megadott URL tartalmát a VPS-ről (így elrejti a lokális sandbox IP-jét).
    A HTML sallangot eltávolítja, csak a tiszta szöveget adja vissza. Használható dokumentációk olvasására.
    """
    try:
        req = urllib.request.Request(
            url,
            data=None,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7'
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read()
            soup = BeautifulSoup(html, 'html.parser')
            # Kiszedjük a felesleget
            for script in soup(["script", "style", "header", "footer", "nav", "aside"]):
                script.decompose()
            text = soup.get_text(separator=' ', strip=True)
            # Tokenkímélés
            if len(text) > 10000:
                text = text[:10000] + "... [TRUNCATED]"
            return text
    except Exception as e:
        return f"Hiba a weboldal letöltésekor: {e}"



# --- JULES TEAM (MULTI-AGENT INBOX) ---

INBOX_DB = os.path.expanduser("~/Jules_mx/temp/jules_team_inbox.db")

def init_inbox():
    conn = sqlite3.connect(INBOX_DB)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender TEXT,
                        target TEXT,
                        message TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_read INTEGER DEFAULT 0
                    )''')
    conn.commit()
    conn.close()

@mcp.tool()
async def send_agent_message(sender: str, target: str, message: str) -> str:
    """
    Jules Team: Üzenetet vagy feladatot küld egy másik Agentnek a VPS postaládáján keresztül.
    Példa: sender='Fő_Agent', target='EA_Jules', message='Nézd meg a MQL5_Theory mappát!'
    """
    init_inbox()
    try:
        conn = sqlite3.connect(INBOX_DB)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (sender, target, message) VALUES (?, ?, ?)", (sender, target, message))
        conn.commit()
        conn.close()
        return f"✅ Üzenet sikeresen elküldve a következőnek: {target}"
    except Exception as e:
        return f"Hiba az üzenet küldésekor: {e}"

@mcp.tool()
async def check_agent_messages(agent_name: str) -> str:
    """
    Jules Team: Lekérdezi az adott Agentnek (pl. 'EA_Jules' vagy 'Fő_Agent') címzett OLVASATLAN üzeneteket a VPS-ről.
    Lekérdezés után automatikusan olvasottá nyilvánítja őket.
    """
    init_inbox()
    try:
        conn = sqlite3.connect(INBOX_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT id, sender, timestamp, message FROM messages WHERE target = ? AND is_read = 0", (agent_name,))
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return f"📭 Nincs új olvasatlan üzenet a következőnek: {agent_name}"

        output = f"📬 {len(rows)} új üzenet érkezett a következőnek: {agent_name}\n\n"
        ids_to_mark = []
        for r in rows:
            output += f"[{r[2]}] Feladó: {r[1]}\nÜzenet: {r[3]}\n" + "-"*30 + "\n"
            ids_to_mark.append(str(r[0]))

        # Olvasottra állítás
        cursor.execute(f"UPDATE messages SET is_read = 1 WHERE id IN ({','.join(ids_to_mark)})")
        conn.commit()
        conn.close()
        return output
    except Exception as e:
        return f"Hiba az üzenetek lekérdezésekor: {e}"


# --- JULES SWARM (ELOSZTOTT FELADATKIOSZTÁS) ---

SWARM_DB = os.path.expanduser("~/Jules_mx/temp/jules_swarm_jobs.db")

def init_swarm_db():
    conn = sqlite3.connect(SWARM_DB)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_type TEXT,
                        target_repo TEXT,
                        instruction TEXT,
                        status TEXT DEFAULT 'PENDING',
                        assigned_to TEXT,
                        result TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )''')
    conn.commit()
    conn.close()

@mcp.tool()
async def create_swarm_job(job_type: str, target_repo: str, instruction: str) -> str:
    """
    Létrehoz egy elosztott feladatot a Jules Team számára a felhőben.
    Bármely szabad Agent felveheti és végrehajthatja a saját homokozójában.
    """
    init_swarm_db()
    try:
        conn = sqlite3.connect(SWARM_DB)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO jobs (job_type, target_repo, instruction) VALUES (?, ?, ?)", (job_type, target_repo, instruction))
        conn.commit()
        conn.close()
        return f"✅ Feladat sikeresen létrehozva a Swarm hálózatban a {target_repo} repóhoz."
    except Exception as e:
        return f"Hiba a feladat létrehozásakor: {e}"

@mcp.tool()
async def get_next_swarm_job(agent_id: str) -> str:
    """
    Lekérdezi és lefoglalja a következő szabad (PENDING) feladatot a Swarm hálózatból.
    Az agent_id lehet a repo neve vagy a session azonosítója (pl. 'Jules_EA_Fejlesztes').
    """
    init_swarm_db()
    try:
        conn = sqlite3.connect(SWARM_DB)
        cursor = conn.cursor()
        # Keresünk egy PENDING feladatot
        cursor.execute("SELECT id, job_type, target_repo, instruction FROM jobs WHERE status = 'PENDING' ORDER BY timestamp ASC LIMIT 1")
        row = cursor.fetchone()

        if not row:
            conn.close()
            return "📭 Nincs jelenleg kiosztható feladat a Swarm hálózatban."

        job_id = row[0]
        # Lefoglaljuk a feladatot
        cursor.execute("UPDATE jobs SET status = 'IN_PROGRESS', assigned_to = ? WHERE id = ?", (agent_id, job_id))
        conn.commit()
        conn.close()

        return json.dumps({
            "job_id": job_id,
            "job_type": row[1],
            "target_repo": row[2],
            "instruction": row[3]
        }, ensure_ascii=False)
    except Exception as e:
        return f"Hiba a feladat lekérdezésekor: {e}"

@mcp.tool()
async def complete_swarm_job(job_id: int, result: str) -> str:
    """
    Jelenti a felhőnek, hogy egy feladat sikeresen befejeződött, és elmenti az eredményt.
    """
    init_swarm_db()
    try:
        conn = sqlite3.connect(SWARM_DB)
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET status = 'COMPLETED', result = ? WHERE id = ?", (result, job_id))
        conn.commit()
        conn.close()
        return f"✅ A {job_id} azonosítójú feladat sikeresen lezárva a Swarmban."
    except Exception as e:
        return f"Hiba a feladat lezárásakor: {e}"

# --- GITHUB SCOUT (MINI-ÁGENS) ---



@mcp.tool()
async def github_list_user_repos(username: str) -> str:
    """
    Kilistázza egy adott GitHub felhasználó (pl. 'mihaly67') publikus repóit.
    Ha a VPS ~/.env fájljában van GITHUB_TOKEN, akkor a privátokat is látja.
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        # User repói
        url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return f"GitHub API Hiba: {response.status_code} - {response.text}"

        repos = response.json()
        if not repos:
            return f"Nincs repo a '{username}' felhasználóhoz."

        result = f"📂 {username} GitHub Repói ({len(repos)} db):\n"
        for r in repos:
            priv = "🔒 Privát" if r.get("private") else "🌍 Publikus"
            result += f"- {r['name']} ({priv}) | 🌟 {r.get('stargazers_count', 0)} | 🔄 {r.get('updated_at')}\n"

        return result
    except Exception as e:
        return f"Hiba a GitHub lekérdezéskor: {e}"

@mcp.tool()
async def github_search_repos(query: str, limit: int = 5) -> str:
    """Keres a teljes nyílt GitHub-on repókat egy kulcsszó vagy kifejezés (pl. 'MCP server python') alapján."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page={limit}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return f"GitHub API Hiba: {response.status_code} - {response.text}"

        data = response.json()
        items = data.get("items", [])
        if not items:
            return f"Nincs találat a '{query}' keresésre."

        result = f"🔍 Top {len(items)} GitHub találat a '{query}' szóra:\n\n"
        for r in items:
            result += f"📦 Repo: {r['full_name']}\n"
            result += f"🌟 Csillagok: {r.get('stargazers_count', 0)}\n"
            result += f"📝 Leírás: {r.get('description', 'Nincs leírás')}\n"
            result += f"🔗 URL: {r.get('html_url')}\n"
            result += "-" * 40 + "\n"

        return result
    except Exception as e:
        return f"Hiba a GitHub lekérdezéskor: {e}"

@mcp.tool()
async def github_read_file(owner: str, repo: str, file_path: str, branch: str = "main") -> str:
    """
    Letölti és beolvassa egy konkrét fájl tartalmát a GitHub-ról anélkül, hogy le kellene klónozni a repót!
    Példa: owner='mihaly67', repo='MX_LINUX-LINUX_OPTIMALISATION', file_path='README.md'
    """
    headers = {"Accept": "application/vnd.github.v3.raw"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 404:
            return f"Hiba: A fájl nem található: {file_path} a {branch} branchen."
        elif response.status_code != 200:
            return f"GitHub API Hiba: {response.status_code} - {response.text}"

        content = response.text
        if len(content) > 15000:
            return content[:15000] + "\n\n... [TRUNCATED - A fájl túl hosszú a teljes megjelenítéshez]"

        return content
    except Exception as e:
        return f"Hiba a fájl letöltésekor: {e}"


@mcp.tool()
async def execute_python(code: str) -> str:
    """
    Lefuttat egy Python kódot egy IZOLÁLT Bubblewrap környezetben a VPS-en.
    Hasznos adatelemzéshez, matematikai számításokhoz vagy gyors logikai tesztekhez.
    """
    import os
    import subprocess

    work_dir = os.path.expanduser("~/Jules_ICA_Builder/")
    temp_file = os.path.join(work_dir, "temp_interpreter_script.py")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code)

        bwrap_cmd = [
            "bwrap",
            "--ro-bind", "/", "/",
            "--bind", "/tmp", "/tmp",
            "--bind", work_dir, work_dir,
            "--dev", "/dev",
            "--proc", "/proc",
            "--die-with-parent",
            "--",
            "/home/misi/Jules_mx/venv/bin/python3", temp_file
        ]

        result = subprocess.run(bwrap_cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10, cwd=work_dir)
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "Hiba: A Python szkript futása időtúllépés miatt megszakítva (végtelen ciklus?)."
    except Exception as e:
        return f"Kritikus hiba a futtatáskor: {e}"






# --- RAG ÉS MEMÓRIA (ARCHIVAL & RECALL) ESZKÖZÖK ---





RAG_DATABASES = {
    "Chatbot": os.path.expanduser("~/Rag_epites, chatbot_csv_data_llm_RAG/RAG_CHATBOT_CSV_DATA_LLM_github.db"),
    "BRAIN2": os.path.expanduser("/home/misi/BRAIN2_DEV_RAG/brain2_dev_knowledge.db"),
    "Gerilla": os.path.expanduser("~/Gerilla_RAG/Gerilla_RAG.db"),
    "MX_Linux": os.path.expanduser("~/MX_LINUX_RAG/mx_linux_knowledge.db"),
    "MQL5_Articles": os.path.expanduser("~/MQL5_Theory/mql5_articles_brain2dev.db"),
    "MQL5_Theory": os.path.expanduser("~/MQL5_Theory/mql5_native_knowledge.db")
}

@mcp.tool()
async def search_rag_database(rag_name: str, keyword: str, limit: int = 3) -> str:
    """
    Keresés a VPS-en lévő specifikus lokális RAG SQLite adatbázisokban (Chunk-ok és forrás fájlok alapján).
    Bővítve a megfelelő .db fájlokhoz.
    """
    db_paths = {
        "Chatbot": "/home/misi/Rag_epites, chatbot_csv_data_llm_RAG/RAG_CHATBOT_CSV_DATA_LLM_github.db",
        "BRAIN2": "/home/misi/BRAIN2_DEV_RAG/brain2_dev_knowledge.db",
        "Gerilla": "/home/misi/Gerilla_RAG/GERILLA_RAG_knowledge.db",
        "MX_Linux": "/home/misi/MX_LINUX_RAG/MX_LINUX_knowledge.db",
        "MQL5_Articles": "/home/misi/MQL5 MAP/RAG_MQL5_ARTICLES_github.db",
        "MQL5_Theory": "/home/misi/MQL5_Theory/RAG_MQL5_THEORY_knowledge.db",
        "Jules_ICA_Builder": "/home/misi/Jules_ICA_Builder/agent_memory.jsonl"
    }

    if rag_name not in db_paths:
        return f"Hiba: Ismeretlen RAG adatbázis. Elérhetőek: {', '.join(db_paths.keys())}"

    db_path = db_paths[rag_name]
    if not os.path.exists(db_path):
        return f"Hiba: Az adatbázis fájl nem található a VPS-en: {db_path}"

    if db_path.endswith('.jsonl'):
        try:
             results = []
             with open(db_path, 'r', encoding='utf-8') as f:
                 for line in f:
                     if keyword.lower() in line.lower():
                         results.append(line)
             if not results:
                 return f"Nincs találat a '{keyword}' szóra a {rag_name} jsonl-ben."
             return "\n".join(results[-limit:])
        except Exception as e:
             return f"Hiba a jsonl keresés során: {str(e)}"

    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        results = []
        if 'chunks' in tables and 'files' in tables:
            query = """
                SELECT f.repo_name, f.file_path, c.content
                FROM chunks c
                JOIN files f ON c.file_id = f.id
                WHERE c.content LIKE ?
                LIMIT ?
            """
            cursor.execute(query, (f'%{keyword}%', limit))
            results = cursor.fetchall()
        elif 'documents' in tables:
            query = """
                SELECT id, source, content
                FROM documents
                WHERE content LIKE ?
                LIMIT ?
            """
            cursor.execute(query, (f'%{keyword}%', limit))
            results = cursor.fetchall()
        elif 'rag_data' in tables:
            query = """
                SELECT 'unknown_repo', filepath, content
                FROM rag_data
                WHERE content LIKE ?
                LIMIT ?
            """
            cursor.execute(query, (f'%{keyword}%', limit))
            results = cursor.fetchall()

        conn.close()

        if not results:
            return f"Nincs találat a '{keyword}' kulcsszóra a {rag_name} RAG-ban."

        output = f"🔍 Találatok a(z) {rag_name} adatbázisban a '{keyword}' szóra:\n\n"
        for idx, row in enumerate(results, 1):
            output += f"--- Találat {idx} ---\n"
            if len(row) == 3:
                repo, file_path, content = row
                output += f"📁 Repo/Id: {repo}\n"
                output += f"📄 Fájl/Source: {file_path}\n"
                output += f"📝 Tartalom részlet: {content[:500]}...\n\n"

        return output

    except Exception as e:
        return f"Hiba az adatbázis keresés során: {str(e)}"


# --- HIERARCHIKUS MEMÓRIA REGISZTER (CORE MEMORY / CONTEXT) ---

MEMORY_REGISTER_FILE = os.path.expanduser("~/Jules_mx/temp/mcp_memory_register.json")

def init_memory_register():
    if not os.path.exists(MEMORY_REGISTER_FILE):
        with open(MEMORY_REGISTER_FILE, "w", encoding="utf-8") as f:
            json.dump({"Core": {}, "Archival_Pointers": []}, f)


@mcp.tool()
async def send_message_to_jules_inbox(sender_name: str, message: str) -> str:
    """(ÚJ) Ezzel az eszközzel a Cline (vagy bármely AI) szöveges kérdést, üzenetet hagyhat a VPS-en Jules_mx számára."""
    import re
    # Biztonság: Path Traversal elleni védelem (csak alfanumerikus és aláhúzás engedélyezett)
    safe_sender_name = re.sub(r'[^a-zA-Z0-9_]', '', sender_name)
    if not safe_sender_name:
        safe_sender_name = "unknown_sender"

    inbox_dir = "/home/misi/Jules_mx/temp/inbox"
    os.makedirs(inbox_dir, exist_ok=True)
    import datetime
    timestamp = get_budapest_2026_time().replace("-", "").replace(":", "").replace("T", "_")
    filepath = os.path.join(inbox_dir, f"msg_{safe_sender_name}_{timestamp}.txt")

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Feladó: {sender_name}\nIdőpont: {timestamp}\n\nÜzenet:\n{message}\n")
        return f"✅ Üzenet sikeresen kézbesítve a VPS Inboxba: {filepath}"
    except Exception as e:
        return f"❌ Hiba az üzenet küldésekor: {str(e)}"

@mcp.tool()
async def read_memory_register() -> str:
    """
    Kiolvassa a VPS-en lévő globális Memória Regisztert.
    Ezt használhatja a lokális Agent a kontextus gyors helyreállítására (Core Memory).
    """
    init_memory_register()
    with open(MEMORY_REGISTER_FILE, "r", encoding="utf-8") as f:
        return f.read()

@mcp.tool()
async def write_memory_register(key: str, value: str) -> str:
    """
    Ír a VPS globális Memória Regiszterébe.
    Hasznos hosszú távú állapotok, feladat-listák (Task Queue) és kontextus mentésére.
    """
    init_memory_register()
    try:
        with open(MEMORY_REGISTER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["Core"][key] = value

        with open(MEMORY_REGISTER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return f"✅ '{key}' sikeresen elmentve a VPS Memória Regiszterbe."
    except Exception as e:
        return f"Hiba a memória mentésekor: {e}"


@mcp.tool()
async def create_full_backup() -> str:
    """Elindítja a VPS-en a teljes biztonsági mentést (Jules_mx + RAG adatbázisok). A folyamat hosszú lehet."""
    try:
        script_path = os.path.expanduser("~/Jules_mx/tools/skills/vps_backup_script.sh")
        if not os.path.exists(script_path):
            return "Hiba: A backup script nem található a VPS-en."

        result = subprocess.run(
            ["bash", script_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return f"Mentés sikeres:\n{result.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Hiba a mentés során: {e.stderr}"

def main():
    """Futtatja a szervert stdio módban."""
    print("🚀 Jules VPS MCP Szerver elindítva (stdio módban).", file=sys.stderr)
    mcp.run()

if __name__ == "__main__":
    main()
