## Context
A felhasználó (Jules ICA fejlesztő) arra kért, hogy toljam ki a kognitív képességek határát ("far beyond"), behozva a gépies, előrelátó tervezést (System 2, Foresight, Tree of Thoughts) a rendszerünkbe, a VPS hardverkorlátjainak figyelembevételével. A RAG-ban lévő és frissen integrált (agentic-os-core, CRSM, yggdrasil-mcp) repók alapján az MCP-n keresztüli aszinkron MCTS (Monte Carlo Tree Search) gráf-tervezés a legjobb irány.

## Decision
Integráljuk a Monte Carlo Tree Search (MCTS) és a Tree-of-Thoughts (ToT) logikát a meglévő Gráf Memóriánkba (`ica_knowledge_graph.db`).
1. Készítünk egy új `ica_mcts_planner.py` modult, amely a feladatokat csomópontokként (Node) reprezentálja a memóriagráfban.
2. A tervezés fázisában az LLM generál 3 alternatív utat (Generator).
3. Egy belső (akár olcsó VPS Llama) Evaluator pontozza az utakat (Simulation).
4. Az MCP `ica_mcp_router.py`-t kibővítjük a `deep_planning` és `evaluate_thought` eszközökkel (az Yggdrasil-mcp mintájára).
5. Ez egy "Offline" System 2 gondolkodást tesz lehetővé: a tényleges cselekvések előtt az agent a fejében/memóriájában futtatja a lehetséges jövőbeli következményeket (Foresight).

## Consequences
- A memóriagráf mérete és komplexitása növekedni fog az ideiglenes "Thought" csomópontok miatt.
- Megnő a tervezési fázis válaszideje (latency trade-off), de sokkal stabilabb, tévedésmentesebb (hallucináció-mentes) lesz a végső kódgenerálás.
- Minimalizáljuk az API költségeket azzal, hogy az Evaluator részlegesen átirányítható a lokális VPS Llama modellekre.

## Status
Proposed.
