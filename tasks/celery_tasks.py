from celery import Celery
from instagram.follow import seguir_y_mensajear
from instagrapi import Client
from database.models import db, guardar_usuario_seguido, collection_seguidos
from analysis.patterns import analizar_patrones_perfiles, sugerir_perfiles
from openai_utils import generar_mensaje_ia
from datetime import datetime

cl = Client()

# Configuración de Celery
def make_celery(app):
    celery = Celery(
        app.import_name,
        broker='pyamqp://guest:guest@localhost//',
        backend='rpc://'
    )
    celery.conf.update(app.config)
    return celery

@celery.task
def analizar_perfiles(kol):
    try:
        print(f"Analizando seguidores de @{kol}...")
        user_id = cl.user_id_from_username(kol)
        seguidores = cl.user_followers(user_id, amount=50)
        for username, datos in seguidores.items():
            guardar_usuario_seguido(username)
        return f"Seguidores analizados de @{kol}."
    except Exception as e:
        return f"Error al analizar perfiles de @{kol}: {e}"

# Tarea para generar sugerencias diarias
@celery.task
def generar_sugerencias_diarias():
    """
    Genera sugerencias de perfiles diariamente y las guarda en la base de datos.
    """
    try:
        # Obtener los perfiles existentes en la base de datos
        perfiles = list(collection_seguidos.find({}, {"_id": 0, "username": 1, "biography": 1}))
        
        # Analizar patrones
        patrones = analizar_patrones_perfiles(perfiles)
        
        # Buscar nuevas sugerencias
        cuentas_competencia = ["cuenta1", "cuenta2", "cuenta3"]  # Reemplazar con las cuentas relevantes
        sugerencias = sugerir_perfiles(patrones, cuentas_competencia)
        
        # Agregar la fecha a cada sugerencia
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        for sugerencia in sugerencias:
            sugerencia["fecha"] = fecha_hoy

        # Guardar sugerencias en la base de datos
        db["sugerencias_diarias"].insert_many(sugerencias)
        print("Sugerencias diarias generadas y guardadas.")
        return "Sugerencias diarias generadas con éxito."
    except Exception as e:
        print(f"Error generando sugerencias diarias: {e}")
        return f"Error: {e}"

@celery.task
def enviar_mensajes(filtro):
    perfiles = collection_seguidos.find(filtro)
    enviados = 0
    for perfil in perfiles:
        username = perfil.get("username")
        mensaje = generar_mensaje_ia(username)
        try:
            cl.direct_send(mensaje, [perfil["_id"]])
            print(f"Mensaje enviado a @{username}: {mensaje}")
            enviados += 1
        except Exception as e:
            print(f"Error al enviar mensaje a @{username}: {e}")
    return f"Mensajes enviados a {enviados} perfiles."

