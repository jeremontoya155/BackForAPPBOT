# config.py (Configuración de la aplicación)
import os

# Configuración general
DEBUG = True
UPLOAD_FOLDER = './mensajes'
LOG_FOLDER = './mensajes/logs'

# Asegurarse de que las carpetas existan
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

# Configuración de MongoDB
MONGO_URI = "mongodb://mongo:aLAubScaenVBRvqaJwNTAolWcfuzijpH@junction.proxy.rlwy.net:47226"
DB_NAME = "hunter"


# Configuración de OpenAI
OPENAI_API_KEY = "A"

from celery import Celery

def make_celery(app):
    """
    Configura una instancia de Celery con la configuración de Flask.
    """
    celery = Celery(
        app.import_name,
        broker='pyamqp://guest:guest@localhost//',
        backend='rpc://'
    )
    celery.conf.update(app.config)
    return celery

PROXIES = {
    "http": "http://acgcyous:nbz3ct3ouck0@154.194.16.49:5968",
    "https": "http://acgcyous:nbz3ct3ouck0@154.194.16.49:5968"
}
