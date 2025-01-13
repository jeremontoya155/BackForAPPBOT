from flask import Flask, render_template, request, jsonify, Response, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from config import make_celery, UPLOAD_FOLDER, LOG_FOLDER
from instagram.session import iniciar_sesion_persistente
from instagram.follow import seguir_y_mensajear
from instagrapi import Client
from database.logs import guardar_log
from database.models import db, autenticar_usuario, registrar_usuario, collection_users
from analysis.patterns import generar_sugerencia
from datetime import datetime
import os
from fpdf import FPDF
import csv
from io import StringIO




# Configuración de Flask
app = Flask(__name__)
app.secret_key = 'clave-secreta-super-segura'
# Registrar los blueprints
 

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['LOG_FOLDER'] = LOG_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['LOG_FOLDER'], exist_ok=True)

# Configuración de Celery
celery = make_celery(app)

cl = Client()

# Configura Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 


# Modelo de usuario
class User(UserMixin):
    def __init__(self, id):
        self.id = id


@login_manager.user_loader
def load_user(user_id):
    user = collection_users.find_one({"username": user_id})
    if user:
        return User(id=user["username"])
    return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"Intentando iniciar sesión para: {username}")
        
        # Validación directa de las credenciales
        if username == "Hunter" and password == "Hunter2024*":
            user = User(id=username)
            login_user(user)
            print(f"Inicio de sesión exitoso para: {username}")
            return redirect(url_for('iniciar_bot'))
        else:
            print(f"Fallo en la autenticación para: {username}")
            return render_template('login.html', error="Usuario o contraseña incorrectos")
    
    return render_template('login.html')

@app.route('/', methods=['GET', 'POST'])
def home():
    if current_user.is_authenticated:
        # Redirige al bot si el usuario ya está autenticado
        return redirect(url_for('iniciar_bot'))

    if request.method == 'POST':
        # Manejar lógica POST (por ejemplo, redirigir al login)
        print("Solicitud POST recibida en '/'")
        return redirect(url_for('login'))

    # Redirigir al login si no está autenticado
    return redirect(url_for('login'))

@app.route('/bot', methods=['GET', 'POST'])
def iniciar_bot():
    if request.method == 'GET':
        # Maneja una solicitud GET (por ejemplo, renderizar una página)
        return render_template("index.html")
    
    # Manejo actual para POST
    try:
        username = request.form.get("username")
        password = request.form.get("password")
        cuentas_competencia = request.form.get("competencia", "").split(",")

        filtros_formulario = {
            "ubicaciones": request.form.get("ubicaciones"),
            "palabras_clave": request.form.get("palabras_clave"),
            "min_publicaciones": request.form.get("min_publicaciones"),
            "min_seguidores": request.form.get("min_seguidores"),
            "tipo_cuenta": request.form.get("tipo_cuenta")
        }

        print(f"Datos recibidos: {filtros_formulario}")
        log, sugerencia = seguir_y_mensajear(cuentas_competencia, username, password, filtros_formulario)

        return render_template("index.html", success="El bot se ejecutó correctamente.", log=log, sugerencia=sugerencia)
    except Exception as e:
        if "login_required" in str(e):
            return render_template("index.html", error="Error: Es necesario iniciar sesión manualmente en Instagram.")
        else:
            print(f"Error al iniciar el bot: {e}")
            return render_template("index.html", error=f"Error inesperado: {e}")



@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            # Registrar el usuario
            success, message = registrar_usuario(username, password)
            if success:
                return redirect(url_for('login'))  # Redirige al login si el registro es exitoso
            return render_template('register.html', error=message)
        return render_template('register.html')  # Renderiza el formulario en GET
    except Exception as e:
        print(f"Error en /register: {e}")
        return render_template('register.html', error="Error interno del servidor.")


