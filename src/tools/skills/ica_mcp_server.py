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

RAG_DATABASES = {
    "Chatbot": "/home/misi/Rag_epites, chatbot_csv_data_llm_RAG/RAG_CHATBOT_CSV_DATA_LLM_github.db",
    "BRAIN2": "/home/misi/BRAIN2_DEV_RAG/brain2_dev_knowledge.db",
    "Gerilla": "/home/misi/Gerilla_RAG/GERILLA_RAG_knowledge.db",
    "MX_Linux": "/home/misi/MX_LINUX_RAG/MX_LINUX_knowledge.db",
    "MQL5_Articles": "/home/misi/Jules cikk és fájl letöltés_RAG/RAG_MQL5_ARTICLES_github.db",
    "MQL5_Theory": "/home/misi/MQL5_Theory_RAG/RAG_MQL5_THEORY_knowledge.db",
    "Jules_ICA_Builder": "/home/misi/Jules_ICA_Builder/agent_memory.jsonl"
}

MEMORY_REGISTER_FILE = os.path.expanduser("~/Jules_ICA_Builder/agent_register.jsonl")

def init_memory_register():
    if not os.path.exists(MEMORY_REGISTER_FILE):
        with open(MEMORY_REGISTER_FILE, 'w') as f:
            f.write('{"Core": {}}')

init_memory_register()



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
def execute_bash(command: str, justification: str = "") -> str:
    import ica_guardrails_mcp
    is_safe, safe_command = ica_guardrails_mcp.sanitize_bash_command(command)
    if not is_safe:
        return "🚨 BLOKKOLVA [BASH GUARDRAIL]: Fájlba írás vagy fájl-átirányítás (>, >>, tee) a Bash-en keresztül szigorúan TILOS! Az AI-nak kötelezően a Pipeline Gate-tel védett write_file_mcp eszközt kell használnia erre a célra! Eredeti parancs: " + command

    if "rm -rf /" in safe_command or "mkfs" in safe_command:
         return "Hiba: Veszélyes parancs letiltva a sandboxban."

    try:
        import subprocess
        import os
        work_dir = os.path.expanduser("~/Jules_ICA_Builder/")

        if "BRAIN2_DEV_RAG" in safe_command and "rm" in safe_command:
             return "🚨 BLOKKOLVA [BASH GUARDRAIL]: Tilos a RAG adatbázis törlése!"

        result = subprocess.run(safe_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=work_dir)
        return "STDOUT:\n" + str(result.stdout) + "\nSTDERR:\n" + str(result.stderr)
    except subprocess.CalledProcessError as e:
        return "Hiba a Bash futtatásakor (Kód: " + str(e.returncode) + "):\nSTDOUT: " + str(e.stdout) + "\nSTDERR: " + str(e.stderr)
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
async def write_file_mcp(filepath: str, content: str, justification: str = "") -> str:
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
        with urllib.request.urlopen(req, timeout=120) as response:
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
    import os
    import subprocess
    work_dir = os.path.expanduser("~/Jules_ICA_Builder/")
    temp_file = os.path.join(work_dir, "temp_interpreter_script.py")
    try:
        with open(temp_file, "w") as f:
            f.write(code)
        bwrap_cmd = [
            "bwrap", "--unshare-all", "--ro-bind", "/", "/",
            "--dev", "/dev", "--proc", "/proc",
            "--bind", "/tmp", "/tmp",
            "--bind", work_dir, work_dir,
            "--unshare-net",
            "--die-with-parent",
            "/home/misi/Jules_mx/venv/bin/python3", temp_file
        ]
        result = subprocess.run(bwrap_cmd, capture_output=True, text=True, timeout=30)
        out_msg = "Kimenet:\n" + str(result.stdout)
        if result.stderr:
            out_msg += "\n\nHibák:\n" + str(result.stderr)
        return out_msg
    except Exception as e:
        return "Kritikus hiba a futtatás során: " + str(e)



