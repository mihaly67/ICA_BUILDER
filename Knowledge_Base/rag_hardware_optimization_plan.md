# 🚀 Hardver és AI alapú RAG Vektorizáló Optimalizációs Jelentés

A fizikai gépen elvégzett benchmarkok (Jules, 100.77.191.66) és az AI RAG tanácsai alapján összeállított rendszerterv:

## 1. Hardveres Képességek (A mért valóság)
*   **CPU:** Intel Xeon E5-1620 v3 (4 mag / 8 szál). Erős, de a 8 szál szűk keresztmetszet a JSON parse-olásnál (GIL miatt egy szál 50-80 MB/s).
*   **RAM:** 32GB (26GB szabad). Hatalmas puffer-lehetőség, amit ki is kell használnunk!
*   **GPU:** Quadro P2000 (5GB VRAM). Szűkös memória, ami agresszív VRAM menedzsmentet (garbage collection) követel.
*   **SSD I/O:** Olvasás: ~3.3 GB/s, Írás: ~432 MB/s.
    *   **Konklúzió:** Az SSD brutálisan gyors, a lemezolvasás SOHA nem lesz szűk keresztmetszet. A probléma kizárólag a Python JSON dekódolásánál van.

## 2. Architektúrális Optimalizáció a RAG AI Javaslata alapján

Az AI és a hardvertesztek kombinált válasza egy **több-lépcsős Producer-Consumer (Gyártó-Fogyasztó) architektúrát** követel:

### A) A CPU Bottleneck áthidalása (File Reading)
Mivel az SSD 3.3 GB/s-el tudja adni az adatot, egyetlen "File Reader" szál másodpercek alatt be tudja olvasni a 6-9GB-os JSONL fájlt nyers stringként (vagy byte tömbként mmap segítségével).
*   **Architektúra:** 1 dedikált "Reader" szál olvassa az SSD-t, és egy gigantikus memóriapufferbe (Queue-ba) dobja a NYERS STRING sorokat. A hatalmas (26GB) RAM miatt a Queue mérete nyugodtan lehet akár 50,000-100,000 is.
*   **Producerek (JSON Parserek):** 4-6 darab dedikált "Parser" process (Multiprocessing a GIL elkerülése végett) veszi ki a nyers stringeket a Queue-ból, és kizárólag a `json.loads` dekódolást végzi el rajtuk.

### B) Vektorizálás és GPU Starvation elkerülése
*   **Batch Padding:** A 4-6 Parser process egy másik, kisebb Queue-ba (pl. 200) dobja a már objektummá alakított adatokat.
*   A GPU (Consumer) szál innen szívja le folyamatosan, blokkolás nélkül a feldolgozott adatokat.

### C) Dual GPU Felkészítés (P2000 + P4000)
A RAG AI válaszai megerősítik, hogy a `Ray` vagy a Pytorch `device_map` segítségével a két GPU feladatait szét kell választani:
*   A **cuda:1 (P2000 5GB)** folyamatosan az Embedding modellt futtatja.
*   A **cuda:0 (P4000 8GB)** tehermentesítve van, hogy a kereső AI modellt (Llama) RAM memóriacsere (OOM) nélkül is futtatni tudja.

## 3. Pause / Resume Állapotmentés (Gép Leállás)
A gép nem fut 24/7, így a vektorizálásnak biztonságos mentésre van szüksége:
*   A JSONL átugrásánál (skip_lines) *SOHA* nem az iterátorok léptetését kell használni hatalmas fájloknál, hanem `itertools.islice`-ot, vagy a JSONL byte-méreteinek indexelését.
*   Minden megszakításkor (SIGINT/SIGTERM) be kell várni az aktuális batch SQLite-ba írását, majd menteni a Faiss Indexet.
