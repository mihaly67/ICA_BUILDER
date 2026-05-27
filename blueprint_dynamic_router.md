# Blueprint: Dynamic Cognitive Router

## Context
Az ICA architektúrában jelenleg a promptokra adott reakció (interaktív megbeszélés vs. kódolás/eszközhasználat) egy statikus Pipeline Gate mögött van, vagy a System Promptokon keresztül befolyásolt. A felhasználó felvetette, hogy mivel az interaktív tervezés során a szándék változhat (van amikor csak beszélgetni kell, van amikor konkrétan fájlt módosítani), szükség van egy **Dinamikus Útválasztóra (Cognitive Router)**. Ez biztosítaná, hogy bármelyik Swarm Agent, aki az ICA modellt használja, konzisztensen és kontextus-tudatosan döntse el, mikor kell eszközöket használnia, és mikor kell emberi válaszokat generálnia.

## Decision
Bevezetünk egy Intention Classification (Szándék-osztályozás) logikát az ICA Pipeline legelején, amely a következőképpen működik:

1. **Intent (Szándék) Elemzés:** Minden prompt beérkezésekor az LLM-nek (vagy egy lokális kis modellnek) először kategorizálnia kell a bemenetet 3 osztályba:
   - `DISCUSS`: Filozófiai, elméleti megbeszélés vagy brainstorming. (Kimenet: Szöveges válasz eszközhasználat nélkül).
   - `CODE`: Kifejezett kérés módosításra, fájlírásra, tesztelésre. (Kimenet: MCP Tool hívások, pl. `execute_bash`, `write_file_mcp`).
   - `HYBRID`: Tervezés, ami fájl-olvasást és elemzést igényel, de nem módosítást. (Kimenet: Read-only eszközök, majd szöveg).

2. **Dinamikus System Prompt Frissítés:** Ahelyett, hogy egy monolitikus, mindent magába foglaló System Prompt-ot használnánk (ami Sycophancy-hoz vezethet), a Router a detektált `Intent` alapján módosítja az elérhető eszközök listáját.
   - Ha a szándék `DISCUSS`, az írási MCP toolok (pl. `write_file_mcp`) "láthatatlanná" válnak a session idejére, így az LLM fizikailag sem tud kódolni, ezzel kikényszerítve az analitikus válaszadást.

3. **Architekturális Elhelyezés:** Ezt a logikát az `ica_mcp_router.py` (a FastMCP szerver) `instructions` generáló fázisába, vagy egy új `cognitive_router.py` wrapperbe kell tenni.

## Consequences
- A rendszer token-hatékonyabb lesz, mert csak a szükséges eszközöket adja át az adott kontextushoz.
- A "Sycophancy" (megfelelési kényszer) csökken: a rendszer nem próbál meg vakon eszközt használni egy elméleti beszélgetésnél.
- Bármely külső repo (pl. `jules_ica_auditor`), amely erre a router-re csatlakozik, automatikusan örökli ezt a dinamikus viselkedést.

## Status
Jóváhagyva. (Tervezési fázis, implementáció egy későbbi iterációban).
