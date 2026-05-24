#!/bin/bash
# Telepíti a szükséges függőségeket a VPS Dashboardhoz (Jules ICA Web Monitor)
# Mivel a VPS Ubuntu 24.04-en PEP 668 van érvényben, a globális telepítéshez
# kötelező a --break-system-packages kapcsoló (ha nem venv-et használunk)

echo "📦 Telepítem a Web Monitor függőségeit (Flask, Waitress)..."
python3 -m pip install flask waitress --break-system-packages

echo "✅ Kész! Most már indítható az ica_web_monitor.py"
