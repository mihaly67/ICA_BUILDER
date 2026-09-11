#!/bin/bash
cd /home/misi/RAG_epito_ismeretek/
source venv/bin/activate
# Vektorizalo leallitasa es ujrainditasa, hogy biztosan a jo fusson
pkill -f vps_cpu_vectorizer || true
python3 vps_cpu_vectorizer.py > builder_output.log 2>&1 &
echo $! > builder.pid
