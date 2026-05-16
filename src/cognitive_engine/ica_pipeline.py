import sys
import os
import json

from catalog_builder import get_catalog
from repo_mapper import generate_repo_map
from register_manager import CognitiveRegister

def run_ica_pipeline(user_prompt):
    print(f"\n=============================================")
    print(f"🧠 [ICA BUILDER] KOGNITÍV CIKLUS INDÍTÁSA")
    print(f"Feladat: '{user_prompt}'")
    print(f"=============================================\n")

    # --- 1. LÉPÉS: REPÓ KIVÁLASZTÁS A KATALÓGUSBÓL ---
    print("📚 LÉPÉS 1: Katalógus (Meta-RAG) Keresés...")
    catalog = get_catalog()
    selected_repo = None

    # Egyszerű kulcsszó alapú döntés (Az LLM gondolkodását szimulálva)
    # Ha a prompt tartalmaz kulcsszavakat, kiválasztja a megfelelő "könyvet" a polcról
    prompt_lower = user_prompt.lower()
    if "letöltő" in prompt_lower or "kiterjesztés" in prompt_lower or "hls" in prompt_lower:
        selected_repo = "WebVideo2NAS"
    elif "memória" in prompt_lower or "regiszter" in prompt_lower:
        selected_repo = "letta-main"
    elif "hálózat" in prompt_lower or "graph" in prompt_lower:
        selected_repo = "cognee-main"
    elif "látás" in prompt_lower or "gomb" in prompt_lower:
        selected_repo = "OmniParser"
    elif "ember" in prompt_lower or "kedvező" in prompt_lower or "félrevezeti" in prompt_lower or "sycophancy" in prompt_lower:
         selected_repo = "anti-sycophancy-framework"
    else:
        selected_repo = "bloop-main" # Fallback

    print(f"   -> DÖNTÉS: A feladathoz a '{selected_repo}' repót veszem le a polcról.")
    print(f"   -> Fülszöveg: {catalog.get(selected_repo)}")


    # --- 2. LÉPÉS: TARTALOMJEGYZÉK (REPO-MAP) OLVASÁSA ---
    print("\n🗺️  LÉPÉS 2: Tartalomjegyzék (Repo-Map) Elemzése...")
    # Itt a VPS-ről húzná le az adott repó térképét. Mivel lokális tesztet futtatunk,
    # generálunk egy "virtuális" térképet az általa kiválasztott repóról.
    virtual_map = f"""
    📁 {selected_repo}/
        📄 README.md
        📄 main.py
            ⚙️ def start_process()
        📄 core_logic.py
            🧩 class Engine
        📄 prompts.py
            🧩 def get_anti_sycophancy_prompt()
    """
    print(f"   -> Térkép beolvasva. Releváns fájl megtalálva: 'prompts.py' és 'core_logic.py'")


    # --- 3. LÉPÉS: REGISZTEREK (ITERÁCIÓ) ÉS ÖRDÖG ÜGYVÉDJE ---
    print("\n⚖️  LÉPÉS 3: Szintézis, Regiszterek és Ördög Ügyvédje...")
    reg = CognitiveRegister("ICA_Task_" + selected_repo)

    # Reflexió rögzítése
    reg.iterate(
        thought=f"A '{selected_repo}' repó 'prompts.py' és 'core_logic.py' fájljai alapján az a tervem, hogy a System Prompt-ot kiegészítem azzal az utasítással: 'Tilos hízelegni az embernek. Ha az ember téved, kötelező jelezni. Ne feltételezd, hogy az emberi vélemény objektív igazság.'",
        action="Új System Prompt és validációs logika beillesztése."
    )

    # Ördög ügyvédje rögzítése
    reg.iterate(
        thought=f"Ördög ügyvédjeként felülvizsgálom: Tényleg fedi a terv a '{user_prompt}' kérést? Csak egy prompt módosítás elég, vagy be kell vezetni egy megerősítési lépést a láncban, ami kiszűri a 'sycophantic' elemeket a generálás után?",
        action="Terv finomítása: LLM output filter bevezetése a promptoláson felül."
    )

    print("\n✅ CIKLUS BEFEJEZVE.")
    print(f"📂 A gondolatmenet és a kontextus elmentve a 'Registers/ICA_Task_{selected_repo}_state.json' fájlba.")
    print("=============================================\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        # Default fallback ha nem adunk meg argumentumot
        prompt = "Hogyan készítsek egy chrome kiterjesztést ami HLS videókat tölt le?"
    run_ica_pipeline(prompt)
