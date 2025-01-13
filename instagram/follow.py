import random
import time
from datetime import datetime
from database.models import collection_seguidos, guardar_usuario_seguido
import json
from instagram.session import cl, verificar_autenticacion, iniciar_sesion_persistente
from openai_utils import generar_mensaje_ia
from database.logs import guardar_log
from analysis.patterns import generar_sugerencia
from instagram.filters import filtrar_usuarios



# Configuración de límites
MAX_SEGUIMIENTOS_DIARIOS = 30  # Límite de seguimientos diarios
MAX_MENSAJES_DIARIOS = 10      # Límite de mensajes diarios

seguimientos_diarios = 0
mensajes_diarios = 0

# Probabilidades de acciones
PROBABILIDAD_SEGUIR = 0.5  # 50% de seguir
PROBABILIDAD_LIKE = 0.8    # 80% de dar "me gusta"
PROBABILIDAD_COMENTAR = 0.3  # 30% de comentar

# Horario permitido para interacciones
HORA_INICIO = 9  # 9:00 AM
HORA_FIN = 24    # 11:59 PM

def pausa_aleatoria(min_seg=30, max_seg=60):
    tiempo = random.uniform(min_seg, max_seg)
    print(f"Pausando por {tiempo:.2f} segundos...")
    time.sleep(tiempo)

def pausa_larga():
    """Pausa larga para simular descansos prolongados."""
    duracion = random.randint(30, 60)  # Entre 30 y 60 minutos
    print(f"Pausa larga de {duracion} minutos...")
    time.sleep(duracion * 60)

def dentro_de_horario():
    """Verifica si la hora actual está dentro del horario permitido."""
    hora_actual = datetime.now().hour
    return HORA_INICIO <= hora_actual < HORA_FIN

def usuario_ya_seguido(username):
    return collection_seguidos.find_one({"username": username}) is not None



def seguir_usuario(username, user_id):
    global seguimientos_diarios

    if usuario_ya_seguido(username):
        print(f"Usuario @{username} ya procesado. Omitiendo...")
        return

    if seguimientos_diarios >= MAX_SEGUIMIENTOS_DIARIOS:
        print("Límite diario de seguimientos alcanzado. No se realizarán más seguimientos hoy.")
        return

    try:
        print(f"Intentando seguir a: @{username}")
        cl.user_follow(user_id)
        guardar_usuario_seguido(username)
        seguimientos_diarios += 1
        print(f"Usuario @{username} seguido con éxito.")
        pausa_aleatoria(15, 30)  # Pausa entre seguimientos
    except Exception as e:
        print(f"Error al intentar seguir a @{username}: {e}")


def interactuar_con_usuario(user_id, username):
    try:
        # Dar "me gusta" a la publicación más reciente
        publicaciones = cl.user_medias(user_id, amount=1)
        if publicaciones:
            media_id = publicaciones[0].id
            cl.media_like(media_id)
            print(f"Me gusta dado a la publicación {media_id} de @{username}")
        else:
            print(f"No hay publicaciones disponibles para @{username}")
    except Exception as e:
        print(f"Error al dar 'me gusta' a @{username}: {e}")

    try:
        # Ver historias
        historias = cl.user_stories(user_id)
        if historias:
            cl.story_seen([story.id for story in historias])
            print(f"Historias vistas para @{username}")
        else:
            print(f"No hay historias disponibles para @{username}")
    except Exception as e:
        print(f"Error al ver historias de @{username}: {e}")



