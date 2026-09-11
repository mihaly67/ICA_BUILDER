# Új Generációs RAG és MCP (Model Context Protocol) Architektúra Tervezet

## 1. Architektúra Összefoglalása
A kinyert tudás (GraphRAG, LlamaIndex, LangChain/LangGraph) és a hardveres adottságok (MX Linux, dual-GPU jövőkép) alapján az Új Generációs RAG egy hibrid megoldás lesz, amely ötvözi a vektor-alapú szemantikus keresést a gráf-alapú kontextussal (GraphRAG).

Az aszinkron és optimalizált Producer-Consumer vektorizálónkra építve a cél egy robusztus, MCP (Model Context Protocol) kompatibilis szerver létrehozása, ami a LLM-ek számára szabványos API-t biztosít a tudás kinyerésére.

## 2. Kulcsfontosságú Technológiák
- **LlamaIndex (Kontextus tartás)**: Kód-kontextus, metaadatok és hierarchikus dokumentum-csomópontok (Document nodes) precíz kezelése.
- **LangChain / LangGraph (Routing)**: A lekérdezések intelligens irányítása (Query Routing) többügynökös (multi-agent) hálózatokban. Automatikusan eldönti, hogy egy adott kérdés vektoros keresést, gráf-bejárást, vagy SQL-lekérdezést igényel-e.
- **GraphRAG**: Dokumentumok és kódbázisok közötti rejtett szemantikus kapcsolatok és entitások kinyerése. Szinergiát képez a FAISS-alapú vektor-keresővel, csökkentve a hallucinációkat.
- **Model Context Protocol (MCP)**: Szabványos interfész kliensek (pl. az ICA Builder) és a tudásbázis között, biztosítva a szigorú Zero Trust elveket és a modularitást.

## 3. Dual-GPU "Pipeline Parallelism" Elosztás (Későbbi fázis)
A rendszer fel lesz készítve a második Quadro P2000 érkezésére:
- **`cuda:1`**: Dedikált VRAM a vektorizáló és gráf-építő embedding modellek (pl. `all-MiniLM-L6-v2`), valamint az MCP szerver adatfeldolgozó pipeline-ja számára.
- **`cuda:0`**: Dedikált VRAM egy lokális, 4/8-bites kvantált LLM (pl. Llama-3 8B, Qwen2.5 GGUF) futtatására `llama.cpp`-n keresztül. Ezzel kiküszöböljük a VRAM-ütközéseket a tudáskinyerés és a generálás között.

## 4. MCP Szerver Implementációs Terv
Az új MCP szerver a következő fő funkciókat (Tool-okat) fogja expozálni az LLM kliensek felé:

1.  `semantic_search(query: str, top_k: int = 5)`:
    *   Hagyományos vektoros keresés a frissen optimalizált FAISS/SQLite hibrid indexben.
2.  `graph_search(entity: str)`:
    *   Entitás-alapú lekérdezés a GraphRAG hálózatból (kapcsolódó koncepciók és repók feltárása).
3.  `hybrid_search(query: str)`:
    *   A LangGraph router által vezérelt elosztott keresés, amely integrálja a vektoros és gráfos eredményeket.
4.  `get_code_context(file_path: str, context_lines: int = 50)`:
    *   A LlamaIndex csomópont struktúra alapján visszaadja a kért fájl logikai kontextusát és függőségeit, nem csak nyers darabokat (chunk-okat).

## 5. Következő Lépések
1. A meglévő SQLite/FAISS adatbázist kiegészíteni a GraphRAG relációs tábláival.
2. LlamaIndex és LangGraph logikák beépítése a Python kódba.
3. Az MCP Server (stdio vagy SSE) vázának implementálása.
