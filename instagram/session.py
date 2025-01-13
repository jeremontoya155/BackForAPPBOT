from instagrapi import Client
from instagrapi.exceptions import LoginRequired
from database.models import guardar_token, obtener_token, limpiar_sesion
from instagrapi.exceptions import ChallengeRequired
from instagrapi.exceptions import TwoFactorRequired
from config import PROXIES
import requests


cl = Client()

def iniciar_sesion_con_2fa(username, password):
    try:
        cl.login(username, password)
        print("Sesión iniciada correctamente.")
    except TwoFactorRequired:
        two_factor_code = input("Introduce el código 2FA de tu aplicación autenticadora: ")
        cl.two_factor_login(two_factor_code)
        print("Sesión con 2FA completada.")
    except Exception as e:
        print(f"Error durante el inicio de sesión: {e}")
        raise


def iniciar_sesion(username, password):
    try:
        cl.login(username, password)
        print("Sesión iniciada correctamente.")
    except ChallengeRequired:
        print("Se requiere resolver un desafío de seguridad.")
        challenge_url = cl.last_json.get("challenge", {}).get("url")
        if challenge_url:
            try:
                cl.challenge_resolve(challenge_url)
                print("Desafío resuelto automáticamente.")
            except Exception as e:
                print(f"No se pudo resolver el desafío automáticamente: {e}")
                print("Es necesario que inicies sesión manualmente.")
                raise
    except Exception as e:
        print(f"Error al iniciar sesión: {e}")
        raise

def iniciar_sesion_persistente(username, password):
    configurar_cliente()
    print(f"Iniciando sesión persistente para @{username}...")

    settings = obtener_token(username)  # Recuperar configuración guardada
    if settings:
        try:
            cl.set_settings(settings)  # Restaurar configuración de la sesión
            cl.get_timeline_feed()  # Validar la sesión
            print(f"Sesión válida para @{username}.")
            return
        except Exception as e:
            print(f"Sesión persistente inválida para @{username}: {e}")
            limpiar_sesion(username)

    print(f"Iniciando nueva sesión para @{username}...")
    try:
        # Intentar iniciar sesión
        cl.login(username, password)
        print("Sesión iniciada correctamente.")
        guardar_token(username, cl.get_settings())  # Guardar configuración de la sesión
    except TwoFactorRequired as e:
        # Manejar la autenticación de dos factores
        print("Se requiere autenticación de dos factores.")
        two_factor_code = input("Introduce el código 2FA de tu aplicación autenticadora: ")
        try:
            cl.login(username, password, verification_code=two_factor_code)
            print("Autenticación de dos factores completada.")
            guardar_token(username, cl.get_settings())  # Guardar configuración de la sesión
        except Exception as e:
            print(f"Error al completar la autenticación de dos factores: {e}")
            raise
    except Exception as e:
        print(f"Error al iniciar sesión para @{username}: {e}")
        raise


def verificar_autenticacion():
    try:
        cl.get_timeline_feed()  # Validar sesión
        print("Autenticación verificada correctamente.")
        return True
    except LoginRequired:
        print("La sesión no es válida. Se requiere login.")
        return False
    except Exception as e:
        print(f"Error inesperado al verificar autenticación: {e}")
        return False


def reconectar_si_es_necesario(func):
    """
    Decorador para reintentar una función en caso de error de conexión o sesión expirada.
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except LoginRequired as e:
            print(f"Error: {e}. Reintentando...")
            if not verificar_autenticacion():
                raise Exception("No se pudo autenticar automáticamente.")
            return func(*args, **kwargs)
    return wrapper



def manejar_login(username, password):
    """
    Verifica la sesión y realiza login si es necesario.
    """
    if not verificar_autenticacion():
        print("La sesión no es válida. Intentando iniciar sesión nuevamente...")
        iniciar_sesion(username, password)


def verificar_sesion(username):
    settings = obtener_token(username)
    if settings:
        try:
            cl.set_settings(settings)
            cl.get_timeline_feed()  # Verifica la validez de la sesión
            print(f"Sesión válida para @{username}.")
            return True
        except Exception as e:
            print(f"Sesión inválida para @{username}: {e}")
            return False
    return False


def configurar_cliente():
    cl.set_device({
        "app_version": "269.0.0.18.75",
        "android_version": 26,
        "android_release": "8.0.0",
        "dpi": "480dpi",
        "resolution": "1080x1920",
        "manufacturer": "Samsung",
        "device": "Galaxy S10",
        "model": "SM-G973F",
        "cpu": "exynos9820",
        "version_code": "269185202"
    })
    cl.set_user_agent(
        "Instagram 269.0.0.18.75 Android (26/8.0.0; 480dpi; 1080x1920; Samsung; Galaxy S10; exynos9820; en_US; 269185202)"
    )
    cl.set_proxy(PROXIES["http"])
