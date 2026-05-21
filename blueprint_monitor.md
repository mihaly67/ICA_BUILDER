## Context
A felhasználó (Jules ICA fejlesztő) arra kért, hogy tervezzünk meg egy "Rendszermonitor" Dashboardot az ICA-hoz, amellyel vizuálisan követhető a memória (jsonl), az ügynökök közti ütközések, a MCP tool-hívások, és a System 2 gráf terheltsége. A feladathoz integráltuk az Agent Observability RAG anyagokat (RagaAI, trace-wave, mem0-aio).

## Decision
Egy könnyűsúlyú, lokális TUI / Web GUI hibridet fogunk építeni (a trace-wave és a mem0-aio mintájára), ami 3 fő réteget monitoroz:
1. **Memória Stream View**: Folyamatosan frissülő nézet az `agent_memory.jsonl` és az INBOX mappák alapján. Így a fejlesztő láthatja a mentett Context_Summary-ket.
2. **MCP / Token Telemetria**: A VPS MCP router (`ica_mcp_router.py`) logjainak, timeoutjainak és terheltségének figyelése (hasonlóan a RagaAI Catalyst LLM observability funkcióihoz).
3. **MCTS Gráf Nézet**: Az újonnan beépített System 2 Foresight (MCTS Planner) gondolkodási fájának és a generált node-oknak az interaktív megjelenítése.

## Consequences
- A rendszer kap egy átlátható felületet, ami nagyban megkönnyíti a hibakeresést és a "System 2" gráf monitorozását.
- Lokális fájl-olvasáson és SSH pollingon (vagy MCP bridge-en) keresztül fog működni, így nem terheli feleslegesen a VPS-t daemonokkal.
- Gyorsabban felfedezhetőek a resource-timeout problémák és INBOX szinkronizációs hibák.

## Status
Proposed.
