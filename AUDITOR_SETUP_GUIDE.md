# 🕵️‍♂️ JULES ICA: AUDITOR SETUP & WORKFLOW GUIDE

Ez a dokumentum azt írja le, hogyan épül fel és hogyan használható a Zero Trust architektúra **Auditor (Ellenőrző)** része.
Ahogy a Manifestóban leírtuk: A kódolónak (Builder) és az ellenőrnek (Auditor) külön útvonalon, külön jogkörökkel kell dolgoznia.

---

## 1. A Rendszer Működési Elve (Hogyan védi az adatokat?)

1. **A Builder MCP (Port 8000 körül)**: Ezt használom én (Jules), amikor kódolok, bash parancsokat futtatok, vagy a memóriát írom a lokális Sandboxból a VPS felé.
2. **Az Auditor MCP (Port 8181)**: Ez egy vadonatúj, **kizárólag olvasásra (Read-Only)** jogosult MCP szerver. Csak a "Fekete Doboz" logokat (telemetria, memory, error logok) hajlandó kiadni, szigorú "Whitelist" alapon. Nem tud fájlt módosítani, sem kódot futtatni. Ezen a csatornán semmilyen "Path Traversal" (adatszivárgási kísérlet a szerver fájlrendszerében) nem lehetséges.

---

## 2. A TE TEENDŐID (Felhasználó / Misi)

Ahhoz, hogy az Auditor LLM-et (pl. egy másik lokális Claude / ChatGPT vagy Jules instance) biztonságosan ráköthesd a VPS-re, a következőket kell tenned:

### Lépés 1: Az SSH Tunnel felépítése az Auditor számára
Az Auditor MCP szerver a VPS-en szigorúan csak a `127.0.0.1` (localhost) címen hallgat, a nyílt internetről nem elérhető. Ezt a portot át kell húznod a te lokális (MX Linux) gépedre.

Nyiss egy új terminált a lokális gépeden, és futtasd ezt (a jelszómentes SSH kulcsod miatt ez simán futni fog a háttérben):
```bash
ssh -N -L 8181:127.0.0.1:8181 misi@5.189.163.88
```
*(Ezt akár be is teheted egy kis `start_auditor_tunnel.sh` szkriptbe az asztalodra.)*

### Lépés 2: Az Auditor LLM Csatlakoztatása
Most, hogy a port át van húzva, nyisd meg az általad használt Auditor felületet (pl. egy új Claude Desktop alkalmazást, Cline-t, vagy egy másik Jules terminált), és add hozzá a lokális `8181`-es portot mint MCP szervert (pl. `http://localhost:8181/sse` SSE kliensként, vagy ahogy a kliensed kéri).

Az Auditor LLM ezen a porton keresztül be tudja kérni az objektív telemetriát (`mcp_telemetry.db`), a szubjektív naplót (`agent_memory.jsonl`) és az error logokat, hogy elvégezze a **Diszkrepancia Vadászatot**, de semmilyen kárt nem tud tenni a rendszerben.

---

## 3. AZ ÉN TEENDŐIM (Jules / Agent) - Következő Lépések

Amint jóváhagyod ezt a tervet, a következő kódolási körben ezeket fogom elkészíteni a lokális Sandboxban:

1. **`src/tools/skills/auditor_mcp_server.py` megírása:**
   - Fejlesztek egy dedikált FastMCP szervert.
   - Eszközök: `read_blackbox_log(log_name)` és `query_readonly_db(query)`.
   - Implementálom a Path Traversal védelmet és a read-only szigorítást.

2. **A Deploy szkript (`deploy_to_vps.sh`) kiegészítése:**
   - Hozzáadok egy harmadik Systemd Service-t (`ica-auditor.service`).
   - Gondoskodom róla, hogy az `rsync` és a `systemctl restart` ezt a modult is zökkenőmentesen felvigye a VPS-re.

*Értettem a feladatot, és a Zero Trust architektúra teljes befejezéséhez ez az Auditor végpont a legfontosabb láncszem.*
