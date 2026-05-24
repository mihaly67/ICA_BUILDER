#!/bin/bash
# VPS kapcsolat azonnali megszakítója (Kill Switch)
# Hardened, Zero-Trust verzió

echo "🚨 [KILL SWITCH] Megszakítom az SSH kapcsolatot és elszigetelem a gépet a VPS-től..."

VPS_IP="5.189.163.88"

# 1. Minden SSH kapcsolat megszakítása (sockets, agent, futó processek)
echo "🔧 SSH Agent kulcsok törlése és kapcsolatok lezárása..."
ssh-add -D || true
pkill -f "ssh.*$VPS_IP" || true
pkill -f "sshpass" || true
pkill -f "scp.*$VPS_IP" || true

# 2. Hálózati elszigetelés (Iptables Reject szabály ideiglenesen)
echo "🛡️ Hálózati útválasztás blokkolása a VPS felé..."
if command -v iptables &> /dev/null; then
    sudo iptables -A OUTPUT -d "$VPS_IP" -j REJECT || echo "⚠️ Nem sikerült az iptables szabályt hozzáadni (nincs sudo jog?)."
fi
if command -v ufw &> /dev/null; then
    sudo ufw deny out to "$VPS_IP" || echo "⚠️ Nem sikerült az ufw szabályt hozzáadni."
fi

# 3. Mountolt fájlrendszerek leválasztása (lazy unmount)
echo "🔌 Hálózati megosztások leválasztása..."
if mount | grep -q "Jules_ICA_Builder"; then
    fusermount -uz ~/Jules_ICA_Builder_Remote || true
    umount -l ~/Jules_ICA_Builder_Remote || true
fi

# 4. Értesítés (ha asztali környezeten fut)
if command -v notify-send &> /dev/null; then
    notify-send -u critical "Jules ICA: VÉSZLEÁLLÍTÁS" "A VPS kapcsolat levágva és blokkolva a hálózaton!"
fi

echo "✅ A rendszer biztonságosan leválasztva a VPS-ről."
read -p "Nyomj entert a bezáráshoz..."
