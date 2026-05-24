#!/bin/bash
# Biztonságos Deploy Script a lokális Sandboxból a VPS-re (Zero Trust)
# Elvárás: Előzetesen beállított jelszó nélküli SSH kulcs alapú hozzáférés (ssh-copy-id).

set -euo pipefail # Szigorú hibakezelés: hiba esetén azonnali leállás

VPS_USER="misi"
VPS_IP="5.189.163.88"
TARGET_DIR="/home/misi/Jules_ICA_Builder"

# Takarítás hiba esetén (Trap)
cleanup_on_error() {
    local exit_code=$?
    echo "❌ [HIBA] A telepítés megszakadt a(z) $exit_code hibakóddal."
    echo "⚠️ A fájlok egy része felkerülhetett a VPS-re, vagy a mentés befejezetlen. Ellenőrizd a VPS állapotát ($TARGET_DIR)!"
    # Ide kerülhet a visszagörgetési (rollback) logika, pl. a tar.gz kicsomagolása a szerveren.
    exit $exit_code
}
trap cleanup_on_error ERR

echo "🚀 Kezdődik a biztonságos telepítés (Deploy) a VPS-re..."

# 0. SSH Kapcsolat Validálása (Jelszó nélkül)
echo "🔒 Hitelesítés ellenőrzése (Public Key)..."
if ! ssh -o BatchMode=yes -o ConnectTimeout=5 "$VPS_USER@$VPS_IP" echo "Ping" > /dev/null; then
    echo "❌ Hiba: Nincs jelszó nélküli SSH hozzáférés! Futtasd: ssh-copy-id $VPS_USER@$VPS_IP"
    exit 1
fi
echo "✅ Hitelesítés sikeres."

# 1. Biztonsági mentés készítése a szerveren
echo "📦 VPS fájlok biztonsági mentése..."
ssh -o BatchMode=yes "$VPS_USER@$VPS_IP" "if [ -d \"$TARGET_DIR\" ]; then tar -czf ~/Jules_ICA_backup_\$(date +%s).tar.gz -C /home/misi Jules_ICA_Builder; fi"

# 2. Lokális fájlok átmásolása (rsync használata biztonságos szűréssel)
echo "📤 Fájlok átvitele (rsync)..."
rsync -avz -e "ssh -o BatchMode=yes" \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.db' \
    --exclude '*.sqlite' \
    --exclude '*.log' \
    --exclude '.env' \
    --exclude 'temp_*.py' \
    --exclude 'patch_*.py' \
    --exclude 'jules_*.desktop' \
    ./ "$VPS_USER@$VPS_IP:$TARGET_DIR/"

# 3. Szolgáltatások újraindítása
echo "🔄 Szolgáltatások újraindítása (mcp router, web monitor)..."
ssh -o BatchMode=yes "$VPS_USER@$VPS_IP" "
    pkill -f ica_mcp_router.py || true;
    kill -9 \$(lsof -t -i :8080) 2>/dev/null || true;
    cd $TARGET_DIR && nohup python3 src/tools/skills/ica_mcp_router.py > mcp_router.log 2>&1 & nohup python3 ica_web_monitor.py > monitor.log 2>&1 &
"

# 4. Tamper-Proofing (Append-Only) bekapcsolása a logokra (Opcionális: NOPASSWD sudo esetén)
echo "🔒 Tamper-proofing (chattr +a) megkísérlése a naplófájlokon..."
ssh -o BatchMode=yes "$VPS_USER@$VPS_IP" "
    cd $TARGET_DIR;
    touch monitor_errors.log monitor.log mcp_router.log;
    sudo -n chattr +a monitor_errors.log 2>/dev/null || echo ' - (i) Nincs sudo jog a chattr-hez, Append-Only mód átugorva.';
    sudo -n chattr +a monitor.log 2>/dev/null || true;
    sudo -n chattr +a mcp_router.log 2>/dev/null || true;
"

# Siker esetén a trap levétele
trap - ERR

echo "✅ Deploy sikeresen befejeződött!"
echo "ℹ️ Megjegyzés: A 'chattr +a' (Append-Only) működéséhez a /etc/sudoers fájlban engedélyezni kell: $VPS_USER ALL=(ALL) NOPASSWD: /usr/bin/chattr"
