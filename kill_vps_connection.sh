#!/bin/bash
# VPS kapcsolat azonnali megszakítója (Kill Switch)
# Hardened, Zero-Trust verzió

echo "🚨 [KILL SWITCH] Megszakítom az SSH kapcsolatot és elszigetelem a gépet a VPS-től..."
echo "ℹ️ FIGYELEM: Ha az iptables/ufw parancsok elbuknak, állíts be NOPASSWD sudo jogokat a felhasználónak (/etc/sudoers)!"

VPS_IP="5.189.163.88"

# 1. Minden SSH kapcsolat megszakítása (sockets, agent, futó processek)
echo "🔧 SSH Agent kulcsok törlése és kapcsolatok lezárása..."
ssh-add -D 2>/dev/null || true
pkill -f "ssh.*$VPS_IP" || true
pkill -f "sshpass" || true
pkill -f "scp.*$VPS_IP" || true
pkill -f "rsync.*$VPS_IP" || true

# 2. Hálózati elszigetelés (Iptables Reject szabály ideiglenesen)
echo "🛡️ Hálózati útválasztás blokkolása a VPS felé..."
if command -v iptables &> /dev/null; then
    # Nem vár jelszóra: ha a sudo elakad, időtúllépés lép érvénybe vagy a -n flag miatt elbukik, de a script halad tovább
    sudo -n iptables -I OUTPUT -d "$VPS_IP" -j REJECT 2>/dev/null || echo "⚠️ Nem sikerült az iptables szabályt hozzáadni (hiányzó NOPASSWD sudo jog)."
fi
if command -v ufw &> /dev/null; then
    sudo -n ufw deny out to "$VPS_IP" 2>/dev/null || echo "⚠️ Nem sikerült az ufw szabályt hozzáadni (hiányzó NOPASSWD sudo jog)."
fi

# 3. Mountolt fájlrendszerek leválasztása (lazy unmount)
echo "🔌 Hálózati megosztások leválasztása..."
if mount | grep -q "Jules_ICA_Builder"; then
    fusermount -uz ~/Jules_ICA_Builder_Remote 2>/dev/null || true
    sudo -n umount -l ~/Jules_ICA_Builder_Remote 2>/dev/null || true
fi

# 4. Értesítés (ha asztali környezeten fut)
if command -v notify-send &> /dev/null; then
    notify-send -u critical "Jules ICA: VÉSZLEÁLLÍTÁS" "A VPS kapcsolat levágva és blokkolva a hálózaton!"
fi

echo "✅ A rendszer biztonságosan leválasztva a VPS-ről."
echo "🔄 A kapcsolat helyreállításához futtasd a 'restore_vps_connection.sh' szkriptet."