@app.route("/filtros", methods=["POST"])
def actualizar_filtros():
    try:
        # Obtener los datos del formulario desde el frontend (se asume que los filtros llegan en formato JSON)
        data = request.get_json()
        
        # Verifica qué filtros fueron recibidos
        print("Filtros recibidos:", data)  # Esto debería imprimirse en tu consola

        # Guardar los filtros en la base de datos
        db["filters"].update_one({}, {"$set": data}, upsert=True)

        return jsonify({"success": True, "message": "Filtros actualizados correctamente."})
    
    except Exception as e:
        print(f"Error al actualizar los filtros: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/estado_tarea/<task_id>")
def estado_tarea(task_id):
    tarea = celery.AsyncResult(task_id)
    if tarea.state == "PENDING":
        return {"estado": "En espera"}
    elif tarea.state == "SUCCESS":
        return {"estado": "Completada", "resultado": tarea.result}
    elif tarea.state == "FAILURE":
        return {"estado": "Fallida", "error": str(tarea.info)}
    else:
        return {"estado": tarea.state}

@app.route("/sugerencias", methods=["GET"])
def obtener_sugerencias_diarias():
    """
    Obtiene las sugerencias del día actual desde la base de datos.
    """
    try:
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        sugerencias = list(db["sugerencias_diarias"].find({"fecha": fecha_hoy}, {"_id": 0}))
        return jsonify({"success": True, "sugerencias": sugerencias})
    except Exception as e:
        print(f"Error al obtener sugerencias diarias: {e}")
        return jsonify({"success": False, "error": str(e)}), 5000


@app.route("/reportes", methods=["GET"])
def obtener_reportes():
    """
    Devuelve todos los reportes generados.
    """
    try:
        reportes = list(db["reportes"].find({}, {"_id": 0}))
        return jsonify({"success": True, "reportes": reportes})
    except Exception as e:
        print(f"Error al obtener reportes: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/descargar_reporte_pdf')
def descargar_reporte_pdf():
    """
    Genera y descarga un reporte en formato PDF.
    """
    # Crear el contenido del PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Reporte de Rendimiento", ln=True, align='C')

    # Agrega los datos del reporte (ejemplo)
    reportes = list(db["reportes"].find({}, {"_id": 0}))
    for reporte in reportes:
        pdf.cell(0, 10, txt=f"Fecha: {reporte['fecha']}", ln=True)
        pdf.cell(0, 10, txt=f"Usuarios Seguidos: {reporte['usuarios_seguidos']}", ln=True)
        pdf.cell(0, 10, txt=f"Mensajes Enviados: {reporte['mensajes_enviados']}", ln=True)
        pdf.cell(0, 10, txt=f"Respuestas Recibidas: {reporte['respuestas_recibidas']}", ln=True)
        pdf.cell(0, 10, txt=f"Tasa de Respuesta: {reporte['tasa_respuesta'] * 100:.2f}%", ln=True)
        pdf.cell(0, 10, txt=f"Seguidores Obtenidos: {reporte['seguidores_obtenidos']}", ln=True)
        pdf.cell(0, 10, txt="-----------------------------------", ln=True)

    # Devuelve el PDF como respuesta
    response = Response(pdf.output(dest='S').encode('latin1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=reporte_rendimiento.pdf'
    return response

@app.route('/descargar_reporte_csv')
def descargar_reporte_csv():
    """
    Genera y descarga un reporte en formato CSV.
    """
    # Crear el contenido del CSV
    output = StringIO()
    writer = csv.writer(output)

    # Encabezados del archivo CSV
    writer.writerow(['Fecha', 'Usuarios Seguidos', 'Mensajes Enviados', 'Respuestas Recibidas', 'Tasa de Respuesta (%)', 'Seguidores Obtenidos'])

    # Agregar los datos del reporte
    reportes = list(db["reportes"].find({}, {"_id": 0}))
    for reporte in reportes:
        writer.writerow([
            reporte['fecha'],
            reporte['usuarios_seguidos'],
            reporte['mensajes_enviados'],
            reporte['respuestas_recibidas'],
            f"{reporte['tasa_respuesta'] * 100:.2f}",
            reporte['seguidores_obtenidos']
        ])

    # Devuelve el CSV como respuesta
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=reporte_rendimiento.csv'
    return response

if __name__ == "__main__":
    app.run(debug=True)