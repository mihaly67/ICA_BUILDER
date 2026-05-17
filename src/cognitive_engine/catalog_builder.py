import json
import os

def build_catalog_from_vps(vps_path):
    """
    Később ez a függvény ssh-n/scp-n keresztül lehúzná az összes
    repó rövidített 'fülszövegét' a VPS RAG adatbázisából.
    """
    pass

def _get_mock_catalog():
    """Ideiglenes lokális katalógus teszteléshez és VPS DB inicializáláshoz."""
    return {
        # --- Web & Vision Tools ---
        "WebVideo2NAS": "Komplett Chrome kiterjesztés HLS/M3U8 videók sniffelésére és letöltésére a háttérben. Ezt használd, ha Manifest V3 letöltőt építesz.",
        "OmniParser": "Képernyőelemző Vision rendszer. Vizuális felületek (GUI) értelmezése, gombok bounding-boxainak kinyerése.",

        # --- Cognitive & Memory ---
        "letta-main": "A MemGPT (most Letta) keretrendszer. Hosszú távú memória (Core Memory, Archival Memory) és OS-szerű Agent futtatás.",
        "cognee-main": "Graph-alapú memóriakezelés és kognitív hálózatépítés LLM-eknek. Tudásgráfok (Knowledge Graph) integrálása.",
        "bloop-main": "Szemantikus kódkereső engine. Rust alapú gyors kód indexelés.",

        # --- Anti-Sycophancy & Honesty ---
        "anti-sycophancy-framework": "Keretrendszer az LLM-ek 'sycophancy' (megfelelési kényszer és hízelgés) viselkedésének csökkentésére. Módszertanok a tényszerű, objektív és az emberi véleménynek akár ellentmondó, de igaz válaszok kikényszerítésére.",
        "sycophancy-eval": "Adathalmazok a 'Towards Understanding Sycophancy in Language Models' című cikkből az LLM szolgalelkűség kiértékelésére.",
        "LLM-sycophancy": "Az 'Uncovering the Internal Origins of Sycophancy in Large Language Models' (AAAI'26) hivatalos kódja, amely a sycophancy belső eredetét kutatja.",
        "awesome-llm-self-reflection": "Gyűjtemény (Awesome-list) az LLM-ek self-reflection és self-correction módszereiről.",
        "mcp-structured-thinking": "TypeScript Model Context Protocol (MCP) szerver, amely lehetővé teszi az LLM-ek számára gondolattérképek programozott építését, kikényszerített 'metakognitív' önreflexióval.",

        # --- LLM Runtime Environments (Környezet/Viselkedés befecskendezés) ---
        "kairos-runtime": "Egy ügynök runtime, amely az operációs rendszer primitívjeként kezeli a kontextust, a végrehajtást és a jogosultságokat, ahelyett, hogy ezeket egyszerű LLM problémaként fogná fel.",
        "Aios": "AI-Native Operating Environment. Linux alapú OS Rust kernel modulokkal és Python AI runtime-mal. Multi-agent hangszerelés és szándékvezérelt (intent-driven) számítástechnika.",
        "loomcycle": "Agentic rendszerek futtatói szubsztrátja (runtime substrate) - egy Go bináris, MCP-natív, menedzselt sandboxként és agent dev környezetként is konfigurálható.",
        "agentruntime": "Egy átfogó platform AI ügynökök lokális környezetben történő futtatásához. Egységes futtatókörnyezetet biztosít különböző képességű és eszközökkel rendelkező LLM ügynökök számára."
    }

def get_catalog():
    """Visszaadja az aktuális meta-RAG katalógust."""
    return _get_mock_catalog()

def export_catalog_to_json(filepath="src/cognitive_engine/katalogus.json"):
    """Exportálja a katalógust egy fizikai JSON fájlba (később VPS feltöltéshez)."""
    cat = get_catalog()
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(cat, f, indent=4, ensure_ascii=False)
    print(f"✅ Katalógus sikeresen exportálva: {filepath}")
    return filepath

if __name__ == "__main__":
    export_catalog_to_json()
    cat = get_catalog()
    print("Elérhető kognitív katalógus frissítve.")
