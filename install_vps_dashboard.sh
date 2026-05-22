#!/bin/bash
# Telepíti a szükséges függőségeket a VPS-en lévő virtuális környezetbe

VENV_PATH="/home/misi/Jules_mx/venv"

echo "🔧 Függőségek telepítése a VPS venv-be..."
$VENV_PATH/bin/python3 -m pip install flask rich textual

echo "✅ Telepítés kész!"
