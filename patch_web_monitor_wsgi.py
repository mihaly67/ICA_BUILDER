import re
import sys

with open('ica_web_monitor.py', 'r') as f:
    content = f.read()

# Eltávolítjuk a Flask beépített szerverét és betesszük a Waitress-t
old_logic = '''if __name__ == '__main__':
    # 8080-as porton indítjuk el, hogy a VPS-ről elérhető legyen
    app.run(host='127.0.0.1', port=8080)'''

new_logic = '''if __name__ == '__main__':
    # Éles WSGI szerver használata a fejlesztői helyett
    from waitress import serve
    print("🚀 Jules ICA Web Monitor elindítva (Waitress WSGI). Elérhető: http://127.0.0.1:8080")
    serve(app, host='127.0.0.1', port=8080)'''

content = content.replace(old_logic, new_logic)

with open('ica_web_monitor.py', 'w') as f:
    f.write(content)
