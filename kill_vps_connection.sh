#!/bin/bash
# VPS kapcsolat azonnali megszakítója (Kill Switch)
# Futtasd ezt lokálisan, ha az AI elszabadul vagy biztonsági kockázat merül fel!

echo "🚨 [KILL SWITCH] Megszakítom az SSH kapcsolatot a VPS-el..."

# 1. SSH folyamatok kilövése (pl. ssh tunnel)
echo "🔧 Lokális SSH és SSHPASS folyamatok kilövése..."
pkill -f "sshpass" || true
pkill -f "ssh -N -L" || true

# 2. Ha az sshfs fel lenne csatolva, lecsatoljuk
echo "🔌 Hálózati megosztások leválasztása..."
if mount | grep -q "Jules_ICA_Builder"; then
    fusermount -u ~/Jules_ICA_Builder_Remote || true
fi

# 3. Értesítés (ha asztali környezeten fut)
if command -v notify-send &> /dev/null; then
    notify-send -u critical "Jules ICA: VÉSZLEÁLLÍTÁS" "A VPS kapcsolat és SSH tunnel megszakítva!"
fi

echo "✅ Kapcsolat levágva."
read -p "Nyomj entert a bezáráshoz..."
