#!/bin/bash

VENV_PATH="/home/Jules/jules_venv"

echo "[*] Központi VENV aktiválása ($VENV_PATH)..."
source "$VENV_PATH/bin/activate"

echo "[*] Függőségek ellenőrzése és telepítése a központi venv-be..."
pip install --upgrade pip

# ELSŐKÉNT a cu118-as Torch-ot kell telepíteni a --no-cache-dir flaggel!
pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu118

# A faiss csomagokat teljesen lepucoljuk, mert a 1.13+ verziók gyakran hibásan installálódnak (üres namespace) PyTorch környezetben!
pip uninstall -y faiss faiss-gpu faiss-cpu || true

# A 'transformers' csomagból downgrade-elünk a 4.40.0 verzióra
# A 'faiss-cpu'-t egy stabil 1.7.4-es verzióra pinneljük, hogy biztosan meglegyen a C++ wrapper!
pip install --no-cache-dir transformers==4.40.0 sentence-transformers==2.7.0 tqdm faiss-cpu==1.7.4

echo "[*] Függőségek telepítve CUDA támogatással! A RAG építő szkript futtatásához indítsd el:"
echo "source $VENV_PATH/bin/activate"
echo "python3 /home/Jules/MX_LINUX_RAG/build_rag_cuda.py"