def seguir_y_mensajear(cuentas_competencia, username, password, filtros_formulario):
    global seguimientos_diarios, mensajes_diarios

    print(f"Iniciando seguir_y_mensajear: username={username}, cuentas_competencia={cuentas_competencia}")
    iniciar_sesion_persistente(username, password)

    if not verificar_autenticacion():
        print(f"Error: La sesión no es válida para @{username}.")
        return [], "No se pudo autenticar la sesión."

    log = []

    # Usar los filtros enviados desde el formulario
    filtros = {
        "ubicaciones": filtros_formulario.get("ubicaciones", "").split(","),
        "palabras_clave": filtros_formulario.get("palabras_clave", "").split(","),
        "min_publicaciones": int(filtros_formulario.get("min_publicaciones", 0)),
        "min_seguidores": int(filtros_formulario.get("min_seguidores", 0)),
        "tipo_cuenta": filtros_formulario.get("tipo_cuenta", "publica")
    }
    print(f"Filtros aplicados: {filtros}")

    for cuenta in cuentas_competencia:
        if not dentro_de_horario():
            print("Fuera del horario permitido. Deteniendo acciones.")
            pausa_larga()
            break

        try:
            print(f"Procesando cuenta de competencia: {cuenta}")
            user_id = cl.user_id_from_username(cuenta)
            pausa_aleatoria(5, 10)
            seguidores = cl.user_followers(user_id, amount=50)
            print(f"Seguidores obtenidos de @{cuenta}: {len(seguidores)}")

            usuarios_funcionales = []
            for seguidor in seguidores.values():
                pausa_aleatoria(10, 20)
                print(f"Verificando cuenta: @{seguidor.username}")
                if es_cuenta_funcional(seguidor):
                    usuarios_funcionales.append(seguidor)
                else:
                    print(f"Cuenta descartada: @{seguidor.username}")

            print(f"Usuarios funcionales encontrados: {[u.username for u in usuarios_funcionales]}")

            for user in usuarios_funcionales:
                print(f"Iniciando acciones para @{user.username}...")

                # Decidir si seguir al usuario
                if random.random() < PROBABILIDAD_SEGUIR:
                    print(f"Decidido: Seguir a @{user.username}")
                    seguir_usuario(user.username, user.pk)
                else:
                    print(f"No se seguirá a @{user.username}")

                # Ver historias
                try:
                    print(f"Intentando ver historias de @{user.username}...")
                    historias = cl.user_stories(user.pk)
                    if historias:
                        cl.story_seen([story.id for story in historias])
                        print(f"Historias vistas para @{user.username}")
                    else:
                        print(f"No hay historias disponibles para @{user.username}")
                except Exception as e:
                    print(f"Error al ver historias de @{user.username}: {e}")

                # Decidir si dar "me gusta"
                if random.random() < PROBABILIDAD_LIKE:
                    try:
                        publicaciones = cl.user_medias(user.pk, amount=1)
                        if publicaciones:
                            cl.media_like(publicaciones[0].id)
                            print(f"Me gusta dado a la publicación {publicaciones[0].id} de @{user.username}")
                        else:
                            print(f"No hay publicaciones disponibles para @{user.username}")
                    except Exception as e:
                        print(f"Error al dar 'me gusta' a @{user.username}: {e}")
                else:
                    print(f"No se dará 'me gusta' a @{user.username}")

                # Decidir si comentar
                if random.random() < PROBABILIDAD_COMENTAR:
                    try:
                        if publicaciones:
                            cl.media_comment(publicaciones[0].id, "¡Gran publicación!")
                            print(f"Comentario realizado en la publicación {publicaciones[0].id} de @{user.username}")
                    except Exception as e:
                        print(f"Error al comentar en @{user.username}: {e}")
                else:
                    print(f"No se comentará en publicaciones de @{user.username}")

                pausa_aleatoria(60, 120)  # Pausa entre usuarios

        except Exception as e:
            print(f"Error procesando @{cuenta}: {e}")
            continue

    if log:
        guardar_log(log)

    sugerencia = generar_sugerencia() if log else "No se generaron sugerencias."
    print(f"Sugerencia generada: {sugerencia}")
    return log, sugerencia


