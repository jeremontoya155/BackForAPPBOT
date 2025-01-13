# models.py (Gestión de la base de datos con MongoDB)
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo.errors import DuplicateKeyError

# Conexión a MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Colecciones de la base de datos
collection_tokens = db["tokens"]  # Para persistencia de sesión
collection_seguidos = db["seguidos"]  # Para usuarios seguidos
collection_users = db["users"]

# Otras colecciones necesarias (ejemplo)
collection_filtros = db["filters"]  # Para guardar filtros
collection_logs = db["logs"]  # Para almacenar logs
collection_sugerencias = db["sugerencias_diarias"]  # Para sugerencias diarias

# Funciones para manejo de tokens
def guardar_token(username, settings):
    """
    Guarda la configuración de sesión (settings) en MongoDB.
    """
    collection_tokens.update_one(
        {"username": username},
        {"$set": {"settings": settings}},  # Almacena las configuraciones de sesión
        upsert=True
    )
    print(f"Configuración de sesión guardada para @{username}.")

def obtener_token(username):
    """
    Obtiene la configuración de sesión desde MongoDB.
    """
    token_doc = collection_tokens.find_one({"username": username})
    return token_doc["settings"] if token_doc else None

def guardar_usuario_seguido(username):
    try:
        if not collection_seguidos.find_one({"username": username}):
            collection_seguidos.insert_one({"username": username})
            print(f"Usuario @{username} guardado como seguido.")
        else:
            print(f"Usuario @{username} ya está registrado.")
    except Exception as e:
        print(f"Error al guardar el usuario @{username}: {e}")
        return False
    return True

def limpiar_sesion(username):
    collection_tokens.delete_one({"username": username})
    print(f"Sesión eliminada para @{username}.")


def registrar_usuario(username, password):
    """
    Registra un nuevo usuario en la base de datos.
    Retorna (True, mensaje) si el registro es exitoso, de lo contrario (False, mensaje).
    """
    try:
        # Verifica si el usuario ya existe
        if collection_users.find_one({"username": username}):
            return False, "El usuario ya existe."

        # Inserta el nuevo usuario en la base de datos
        hashed_password = generate_password_hash(password)
        collection_users.insert_one({"username": username, "password": hashed_password})
        return True, "Usuario registrado exitosamente."
    except DuplicateKeyError:
        return False, "El usuario ya está registrado."
    except Exception as e:
        print(f"Error al registrar usuario: {e}")
        return False, "Error al registrar el usuario. Inténtalo de nuevo más tarde."


def autenticar_usuario(username, password):
    """
    Verifica si las credenciales del usuario son correctas.
    """
    user = collection_users.find_one({"username": username})
    if not user or not check_password_hash(user["password"], password):
        return False
    return True