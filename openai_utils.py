import openai
import random
from config import OPENAI_API_KEY

# Configurar la clave de API de OpenAI
openai.api_key = OPENAI_API_KEY

# Mensajes predefinidos en caso de error o como alternativa
MENSAJES_PREDEFINIDOS = [
    "Hola, ¡me encanta tu contenido!",
    "¡Qué gran trabajo estás haciendo!",
    "Saludos, sigue creando cosas tan inspiradoras."
]

def generar_mensaje_ia(username):
    print(f"Generando mensaje para @{username}...")
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente amable y profesional que genera mensajes personalizados para Instagram."},
                {"role": "user", "content": f"Escribe un mensaje amistoso y profesional para el usuario de Instagram @{username}, invitándolo a conectar."}
            ]
        )
        mensaje = response['choices'][0]['message']['content'].strip()
        print(f"Mensaje generado por IA para @{username}: {mensaje}")
        return mensaje
    except Exception as e:
        print(f"Error al generar mensaje para @{username}: {e}")
        mensaje_alternativo = random.choice(MENSAJES_PREDEFINIDOS)
        print(f"Usando mensaje alternativo: {mensaje_alternativo}")
        return mensaje_alternativo
