#!/bin/bash

# A felhasználó kérésére NEM hozunk létre új 5GB-os venv-et, hanem a már meglévő
# központi 8GB-os környezetet aktiváljuk a fizikai gépen.
VENV_PATH="/home/Jules/jules_venv"

echo "[*] Központi VENV aktiválása ($VENV_PATH)..."
source "$VENV_PATH/bin/activate"

echo "[*] Függőségek ellenőrzése és telepítése a központi venv-be..."
pip install --upgrade pip

# ELSŐKÉNT a cu118-as Torch-ot kell telepíteni a --no-cache-dir flaggel!
# Ha a sentence-transformers-t telepítjük előbb, akkor a pip alapértelmezetten lerántja a PyPI cu12-es (3GB+) csomagjait!
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu118

# A Quadro P2000 (Pascal) architektúra miatt a faiss-gpu hibát (CUDA 209) dob,
# ezért faiss-cpu-ra váltunk! A SentenceTransformer így is a GPU-n pörög!
pip uninstall -y faiss-gpu || true
pip install --no-cache-dir transformers==4.40.0 sentence-transformers==2.7.0 tqdm faiss-cpu

echo "[*] Függőségek telepítve CUDA támogatással! A RAG építő szkript futtatásához indítsd el:"
echo "source $VENV_PATH/bin/activate"
echo "python3 /home/Jules/MX_LINUX_RAG/build_rag_cuda.py"
