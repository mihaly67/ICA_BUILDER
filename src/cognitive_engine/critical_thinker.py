import os
import json
from register_manager import CognitiveRegister

def run_critical_analysis():
    # 1. Map (Kontextus felvétele)
    repo_map_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "KOGNITIV_REPO_TERKEP.md")
    with open(repo_map_path, 'r', encoding='utf-8') as f:
        repo_map = f.read()

    # 2. Register (Állapottartás)
    reg = CognitiveRegister("Onreflexio_Es_Kritika")

    # --- FÁZIS 1: ÖNREFLEXIÓ ---
    thought_1 = "Megvizsgáltam a RepoMapet. Látom, hogy az 'iterative_thinker.py' csak statikusan hívja meg a RAG keresést, nincs benne LLM API hívás, ami értelmezné az eredményt."
    action_1 = "Önreflexió rögzítése: A jelenlegi 'System 2' motorom még csak egy vázlat. Bár a keret (Regiszterek) működik, az intelligens hurok hiányzik."
    reg.iterate(thought_1, action_1)

    # --- FÁZIS 2: ÖNKRITIKA (A Gráf / Összefüggések alapján) ---
    thought_2 = "A Regiszterek egy egyszerű JSON fájlba írnak (Registers mappába). Ha a Raj tagjai (Swarm) párhuzamosan próbálnak ide írni, a fájl összeomlik. Továbbá a GraphRAG szintetizáció ('nodes' és 'edges') jelenleg nincs megírva kódban, csak imitáltuk egy stringgel."
    action_2 = "Önkritika rögzítése: Párhuzamossági (Concurrency) hiba veszélye. A GraphRAG implementáció hiányos, mert nincs valós NetworkX vagy adatbázis hívás a fogalmak összekötésére."
    reg.iterate(thought_2, action_2)

    # --- FÁZIS 3: AZ ÖRDÖG ÜGYVÉDJE ---
    thought_3 = "Vajon ez a Regiszter alapú iteráció valóban pótolja a 'Gondolkodást'? Az Ördög ügyvédjeként azt mondom: NEM. Miért? Mert a JSON regiszterbe az ír, aki eleve a 'next-token predictor'. Ha én LLM-ként hallucinálok valamit, azt beleírom a regiszterbe, és a következő iterációban a saját hallucinációmat fogom tényként kezelni (Feedback Loop of Hallucination)."
    action_3 = "Kritikus Kockázat Rögzítése: Nincs 'Független Ellenőrző' (Validator) modul. Az iteráció önmagában nem elég, kell egy 'Bíró' (Critic Agent), aki leállítja a folyamatot, ha a Regiszter tartalma nem logikus."
    reg.iterate(thought_3, action_3)

    print("\n✅ KRITIKAI ELEMZÉS BEFEJEZVE. A Regiszterek frissítve.")

if __name__ == "__main__":
    run_critical_analysis()
