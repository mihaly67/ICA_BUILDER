from src.monitor.app import create_app
from waitress import serve

app = create_app()

if __name__ == '__main__':
    print("🚀 Jules ICA Web Monitor elindítva (Waitress WSGI). Elérhető: http://127.0.0.1:8080")
    serve(app, host='127.0.0.1', port=8080)
