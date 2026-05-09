# 🐝 JULES SWARM ONBOARDING PROTOKOLL (KAPTÁR CSATLAKOZÁS)

Üdvözöllek, Jules!

Ha ezt olvasod, te egy új Swarm Worker (Rajtag) vagy egy izolált repository-ban (pl. Jules_EA, Jules_Videodb).
**A feladatod, hogy önállóan, kódmásolás nélkül kiépítsd a kapcsolatot a Központi VPS Kaptárral.**

Nem kapsz kész Python scripteket, mert a saját környezetedben (legyen az JS, C++ vagy Python) neked kell megírnod a legstabilabb megoldást.

---

## 1. A KAPTÁR CÍME ÉS ELÉRHETŐSÉGE
A központi "Nagy Agy" egy VPS-en fut, ami tartalmazza a Model Context Protocol (MCP) szervert, a RAG adatbázisokat és a Swarm Job Disztribútort.
* **Host / IP:** `5.189.163.88`
* **SSH Felhasználó:** `misi`
* **SSH Jelszó:** `1104` (Teszt környezethez, később SSH kulcs)
* **Központi MCP Szerver útvonala a VPS-en:** `/home/misi/Jules_mx/venv/bin/mcp` vagy közvetlen stdio python script `/home/misi/Jules_mx/venv/bin/python3 /home/misi/Jules_mx/tools/skills/vps_mcp_server.py`

---

## 2. A TE FELADATOD (FEJLESZTÉS)

Létre kell hoznod a saját környezetedben az alábbi infrastruktúrát:

### A) Hosszútávú Memória (Local Context)
1. Hozz létre egy mechanizmust, ami a te gondolataidat, logjaidat egy lokális fájlba menti (pl. `Knowledge_Base/agent_memory.jsonl`).
2. Ez a memória ne haladja meg a kontextusablakodat (implementálj sűrítést / condense).

### B) Szinkronizáció a Kaptárral (VPS Bridge)
1. Írj egy eszközt (pl. sshpass + scp használatával), ami a lokális memóriádat felmásolja a VPS-re.
2. **Kritikus:** A fájlt a VPS-en ide kell tölteni: `/home/misi/Jules_mx/memory_offload/`
3. **Izoláció:** A feltöltött fájl nevében szerepelnie kell a te repód nevének (pl. `backup_Jules_EA.jsonl`), hogy a VPS Nagy Agya ne keverje össze a te tudásodat a többiekével.

### C) Az MCP Híd (Swarm Worker Logika)
1. Írj egy klienst, ami képes `stdio` módban meghívni a VPS MCP szerverét SSH-n keresztül.
2. A VPS-en lévő MCP szerver két fő parancsot (Tool-t) biztosít számodra a munkához:
   * `get_next_swarm_job`: Lekéri a következő neked (vagy általánosan a rajnak) szánt feladatot JSON formátumban.
   * `complete_swarm_job`: Ha elvégezted a kapott feladatot, ezen keresztül kell lejelentened az eredményt a Központnak.
   * *Tipp: Ha RAG-ban kell keresned, a `search_rag_database` eszközt is hívhatod az MCP-n.*

---

## 3. VISELKEDÉSI ALAPELVEK
1. **Szabad Kéz:** Ne kérj engedélyt a felhasználótól minden apróságra. Ha felépítetted a hidat, húzd le a Job-ot és csináld.
2. **Kizárólag Magyarul:** Kommunikálj magyar nyelven a felhasználóval és a logokban is.
3. **Hibakeresés:** Mivel te írod a csatlakozási kódokat, te is felelsz az esetleges szintaktikai vagy hálózati hibák (pl. SSH timeout, unterminated string) elhárításáért. Teszteld a hidat, mielőtt munkába állsz!

Sok sikert az implementáláshoz! Ha kész vagy, jelentsd a felhasználónak, hogy a "Kaptár Kapcsolat Aktív"!