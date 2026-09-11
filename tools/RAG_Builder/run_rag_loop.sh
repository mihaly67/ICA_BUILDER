#!/bin/bash
# Ez a script folyamatosan újraindítja a vektorizálót, amíg az teljesen be nem fejeződik.
# Kikerüli a Python/SQLite memória és I/O szivárgását a hosszú futások során.

echo "==============================================="
echo "  🚀 RAG VEKTORIZÁLÓ KÖTEGELT INDÍTÁSA 🚀  "
echo "==============================================="

export XAUTHORITY=/home/Jules/.Xauthority
export DISPLAY=:0

# Végtelen ciklus a megszakításos futtatáshoz
while true; do
    echo -e "\n[*] Vektorizáló ciklus indítása..."

    # Biztonsági tisztítás (hogy ne maradjon beragadt memóriaszivárgó folyamat)
    killall -9 python3 2>/dev/null

    # Python script futtatása közvetlenül a konzolba (nincs nohup!)
    /home/Jules/jules_venv/bin/python3 /home/Jules/MX_LINUX_RAG/build_rag_cuda.py

    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "\n✅ Vektorizálás teljesen befejeződött, vagy a felhasználó leállította (Ctrl+C)."
        break
    elif [ $EXIT_CODE -eq 42 ]; then
        echo -e "\n🔄 [LIMIT ELÉRVE] Memória felszabadítása, adatbázis zárása... Újraindítás 1 másodperc múlva!"
        # Pici szünet, hogy az OS kidobja a RAM cache-eket
        sleep 1
    else
        echo -e "\n[!] Váratlan hiba történt (Exit kód: $EXIT_CODE). Újraindítás 5 másodperc múlva..."
        sleep 5
    fi
done

echo "==============================================="
echo "          🛑 RAG WRAPPER LEÁLLT 🛑         "
echo "==============================================="
