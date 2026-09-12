#!/bin/bash
# 1. Kill all konsole instances directly via process name
killall -9 konsole 2>/dev/null
pkill -9 -x konsole 2>/dev/null

# 2. Kill all stray python processes related to our vectorization scripts
pkill -9 -f "8_extreme_vectorize.py"
pkill -9 -f "7_hyper_multi_gpu.py"
pkill -9 -f "5_ultra_gpu_vectorize.py"
pkill -9 -f "multiprocessing.spawn"

echo "Cleanup complete."