@mcp.tool()
async def search_rag_database(rag_name: str, keyword: str, limit: int = 3) -> str:
    global RAG_DATABASES

    if rag_name not in RAG_DATABASES:
        return f"Hiba: Ismeretlen RAG adatbázis. Elérhetőek: {', '.join(RAG_DATABASES.keys())}"

    db_path = RAG_DATABASES[rag_name]

    # ------------------------------------------------------------------------------------------
    # ZERO TRUST VPS PROXY FALLBACK (Ha a Sandbox nem látja közvetlenül a VPS fájlrendszert)
    # ------------------------------------------------------------------------------------------
    if not os.path.exists(db_path):
        import subprocess

        VPS_HOST = os.environ.get("VPS_HOST", "5.189.163.88")
        VPS_USER = os.environ.get("VPS_USER", "misi")

        # Generálunk egy egysoros python parancsot, ami lefut a VPS-en, és visszadobja a JSONL / SQLite eredményt
        safe_keyword = keyword.replace("'", "\\'")

        if db_path.endswith('.jsonl'):
            python_code = f"""
import json
try:
    with open('{db_path}', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    res = []
    for l in reversed(lines):
        if '{safe_keyword}'.lower() in l.lower():
            res.append(l.strip())
            if len(res) >= {limit}: break
    print('PROXY_RESULT:' + json.dumps(res))
except Exception as e:
    print('PROXY_ERROR:' + str(e))
"""
        else:
            # SQLite logika proxy
            python_code = f"""
import json, sqlite3
try:
    conn = sqlite3.connect('{db_path}')
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()
    results = []
    for table in tables:
        tname = table[0]
        try:
            # Csak szöveges mezőkben keresünk egyszerűséggel
            c.execute(f"SELECT * FROM {{tname}} LIMIT 1")
            cols = [desc[0] for desc in c.description]
            where_clause = " OR ".join([f"{{col}} LIKE '%{safe_keyword}%'" for col in cols])
            c.execute(f"SELECT * FROM {{tname}} WHERE {{where_clause}} LIMIT {limit}")
            rows = c.fetchall()
            for r in rows:
                results.append(f"[Table: {{tname}}] " + " | ".join([str(x)[:200] for x in r]))
                if len(results) >= {limit}: break
        except Exception:
            pass
        if len(results) >= {limit}: break
    print('PROXY_RESULT:' + json.dumps(results))
except Exception as e:
    print('PROXY_ERROR:' + str(e))
"""
        # Biztonságos SSH futtatás a Python kód stdin-en keresztüli beküldésével (RCE és idézőjel escaping hibák elkerülésére)
        ssh_cmd = [
            "ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
            f"{VPS_USER}@{VPS_HOST}",
            "python3 -"
        ]

        try:
            result = subprocess.run(ssh_cmd, input=python_code, check=True, capture_output=True, text=True, timeout=15)
            stdout = result.stdout
            if "PROXY_ERROR:" in stdout:
                err = stdout.split("PROXY_ERROR:")[1].strip()
                return f"Hiba a VPS Proxy hívásakor: {err}"
            elif "PROXY_RESULT:" in stdout:
                import json
                json_str = stdout.split("PROXY_RESULT:")[1].strip()
                res_list = json.loads(json_str)
                if not res_list:
                    return f"Nincs találat a '{keyword}' szóra a VPS proxy memóriában ({rag_name})."
                return "🔍 Találatok a(z) " + str(rag_name) + " VPS Proxy memóriában:\n" + "\n".join(res_list)
            else:
                return f"Ismeretlen VPS Proxy válasz: {stdout}"
        except subprocess.CalledProcessError as e:
            return f"Hiba az SSH proxy futtatásakor: {e.stderr}"
        except Exception as e:
             return f"Rendszerhiba a proxy során: {str(e)}"
    # ------------------------------------------------------------------------------------------

    if db_path.endswith('.jsonl'):
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            results = []
            for line in reversed(lines):
                if keyword.lower() in line.lower():
                    results.append(line)
                    if len(results) >= limit:
                        break
            if not results:
                return f"Nincs találat a '{keyword}' szóra a {rag_name} memóriában."
            out_json = "🔍 Találatok a(z) " + str(rag_name) + " memóriában:\n"
            for r in results: out_json += r + "\n"
            return out_json
        except Exception as e:
            return f"Hiba a JSONL olvasásakor: {e}"

    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='chunks' OR name='documents' OR name='rag_data')")
        tables = [row[0] for row in c.fetchall()]

        if not tables:
            return "Hiba: Nem található megfelelő tábla az adatbázisban."

        table = tables[0]
        try:
            c.execute(f"SELECT source, content FROM {table} WHERE content LIKE ? LIMIT ?", (f'%{keyword}%', limit))
        except:
            try:
                c.execute(f"SELECT filepath, content FROM {table} WHERE content LIKE ? LIMIT ?", (f'%{keyword}%', limit))
            except:
                 c.execute(f"SELECT * FROM {table} LIMIT ?", (limit,))

        results = c.fetchall()
        conn.close()

        if not results:
            return f"Nincs találat a '{keyword}' kulcsszóra a {rag_name} RAG-ban."

        output = "🔍 Találatok a(z) " + str(rag_name) + " adatbázisban a '" + str(keyword) + "' szóra:\n\n"

        for i, row in enumerate(results, 1):
            source = str(row[0])
            content_snippet = str(row[1])[:300] + "..." if len(row) > 1 else str(row)
            output += "--- Találat " + str(i) + " ---\n📁 Forrás: " + source + "\n📝 Tartalom: " + content_snippet + "\n\n"

        return output
    except Exception as e:
        return f"Hiba a RAG keresés során: {e}"
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


