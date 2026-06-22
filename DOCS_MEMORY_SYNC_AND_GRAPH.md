# ICA Memory Synchronization & Knowledge Graph Architecture

Ez a dokumentum azt a "System 2" kognitív perzisztencia modellt írja le, amely lehetővé teszi, hogy az ICA (Intelligent Cognitive Agent) lokális sandboxban keletkező memóriái (`agent_memory.jsonl`) automatikusan felszinkronizálásra kerüljenek a VPS szerverre, és ott egy relációs Tudásgráffá (Knowledge Graph) épüljenek.

## Architektúra Elemei

### 1. Helyi Memória Szinkronizáló (`tools/sync_memory_to_vps.py`)
- **Célja:** A lokális `Knowledge_Base/agent_memory.jsonl` rendszeres, megszakítás nélküli tükrözése a központi VPS-re.
- **Működés:** `apscheduler` segítségével 5 percenként lefut.
- **Zero Trust Megoldás:** A szinkronizáció idejére (és kizárólag arra a pillanatra) ideiglenesen feloldja a `chattr +a` (append-only) védelmet az `rsync` parancs előtt, majd azonnal visszazárja. A biztonság érdekében a hitelesítő adatok jelszó/kulcs nem forráskódban tárolt, hanem környezeti változóból (`SSH_PASS` vagy SSH Key) injektáltak.

### 2. VPS Gráf Építő Szerviz (`tools/graph_builder_service.py`)
- **Célja:** A felmásolt JSONL naplófájlt (Stream) feldolgozása, és a releváns tudáselemek beemelése egy D3.js által renderelhető struktúrába.
- **Működés:** Rendszerszintű Systemd service-ként (`ica-graph-builder.service`) fut a VPS-en a háttérben. 10 percenként végigolvassa a `jsonl` fájlt.
- **Gráf logika:**
  - Kiszűri a kulcsfontosságú kognitív mérföldköveket (`Architecture_Decision`, `Reflection`, `Context_Summary`, `Session_Handoff`).
  - Létrehoz számukra egy-egy Node-ot (csomópontot) az `entities` táblában (SQLite).
  - Létrehoz egy `followed_by` (vagy ahhoz hasonló) Edge-et (vonalat) az `edges` táblában, kronológiai sorrendben összekötve a memóriákat.

## Más Repozitóriumokban / Domainekben (RAG) Való Használat

A Tudásgráfot más, domain-specifikus repóknál (pl. Videó Letöltő, EA Kereskedő Robot, MX Linux Fejlesztő) is lehet és érdemes használni.

**Van-e értelme?** Igen. A Tudásgráf elkülönítése az MCTS keresési fától (ami egy ideiglenes hipotézis-terület) pontosan azt szolgálja, hogy a véglegesített építészeti döntések hosszú távon is lekérdezhetők maradjanak, vizuálisan követve a logika alakulását.

### Implementációs útmutató új repókhoz:

1. **Szeparáció biztosítása:** A különböző repókból érkező memóriákat el kell választani egymástól a Tudásgráfban, különben "összemosódik" az AI kontextusa (hallucinációhoz vezet).
   - A memóriák generálásakor a `jsonl` struktúrába (vagy a node nevébe) egy **domain tag-et** kell szúrni. Pl.: `name = f"repo:video_dl_{timestamp}_{keywords}"`.
   - A Web Monitor felület így képes lesz RAG alapján szűrni és csak az aktuális projekt node-jait megjeleníteni.

2. **Szolgáltatások újrahasznosítása:**
   - A `graph_builder_service.py` **központilag** fut a VPS-en (a `Jules_ICA_Builder` mappában lévő DB-re mutatva). Új repó esetén nem kell új Gráf Építőt írni.
   - Elegendő csak a helyi lokális `sync_memory_to_vps.py` másolatát (és testreszabását) futtatni az új repó környezetében, ami ugyanabba a központi `/home/misi/Jules_ICA_Builder/Knowledge_Base/` könyvtárba, vagy egy dedikált alegységbe szinkronizál (pl. `agent_memory_video_dl.jsonl`), amit a Gráf Építő kiegészítve olvas.

3. **Központosított SQLite vs Dedikált SQLite:**
   - A jelenlegi ICA modellben a `ica_knowledge_graph.db` a központi agy.
   - Minden új repó kliensnek ehhez a központi adatbázishoz kell node-okat / edge-eket csatolnia, megfelelő prefixekkel ("repo_name"), hogy az ICA Web Monitor egységesen tudja a teljes rendszer egészségét és tudását vizualizálni a lenyíló RAG választó gomb segítségével.
