#!/bin/bash

# A script telepíti a VPS oldali Graph Builder szervizt
# Használat: SSH_PASS=your_password ./install_sync_services.sh

VPS_IP="${VPS_IP:-5.189.163.88}"
VPS_USER="${VPS_USER:-misi}"
REMOTE_DIR="/home/misi/Jules_ICA_Builder"

if [ -z "$SSH_PASS" ]; then
    echo "Hiba: Az SSH_PASS környezeti változó nincs beállítva."
    return 1 2>/dev/null || true
fi

echo "Töltöm fel a graph_builder_service.py fájlt a VPS-re..."
sshpass -p "$SSH_PASS" scp -o StrictHostKeyChecking=no tools/graph_builder_service.py $VPS_USER@$VPS_IP:$REMOTE_DIR/tools/

echo "Készítem a Systemd szerviz fájlt a VPS-re..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no $VPS_USER@$VPS_IP << 'EOF_VPS'
mkdir -p ~/.config/systemd/user/

cat << 'SYS' > ~/.config/systemd/user/ica-graph-builder.service
[Unit]
Description=ICA Knowledge Graph Builder Service
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/misi/Jules_ICA_Builder
ExecStart=/usr/bin/python3 /home/misi/Jules_ICA_Builder/tools/graph_builder_service.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
SYS

systemctl --user daemon-reload
systemctl --user enable ica-graph-builder.service
systemctl --user restart ica-graph-builder.service
echo "VPS Graph Builder szerviz sikeresen újraindítva."
EOF_VPS

echo "Telepítés kész!"
