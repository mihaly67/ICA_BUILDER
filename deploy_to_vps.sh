#!/bin/bash
# Biztonságos Deploy Script a lokális Sandboxból a VPS-re (Zero Trust)
# Állapottudatos (State-Aware) verzió Systemd és SHA256 integrációval

set -euo pipefail

VPS_USER="misi"
VPS_IP="5.189.163.88"
TARGET_DIR="/home/misi/Jules_ICA_Builder"

cleanup_on_error() {
    local exit_code=$?
    echo "❌ [HIBA] A telepítés megszakadt a(z) $exit_code hibakóddal."
    echo "⚠️ A rendszer állapota nem garantált. Kérlek, ellenőrizd a VPS logjait!"
    exit $exit_code
}
trap cleanup_on_error ERR

echo "🚀 Kezdődik a biztonságos telepítés (Deploy) a VPS-re..."

# 0. SSH Kapcsolat Validálása
echo "🔒 Hitelesítés ellenőrzése (Public Key)..."
if ! ssh -n -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 "$VPS_USER@$VPS_IP" echo "Ping" > /dev/null; then
    echo "❌ Hiba: Nincs jelszó nélküli SSH hozzáférés, vagy megváltozott a szerver kulcsa! Futtasd: ssh-copy-id $VPS_USER@$VPS_IP"
    exit 1
fi
echo "✅ Hitelesítés sikeres."

# 1. Biztonsági mentés készítése
echo "📦 VPS fájlok biztonsági mentése..."
ssh -n -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$VPS_USER@$VPS_IP" "
    if [ -d \"$TARGET_DIR\" ]; then
        tar -czf ~/Jules_ICA_backup_\$(date +%s).tar.gz -C /home/misi Jules_ICA_Builder
    else
        mkdir -p \"$TARGET_DIR\"
    fi
"

# 2. Lokális Hash-Pinning (Manifest generálása)
echo "🧮 Kód integritás (SHA256 Manifest) generálása..."
# Csak a Python fájlokat ellenőrizzük az integritáshoz, mivel a logok és adatbázisok változnak
find . -name "*.py" -not -path "*/__pycache__/*" -exec sha256sum {} + > manifest.sha256

# 3. Fájlok átmásolása (rsync)
echo "📤 Fájlok átvitele (rsync)..."
rsync -avz -e "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new" \
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

# 4. Systemd Service beállítása és újraindítás a VPS-en
echo "🔄 Állapotalapú szolgáltatás (Systemd) konfigurálása és újraindítása..."
ssh -n -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$VPS_USER@$VPS_IP" "
    # Linger bekapcsolása, hogy a user service-k fussanak kijelentkezés után is
    loginctl enable-linger \$USER || true

    mkdir -p ~/.config/systemd/user/

    # ica-router.service generálása
    cat << 'SVC' > ~/.config/systemd/user/ica-router.service
[Unit]
Description=Jules ICA MCP Router
After=network.target

[Service]
Type=simple
WorkingDirectory=$TARGET_DIR
ExecStart=/usr/bin/python3 src/tools/skills/ica_mcp_router.py
StandardOutput=append:$TARGET_DIR/mcp_router.log
StandardError=append:$TARGET_DIR/mcp_router.log
Restart=on-failure
RestartSec=5
KillSignal=SIGTERM
TimeoutStopSec=10

[Install]
WantedBy=default.target
SVC

    # ica-monitor.service generálása
    cat << 'SVC' > ~/.config/systemd/user/ica-monitor.service
[Unit]
Description=Jules ICA Web Monitor
After=network.target

[Service]
Type=simple
WorkingDirectory=$TARGET_DIR
ExecStart=/usr/bin/python3 ica_web_monitor.py
StandardOutput=append:$TARGET_DIR/monitor.log
StandardError=append:$TARGET_DIR/monitor_errors.log
Restart=on-failure
RestartSec=5
KillSignal=SIGTERM
TimeoutStopSec=10

[Install]
WantedBy=default.target
SVC

    # Systemd daemon frissítése és szolgáltatások indítása
    systemctl --user daemon-reload
    systemctl --user enable ica-router.service ica-monitor.service
    systemctl --user restart ica-router.service ica-monitor.service
"

# 5. Tamper-Proofing (Append-Only) és Hash ellenőrzés
echo "🔒 Integritás ellenőrzése és Tamper-proofing (chattr +a)..."
ssh -n -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$VPS_USER@$VPS_IP" "
    cd $TARGET_DIR;
    # Hash verifikáció
    echo ' - SHA256 Manifest ellenőrzése...'
    sha256sum -c manifest.sha256 --quiet || { echo '❌ Hiba: Az integritás ellenőrzés (Hash) elbukott a VPS-en!'; exit 1; }
    echo ' - ✅ Hash-Pinning sikeres. A kód nem korrumpálódott.'

    touch monitor_errors.log monitor.log mcp_router.log Knowledge_Base/agent_memory.jsonl;
    sudo -n chattr +a monitor_errors.log monitor.log mcp_router.log Knowledge_Base/agent_memory.jsonl || echo '⚠️ Nincs NOPASSWD sudo jog a chattr-hez, Append-Only (Fekete Doboz) mód SIKERTELEN.';
"

# 6. Healthcheck (State-Awareness)
echo "🩺 Healthcheck (Állapotellenőrzés) futtatása a szolgáltatásokon..."
sleep 3 # Várunk, hogy a Waitress és a Router elinduljon
ssh -n -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$VPS_USER@$VPS_IP" "
    if curl -s http://127.0.0.1:8080/api/data | grep -q '\"stats\"'; then
        echo ' - ✅ Web Monitor sikeresen válaszol (HTTP 200) és aktív.'
    else
        echo '❌ Hiba: A Web Monitor elindult, de nem válaszol a lokális 8080-as porton!'
        systemctl --user status ica-monitor.service --no-pager
        exit 1
    fi
"

trap - ERR
echo "✅ Deploy sikeresen befejeződött és validálva lett!"
