import psutil
try:
    temps = psutil.sensors_temperatures()
    if 'coretemp' in temps:
        pkg = next((t for t in temps['coretemp'] if 'Package' in t.label), None)
        if pkg:
            print(f"Package: {pkg.current}")
        else:
            print(f"First: {temps['coretemp'][0].current}")
    else:
        print("No coretemp found")
except Exception as e:
    print(f"Error: {e}")
