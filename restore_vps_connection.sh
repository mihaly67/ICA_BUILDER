#!/bin/bash
# VPS kapcsolat helyreállítója (Revive Switch)

echo "🔄 [REVIVE SWITCH] A hálózati blokkolás feloldása a VPS felé..."
echo "ℹ️ FIGYELEM: Ha a sudo parancsok elbuknak, állíts be NOPASSWD sudo jogokat a felhasználónak (/etc/sudoers)!"

VPS_IP="5.189.163.88"

# 1. Hálózati elszigetelés feloldása (Iptables)
echo "🛡️ Iptables OUTPUT szabályok törlése a $VPS_IP címhez..."
if command -v iptables &> /dev/null; then
    # Ha volt reject szabály, addig töröljük, amíg létezik
    while sudo -n iptables -D OUTPUT -d "$VPS_IP" -j REJECT 2>/dev/null; do
        echo " - Iptables REJECT szabály törölve."
    done
fi

# 2. Hálózati elszigetelés feloldása (UFW)
echo "🛡️ UFW deny szabályok törlése a $VPS_IP címhez..."
if command -v ufw &> /dev/null; then
    sudo -n ufw delete deny out to "$VPS_IP" 2>/dev/null || echo " - Nincs törlendő ufw szabály, vagy hiányzó NOPASSWD sudo jog."
fi

# 3. Értesítés
if command -v notify-send &> /dev/null; then
    notify-send -u normal "Jules ICA: KAPCSOLAT HELYREÁLLÍTVA" "A VPS ($VPS_IP) felé a hálózati forgalom újra engedélyezve."
fi

echo "✅ A hálózati útvonalak helyreállítva. Most már újra csatlakozhatsz (pl. SSH, deploy)."
