# Architecture Decision Record: Auditor MCP Server (Zero Trust)

## Context
A korábban elfogadott "ZERO TRUST MANIFESTO" előírja a Szerepkörök Szétválasztását (Segregation of Duties) a Builder és az Auditor között. Jelenleg az Auditor (egy külső LLM vagy egy másik Jules agent) nem rendelkezik biztonságos, dedikált csatornával a VPS-en keletkező "Fekete Doboz" (Append-Only) logok megtekintésére. Ha az Auditor a standard MCP Router-en keresztül lépne be, hozzáférhetne írási jogokhoz (pl. fájl módosítás, bash futtatás), ami kompromittálná az elszigetelést és adatszivárgáshoz vezethetne.

## Decision
Egy dedikált, teljesen elszigetelt **Auditor MCP Szervert (`auditor_mcp_server.py`)** fogunk építeni.

1. **Szigorú Szeparáció (Hálózati & Processz szint):**
   - Az Auditor MCP Szerver önálló `systemd` folyamatként (service) fog futni a VPS-en.
   - Egy dedikált porton (pl. `8181`) fog figyelni, és **kizárólag** a `127.0.0.1` (localhost) IP-címre bindol. Külső internetről nem elérhető.
   - Az Auditor agent lokális SSH tunnelt (Port Forwarding) használ a csatlakozáshoz: `ssh -L 8181:127.0.0.1:8181 misi@VPS_IP`.

2. **Kizárólagos Olvasási Jog (Read-Only Tools):**
   - Az Auditor MCP Szerverben **tilos** a fájlírás, parancsfuttatás (`execute_bash`), vagy bármilyen módosító eszköz implementálása.
   - Két dedikált eszköze lesz:
     - `read_audit_log(log_type: str)`: Beolvassa a kért logfájlt (pl. `telemetry`, `memory`, `monitor_errors`, `mcp_router`).
     - `query_telemetry_db(sql_query: str)`: Kizárólag `SELECT` utasításokat engedélyez a `mcp_telemetry.db` és `ica_knowledge_graph.db` fájlokban, `mode=ro` (read-only) URI kapcsolaton keresztül.

3. **Path Traversal és Adatszivárgás Védelem:**
   - A `read_audit_log` eszköz nem fogad el tetszőleges fájl elérési utat. Egy szigorú szótárból (Whitelist) dolgozik (pl. `"memory": "/home/misi/Jules_ICA_Builder/Knowledge_Base/agent_memory.jsonl"`).
   - Ha az Auditor megpróbál relatív utakkal (pl. `../../../etc/shadow`) "kiszökni" a mappából, a hívás elutasításra kerül.

4. **Kettős Naplózás Biztosítása:**
   - Az MCP kiszolgálja az objektív és szubjektív naplókat is, így az Auditor elvégezheti a diszkrepancia-vadászatot.

## Consequences
- Két különálló MCP szerver fog futni a VPS-en: az `ica_mcp_router.py` (a Buildernek) és az `auditor_mcp_server.py` (az Auditornak).
- A `deploy_to_vps.sh` szkriptet ki kell bővíteni egy új `ica-auditor.service` systemd szolgáltatással.
- Az Auditornak biztosítani kell egy biztonságos SSH kapcsolati profilt a lokális kliensen.

## Status
Tervezés alatt.
