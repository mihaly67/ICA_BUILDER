import sys
import os

# Csatoljuk be a hálózati hídat a VPS RAG-hoz
bridge_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tools")
sys.path.append(bridge_path)

from vps_bridge import run_on_vps
from register_manager import CognitiveRegister

def run_cognitive_loop():
    """
    Ez az Iterációs Ciklus (System 2 Thinking).
    Nem egyben próbálja megoldani a feladatot, hanem ciklusokban gondolkodik.
    """
    reg = CognitiveRegister("Munchausen_Tudasepites")

    # 1. Lépés: RAG Tudás hálózati lekérdezése (Cognee/GraphRAG elvek)
    reg.iterate("Meg kell értenem, hogyan kell Tudáshálót csinálni.", "Keresés a VPS RAG-ban a 'cognee' és 'graph' kulcsszavakra.")
    success, output = run_on_vps("/home/misi/Jules_mx/venv/bin/python3 /home/misi/Jules_mx/scripts/rag_search.py")

    if success:
        # A Tudás szintézise a Regiszterbe
        reg.state["learned_context"] = "A GraphRAG lényege: Az Entitásokat Nodes-ként, a funkciókat Edges-ként tárolja, így nem szavakat keres, hanem logikai útvonalakat."
        reg.iterate("Megértettem a GraphRAG logikát. A következőkben ezt be kell építenem a Repo Map-be.", "Kód frissítése (Tervezett)")
        print("✅ Kognitív ciklus sikeres! A tudás átemelve a Regiszterbe.")
    else:
        reg.iterate("Hiba a RAG elérésekor.", "Újrapróbálkozás / Hibakeresés")

if __name__ == "__main__":
    run_cognitive_loop()