def es_cuenta_funcional(usuario):
    """
    Verifica si una cuenta es funcional según los criterios establecidos y realiza acciones:
    - La cuenta no es privada.
    - Tiene al menos una publicación.
    - Tiene un número mínimo de seguidores.
    Si la cuenta es funcional, realiza las acciones de seguir, dar "me gusta",
    comentar (con mensajes generados por IA) y ver historias según las probabilidades configuradas.
    
    Parámetros:
        usuario: Objeto de usuario obtenido de la API de Instagram.
    
    Retorna:
        bool: True si la cuenta cumple los criterios y se realizaron acciones, False de lo contrario.
    """
    try:
        # Obtener información del usuario desde la API
        info_usuario = cl.user_info(usuario.pk)

        # Filtrar y mostrar solo información relevante del usuario
        print(f"Procesando cuenta @{usuario.username}:")
        print(f"- Seguidores: {info_usuario.follower_count}")
        print(f"- Publicaciones: {info_usuario.media_count}")

        # Verificar si la cuenta es privada
        if info_usuario.is_private:
            print(f"[DESCARTADO] Cuenta privada: @{usuario.username}.")
            return False

        # Verificar que tenga al menos una publicación
        if info_usuario.media_count == 0:
            print(f"[DESCARTADO] Cuenta sin publicaciones: @{usuario.username}.")
            return False

        # Verificar el número mínimo de seguidores
        if info_usuario.follower_count < 10:  # Ajusta este límite según tus necesidades
            print(f"[DESCARTADO] Cuenta con pocos seguidores ({info_usuario.follower_count}): @{usuario.username}.")
            return False

        # Si la cuenta es funcional, realizar acciones
        print(f"[FUNCIONAL] Cuenta funcional: @{usuario.username}. Iniciando acciones...")

        # Acción 1: Seguir al usuario
        if random.random() < PROBABILIDAD_SEGUIR:
            try:
                cl.user_follow(usuario.pk)
                guardar_usuario_seguido(usuario.username)
                print(f"✅ Seguido con éxito: @{usuario.username}")
            except Exception as e:
                print(f"❌ Error al intentar seguir a @{usuario.username}: {e}")

        # Acción 2: Ver historias
        try:
            historias = cl.user_stories(usuario.pk)
            if historias:
                cl.story_seen([story.id for story in historias])
                print(f"✅ Historias vistas para @{usuario.username}")
            else:
                print(f"ℹ️ No hay historias disponibles para @{usuario.username}")
        except Exception as e:
            print(f"❌ Error al ver historias de @{usuario.username}: {e}")

        # Acción 3: Dar "me gusta" a la publicación más reciente
        if random.random() < PROBABILIDAD_LIKE:
            try:
                publicaciones = cl.user_medias(usuario.pk, amount=1)
                if publicaciones:
                    print(f"Publicación más reciente: ID {publicaciones[0].id}")
                    cl.media_like(publicaciones[0].id)
                    print(f"✅ 'Me gusta' dado a la publicación {publicaciones[0].id} de @{usuario.username}")
                else:
                    print(f"ℹ️ No hay publicaciones disponibles para @{usuario.username}")
            except Exception as e:
                print(f"❌ Error al dar 'me gusta' a @{usuario.username}: {e}")

        # Acción 4: Comentar en la publicación más reciente (con IA)
        if random.random() < PROBABILIDAD_COMENTAR:
            try:
                if publicaciones:
                    # Generar mensaje con IA
                    comentario = generar_mensaje_ia(usuario.username)
                    cl.media_comment(publicaciones[0].id, comentario)
                    print(f"✅ Comentario realizado en la publicación {publicaciones[0].id} de @{usuario.username}")
                else:
                    print(f"ℹ️ No hay publicaciones disponibles para comentar de @{usuario.username}")
            except Exception as e:
                print(f"❌ Error al comentar en @{usuario.username}: {e}")

        return True

    except Exception as e:
        # Manejar errores al obtener la información del usuario
        print(f"[ERROR] No se pudo verificar la cuenta @{usuario.username}: {e}")
        return False
