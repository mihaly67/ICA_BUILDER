from flask import Flask
import logging
import psutil

# Setup initial CPU percentage calculation
psutil.cpu_percent()

# Configure logging
if not logging.getLogger().handlers:
    logging.basicConfig(filename='monitor_errors.log', level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def create_app():
    app = Flask(__name__)

    from src.monitor.routes.api import api_bp
    from src.monitor.routes.views import views_bp

    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)

    return app
