import psutil
try:
    print("Temps:")
    print(psutil.sensors_temperatures())
except Exception as e:
    print(e)
try:
    print("Freqs:")
    print(psutil.cpu_freq(percpu=True))
except Exception as e:
    print(e)
