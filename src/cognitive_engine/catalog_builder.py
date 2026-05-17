import json
import os

def build_catalog_from_vps(vps_path):
    """
    Később ez a függvény ssh-n/scp-n keresztül lehúzná az összes
    repó rövidített 'fülszövegét' a VPS RAG adatbázisából.
    """
    pass

def _get_mock_catalog():
    """Ideiglenes lokális katalógus teszteléshez."""
    return {
        "WebVideo2NAS": "Komplett Chrome kiterjesztés HLS/M3U8 videók sniffelésére és letöltésére a háttérben. Ezt használd, ha Manifest V3 letöltőt építesz.",
        "letta-main": "A MemGPT (most Letta) keretrendszer. Hosszú távú memória (Core Memory, Archival Memory) és OS-szerű Agent futtatás.",
        "cognee-main": "Graph-alapú memóriakezelés és kognitív hálózatépítés LLM-eknek. Tudásgráfok (Knowledge Graph) integrálása.",
        "OmniParser": "Képernyőelemző Vision rendszer. Vizuális felületek (GUI) értelmezése, gombok bounding-boxainak kinyerése.",
        "bloop-main": "Szemantikus kódkereső engine. Rust alapú gyors kód indexelés.",
        "anti-sycophancy-framework": "Keretrendszer az LLM-ek 'sycophancy' (megfelelési kényszer és hízelgés) viselkedésének csökkentésére. Módszertanok a tényszerű, objektív és az emberi véleménynek akár ellentmondó, de igaz válaszok kikényszerítésére (pl. TruthfulQA finomhangolás, System Prompt engineering)."
    }

def get_catalog():
    """Visszaadja az aktuális meta-RAG katalógust."""
    # Jelenleg a mock-ot használjuk, amíg a VPS-szel a teljes RAG szinkron nincs kész.
    return _get_mock_catalog()

if __name__ == "__main__":
    cat = get_catalog()
    print("Elérhető kognitív katalógus:")
    print(json.dumps(cat, indent=4, ensure_ascii=False))