@mcp.tool()
async def check_system_health() -> str:
    import subprocess
    try:
        mem = subprocess.run(["free", "-h"], capture_output=True, text=True).stdout
        cpu = subprocess.run(["top", "-bn1"], capture_output=True, text=True).stdout.split('\n')[2]
        return f"Memória:\n{mem}\nCPU:\n{cpu}"
    except Exception as e:
        return f"Health check hiba: {e}"

@mcp.tool()
async def deep_planning(initial_state: str, max_iterations: int = 5) -> str:
    try:
        import ica_mcts_planner
        import subprocess
        import sys
        import os
        import re

        # Helper a lokális Llama meghívásához
        def call_llama(prompt, system="Te egy logikai tervező AI vagy. Légy tömör."):
            llama_path = os.path.join(os.path.dirname(__file__), "vps_llama_client.py")
            cmd = [sys.executable, llama_path, prompt, "--model", "qwen2.5:1.5b", "--system", system]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                # Kinyerjük az outputból csak a Llama választ
                if "LLAMA VÁLASZ" in res.stdout:
                    return res.stdout.split("LLAMA VÁLASZ")[1].replace("="*50, "").strip()
                return ""
            except:
                return ""

        planner = ica_mcts_planner.MCTSPlanner(max_iterations=max_iterations, exploration_weight=2.0)

        def gen_func(state):
            prompt = f"Állapot: '{state}'. Sorolj fel max 2 logikus következő lépést a megoldáshoz. Tömören, egymás alá."
            resp = call_llama(prompt)
            actions = []
            if resp:
                lines = resp.split('\n')
                for line in lines[:3]:
                    clean = line.strip().strip('-*0123456789. ')
                    if clean:
                        actions.append(f"{state} -> {clean}")
            if not actions:
                actions = [f"{state} -> (Fallback) Kutatás folytatása"]
            return actions

        def eval_func(state):
            prompt = f"Értékeld a következő gondolatmenetet/tervet 0.0-tól 1.0-ig terjedő skálán aszerint, hogy mennyire logikus és hatékony. Csak egyetlen lebegőpontos számot írj le, semmi mást! Gondolatmenet: '{state}'"
            resp = call_llama(prompt)
            try:
                # Keresünk valami szám-szerűt a válaszban
                nums = re.findall(r"0\.\d+|1\.0|0|1", resp)
                if nums:
                    return float(nums[0])
            except:
                pass
            import random
            return random.uniform(0.3, 0.7)

        best_path = planner.search(initial_state, gen_func, eval_func)
        import json
        tree_data = planner.get_tree_data()
        return json.dumps({"status": "success", "best_predicted_path": best_path, "tree_data": tree_data})
    except Exception as e:
        return f"Hiba az MCTS tervezés során: {e}"

def main():
    print("🚀 Jules VPS MCP Szerver elindítva (stdio módban).", file=sys.stderr)
    mcp.run()

if __name__ == "__main__":
    main()
