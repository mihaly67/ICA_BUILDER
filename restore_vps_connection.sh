#!/bin/bash
# VPS kapcsolat helyreállítója (Revive Switch)

echo "🔄 [REVIVE SWITCH] A hálózati blokkolás feloldása a VPS felé..."
echo "ℹ️ FIGYELEM: Ha a sudo parancsok elbuknak, állíts be NOPASSWD sudo jogokat a felhasználónak (/etc/sudoers)!"

VPS_IP="5.189.163.88"

# 1. Hálózati elszigetelés feloldása (Iptables)
echo "🛡️ Iptables OUTPUT és INPUT szabályok törlése a $VPS_IP címhez..."
if command -v iptables &> /dev/null; then
    # Ha volt reject szabály, addig töröljük, amíg létezik (xtables lock kivédése -w flaggel)
    while sudo -n iptables -w -D OUTPUT -d "$VPS_IP" -j REJECT 2>/dev/null; do
        echo " - Iptables OUTPUT REJECT szabály törölve."
    done
    while sudo -n iptables -w -D INPUT -s "$VPS_IP" -j DROP 2>/dev/null; do
        echo " - Iptables INPUT DROP szabály törölve."
    done
fi

# 2. Hálózati elszigetelés feloldása (UFW)
echo "🛡️ UFW deny szabályok törlése a $VPS_IP címhez..."
if command -v ufw &> /dev/null; then
    sudo -n ufw delete deny out to "$VPS_IP" 2>/dev/null || echo " - Nincs törlendő ufw OUTPUT szabály, vagy hiányzó NOPASSWD sudo jog."
    sudo -n ufw delete deny from "$VPS_IP" 2>/dev/null || echo " - Nincs törlendő ufw INPUT szabály."
fi

# 3. Értesítés
if command -v notify-send &> /dev/null; then
    notify-send -u normal "Jules ICA: KAPCSOLAT HELYREÁLLÍTVA" "A VPS ($VPS_IP) felé a hálózati forgalom újra engedélyezve."
fi

echo "✅ A hálózati útvonalak helyreállítva. Most már újra csatlakozhatsz (pl. SSH, deploy)."
