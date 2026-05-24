#!/bin/bash
# Biztonságos Deploy Script a lokális Sandboxból a VPS-re

VPS_USER="misi"
VPS_IP="5.189.163.88"
VPS_PORT="22"
TARGET_DIR="/home/misi/Jules_ICA_Builder"

if [ -z "$VPS_PWD" ]; then
    echo "Hiba: A VPS_PWD kornyezeti valtozo nincs beallitva!"
fi

echo "🚀 Kezdodik a biztonsagos telepites (Deploy) a VPS-re..."

# 1. Biztonsági mentés készítése a szerveren
echo "📦 VPS fajlok biztonsagi mentese..."
sshpass -p "$VPS_PWD" ssh -o StrictHostKeyChecking=no $VPS_USER@$VPS_IP "tar -czf ~/Jules_ICA_backup_\$(date +%s).tar.gz -C /home/misi Jules_ICA_Builder"

# 2. Lokális fájlok átmásolása
echo "📤 Fajlok atvitele (SCP)..."
sshpass -p "$VPS_PWD" scp -o StrictHostKeyChecking=no ica_web_monitor.py $VPS_USER@$VPS_IP:$TARGET_DIR/ica_web_monitor.py
sshpass -p "$VPS_PWD" scp -o StrictHostKeyChecking=no src/tools/skills/*.py $VPS_USER@$VPS_IP:$TARGET_DIR/src/tools/skills/

# 3. Szolgáltatások újraindítása
echo "🔄 Szolgaltatasok ujrainditasa (mcp router, web monitor)..."
sshpass -p "$VPS_PWD" ssh -f -o StrictHostKeyChecking=no $VPS_USER@$VPS_IP "pkill -f ica_mcp_router.py || true; kill -9 \$(lsof -t -i :8080) 2>/dev/null || true; sh -c 'cd $TARGET_DIR && python3 ica_web_monitor.py > monitor.log 2>&1 &'"

echo "✅ Deploy sikeresen befejezodott!"
