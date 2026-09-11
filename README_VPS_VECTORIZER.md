# VPS RAG Vectorizer

Ezzel a scripttel a VPS-en lévő ~2.2 GB-nyi nyers kódbázis vektorizálható tisztán CPU használatával, a szerver stabilitásának megőrzése mellett.

## Telepítés és Indítás a VPS-en (100.77.191.66 / 5.189.163.88)

1. Lépj be SSH-n a VPS-re:
   ```bash
   ssh misi@5.189.163.88
   ```
2. Lépj be a munkakönyvtárba:
   ```bash
   cd /home/misi/RAG_epito_ismeretek/
   ```
3. (Opcionális) Telepítsd a függőségeket, ha még nincsenek:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install torch faiss-cpu sentence-transformers
   ```
4. Indítsd el a biztonságos, memóriakímélő folyamatot:
   ```bash
   chmod +x start_vps_vectorizer.sh
   ./start_vps_vectorizer.sh
   ```

A folyamat állapota a `builder_output.log` fájlban követhető, a kimenetek pedig a `metadata.db` és a `vectors.index` fájlokba kerülnek.
