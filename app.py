import os
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
from database import conectar_bd
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)

load_dotenv()
app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
if not app.config["JWT_SECRET_KEY"]:
    raise ValueError("JWT_SECRET_KEY is not set in the environment variables.")
jwt = JWTManager(app)

# CORS
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"], supports_credentials=True)


# DECORADOR DE ROLES
def rol_requerido(rol):
    def decorator(func):
        @wraps(func)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if claims.get("rol") != rol:
                return jsonify({"mensaje": "Acceso denegado"}), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator


# PRUEBA DE CONEXIÓN
@app.route("/probar", methods=["GET"])
def probar_data():
    conec = None
    try:
        conec = conectar_bd()
        if conec and conec.is_connected():
            return jsonify({"mensaje": "//CONNECTED=!//"}), 200
        return jsonify({"mensaje": "//NO CONNECTION//"}), 500
    except Exception as error:
        print("/probar FAILED:", error)
        return jsonify({"mensaje": "//NO CONNECTION//", "error": str(error)}), 500
    finally:
        if conec and conec.is_connected():
            conec.close()


@app.route("/", methods=["GET"])
def inicio():
    return "API FUNCTIONAL"

# GESTIÓN DE USUARIOS

# REGISTRO DE USUARIO
@app.route("/api/registrousuario", methods=["POST"])
def registro_usuario():
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos:
            return jsonify({"mensaje": "JSON requerido"}), 400

        # Normalización de nombres de campos
        if "nombre_user" not in datos:
            if "nombre" in datos:
                datos["nombre_user"] = datos["nombre"]
            elif "usuario" in datos:
                datos["nombre_user"] = datos["usuario"]

        if "correo_user" not in datos:
            if "correo" in datos:
                datos["correo_user"] = datos["correo"]
            elif "email" in datos:
                datos["correo_user"] = datos["email"]

        if "contraseña" not in datos:
            if "contrasena" in datos:
                datos["contraseña"] = datos["contrasena"]
            elif "password" in datos:
                datos["contraseña"] = datos["password"]

        # Validación de campos obligatorios
        campos = ["nombre_user", "correo_user", "contraseña"]
        for campo in campos:
            if campo not in datos or datos[campo] is None or str(datos[campo]).strip() == "":
                return jsonify({"mensaje": f"CAMPO VACÍO: {campo}"}), 400

        # Validación de contraseña
        contraseña_texto = str(datos["contraseña"]).strip()
        if len(contraseña_texto) < 8 or len(contraseña_texto) > 15:
            return jsonify({"mensaje": "LA CONTRASEÑA DEBE TENER ENTRE 8 Y 15 CARACTERES"}), 400

        contraseña_encriptada = generate_password_hash(contraseña_texto)

        # Rol por defecto 'Aprendiz'
        rol = datos.get("rol")
        if not rol or str(rol).strip() == "" or rol not in ["Aprendiz", "Reclutador"]:
            rol = "Aprendiz"

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)

        correo_limpio = datos["correo_user"].strip().lower()
        nombre_limpio = datos["nombre_user"].strip()

        # Verificar correo existente
        cursor.execute("SELECT id_USER FROM USUARIO WHERE correo_user = %s", (correo_limpio,))
        if cursor.fetchone():
            return jsonify({"mensaje": "CORREO YA REGISTRADO"}), 409

        # Verificar nombre de usuario existente
        cursor.execute("SELECT id_USER FROM USUARIO WHERE nombre_user = %s", (nombre_limpio,))
        if cursor.fetchone():
            return jsonify({"mensaje": "USUARIO YA REGISTRADO"}), 409

        # Insertar usuario
        sql = "INSERT INTO USUARIO (nombre_user, correo_user, contraseña, rol) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (nombre_limpio, correo_limpio, contraseña_encriptada, rol))
        conec.commit()

        id_generado = cursor.lastrowid
        return jsonify({"mensaje": "USUARIO REGISTRADO", "id": id_generado, "id_USER": id_generado}), 201

    except Exception as error:
        print("ERROR REGISTRANDO USUARIO:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# LOGIN DE USUARIO
@app.route("/api/login", methods=["POST"])
def login():
    datos = request.get_json(silent=True)
    if not datos:
        return jsonify({"mensaje": "Datos Incompletos"}), 400

    correo = (datos.get("correo_user") or datos.get("correo") or datos.get("email") or "").strip().lower()
    contraseña = datos.get("contraseña") or datos.get("contrasena") or datos.get("password")

    if not correo or not contraseña:
        return jsonify({"mensaje": "Correo y Contraseña Requeridos"}), 400

    conexion = None
    cursor = None
    try:
        conexion = conectar_bd()
        if conexion is None or not conexion.is_connected():
            return jsonify({"mensaje": "Error de conexión a la base de datos"}), 500

        cursor = conexion.cursor(dictionary=True)
        sql = "SELECT id_USER, nombre_user, correo_user, contraseña, rol, estado FROM USUARIO WHERE correo_user = %s"
        cursor.execute(sql, (correo,))
        usuario = cursor.fetchone()

        if not usuario:
            return jsonify({"mensaje": "Usuario No Encontrado"}), 404

        if not usuario.get("estado"):
            return jsonify({"mensaje": "Usuario Inactivo"}), 403

        if not check_password_hash(usuario["contraseña"], contraseña):
            return jsonify({"mensaje": "Contraseña Incorrecta"}), 401

        token = create_access_token(
            identity=str(usuario["id_USER"]),
            additional_claims={"rol": usuario["rol"]},
        )

        return jsonify({
            "mensaje": "Inicio de Sesión Exitoso",
            "token": token,
            "usuario": {
                "id": usuario["id_USER"],
                "id_USER": usuario["id_USER"],
                "nombre": usuario["nombre_user"],
                "correo": usuario["correo_user"],
                "rol": usuario["rol"],
            },
        }), 200

    except Exception as error:
        print("ERROR INICIANDO SESIÓN:", error)
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conexion and conexion.is_connected():
            conexion.close()

# HOJAS DE VIDA

# REGISTRAR HOJA DE VIDA
@app.route("/api/registrohv", methods=["POST"])
@jwt_required()
def registrohvida():
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos:
            return jsonify({"mensaje": "JSON requerido"}), 400

        usuario_id = int(get_jwt_identity())

        campos = ["nombre", "edad", "ciudad", "correo", "programa", "ficha", "jornada"]
        for campo in campos:
            if campo not in datos or datos[campo] is None or str(datos[campo]).strip() == "":
                return jsonify({"mensaje": f"CAMPO VACÍO: {campo}"}), 400

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)

        # Verificar si el usuario ya tiene hoja de vida registrada
        cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE usuario_ID = %s", (usuario_id,))
        if cursor.fetchone():
            return jsonify({"mensaje": "EL USUARIO YA TIENE UNA HOJA DE VIDA REGISTRADA"}), 409

        # Verificar correo único en hojas de vida
        cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE correo = %s", (datos["correo"].strip().lower(),))
        if cursor.fetchone():
            return jsonify({"mensaje": "CORREO YA REGISTRADO"}), 409

        foto_valor = datos.get("foto") or datos.get("fotografia")

        sql = """INSERT INTO HOJAS_VIDA (usuario_ID, nombre, edad, ciudad, correo, foto, programa, ficha, jornada) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        valores = (
            usuario_id,
            datos["nombre"].strip(),
            datos["edad"],
            datos["ciudad"].strip(),
            datos["correo"].strip().lower(),
            foto_valor,
            datos["programa"].strip(),
            datos["ficha"].strip(),
            datos["jornada"].strip(),
        )

        cursor.execute(sql, valores)
        conec.commit()
        id_generado = cursor.lastrowid
        return jsonify({"mensaje": "HOJA DE VIDA CREADA", "id": id_generado, "id_HV": id_generado}), 201

    except Exception as error:
        print("ERROR REGISTRANDO HOJA DE VIDA:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# HELPER: CARGAR DETALLES DE HOJA DE VIDA (Estudios, Cursos, Experiencias, Habilidades)
def cargar_detalles_hoja_vida(cursor, id_hv):
    # Consultar estudios
    cursor.execute(
        "SELECT id_EST, id_EST AS id, hoja_vida_id, nivel, institucion, titulo, anio_graduacion FROM ESTUDIOS WHERE hoja_vida_id = %s",
        (id_hv,)
    )
    estudios = cursor.fetchall()

    # Consultar cursos
    cursor.execute(
        "SELECT id_CUR, id_CUR AS id, hoja_vida_id, nombre FROM CURSOS WHERE hoja_vida_id = %s",
        (id_hv,)
    )
    cursos = cursor.fetchall()

    # Consultar experiencias y sus habilidades
    cursor.execute(
        "SELECT id_EXP, id_EXP AS id, hoja_vida_id, empresa, cargo, tiempo, funciones FROM EXPERIENCIAS WHERE hoja_vida_id = %s",
        (id_hv,)
    )
    experiencias = cursor.fetchall()

    todas_habilidades = []
    for exp in experiencias:
        exp_id = exp.get("id_EXP") or exp.get("id")
        cursor.execute(
            "SELECT id_HAB, id_HAB AS id, experiencia_id, nombre FROM HABILIDADES WHERE experiencia_id = %s",
            (exp_id,)
        )
        habs = cursor.fetchall()
        exp["habilidades"] = habs
        for h in habs:
            todas_habilidades.append({
                "id_HAB": h.get("id_HAB"),
                "id": h.get("id"),
                "nombre": h.get("nombre"),
                "experiencia_id": exp_id
            })

    return estudios, cursos, experiencias, todas_habilidades


# CONSULTAR TODAS LAS HOJAS DE VIDA (Sólo Reclutadores)
@app.route("/api/hojasdevida", methods=["GET"])
@app.route("/api/hojasvida", methods=["GET"])
@rol_requerido("Reclutador")
def obtener_hojasvida():
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(dictionary=True)
        cursor.execute("SELECT id_HV, id_HV AS id, usuario_ID, nombre, edad, ciudad, correo, foto, foto AS fotografia, programa, ficha, jornada FROM HOJAS_VIDA")
        hojasdevida = cursor.fetchall()

        # Adjuntar información detallada a cada hoja de vida
        for hoja in hojasdevida:
            id_hv = hoja.get("id_HV") or hoja.get("id")
            estudios, cursos, experiencias, habilidades = cargar_detalles_hoja_vida(cursor, id_hv)
            hoja["estudios"] = estudios
            hoja["cursos"] = cursos
            hoja["experiencias"] = experiencias
            hoja["habilidades"] = habilidades

        return jsonify({"hojas_vida": hojasdevida}), 200
    except Exception as error:
        print("ERROR CONSULTANDO HOJAS DE VIDA:", error)
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# CONSULTAR HOJA DE VIDA POR ID
@app.route("/api/hojasdevida/<int:id>", methods=["GET"])
@app.route("/api/hojasvida/<int:id>", methods=["GET"])
def obtener_hojasvidaid(id):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(dictionary=True)
        cursor.execute("SELECT id_HV, id_HV AS id, usuario_ID, nombre, edad, ciudad, correo, foto, foto AS fotografia, programa, ficha, jornada FROM HOJAS_VIDA WHERE id_HV = %s", (id,))
        hoja = cursor.fetchone()

        if hoja is None:
            return jsonify({"mensaje": "HOJA DE VIDA NO ENCONTRADA"}), 404

        estudios, cursos, experiencias, habilidades = cargar_detalles_hoja_vida(cursor, id)
        hoja["estudios"] = estudios
        hoja["cursos"] = cursos
        hoja["experiencias"] = experiencias
        hoja["habilidades"] = habilidades

        return jsonify(hoja), 200
    except Exception as error:
        print("ERROR OBTENIENDO HOJA DE VIDA:", error)
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# ACTUALIZAR HOJA DE VIDA
@app.route("/api/actualizarhv/<int:id>", methods=["PUT"])
@jwt_required()
def actualizar_hv(id):
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos:
            return jsonify({"mensaje": "JSON requerido"}), 400

        campos = ["nombre", "edad", "ciudad", "correo", "programa", "ficha", "jornada"]
        for campo in campos:
            if campo not in datos or datos[campo] is None or str(datos[campo]).strip() == "":
                return jsonify({"mensaje": f"CAMPO VACÍO: {campo}"}), 400

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)

        cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE id_HV = %s", (id,))
        if cursor.fetchone() is None:
            return jsonify({"mensaje": "HOJA DE VIDA NO ENCONTRADA"}), 404

        correo_limpio = datos["correo"].strip().lower()
        cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE correo = %s AND id_HV != %s", (correo_limpio, id))
        if cursor.fetchone() is not None:
            return jsonify({"mensaje": "CORREO YA EXISTENTE"}), 409

        foto_valor = datos.get("foto") or datos.get("fotografia")

        sql = """UPDATE HOJAS_VIDA SET nombre = %s, edad = %s, ciudad = %s, correo = %s, foto = %s, programa = %s, ficha = %s, jornada = %s WHERE id_HV = %s"""
        valores = (
            datos["nombre"].strip(),
            datos["edad"],
            datos["ciudad"].strip(),
            correo_limpio,
            foto_valor,
            datos["programa"].strip(),
            datos["ficha"].strip(),
            datos["jornada"].strip(),
            id,
        )

        cursor.execute(sql, valores)
        conec.commit()
        return jsonify({"mensaje": "HOJA DE VIDA ACTUALIZADA", "id": id, "id_HV": id}), 200

    except Exception as error:
        print("ERROR ACTUALIZANDO HOJA DE VIDA:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# ELIMINAR HOJA DE VIDA
@app.route("/api/eliminarhv/<int:id>", methods=["DELETE"])
@jwt_required()
def eliminar_hv(id):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)

        cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE id_HV = %s", (id,))
        if cursor.fetchone() is None:
            return jsonify({"mensaje": "HOJA DE VIDA NO ENCONTRADA"}), 404

        cursor.execute("DELETE FROM HOJAS_VIDA WHERE id_HV = %s", (id,))
        conec.commit()

        return jsonify({"mensaje": "HOJA DE VIDA ELIMINADA", "id": id, "id_HV": id}), 200

    except Exception as error:
        print("ERROR ELIMINANDO HOJA DE VIDA:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()

# ESTUDIOS
# REGISTRAR ESTUDIO
@app.route("/api/hojasvida/<int:id_hv>/estudios", methods=["POST"])
@app.route("/api/HOJAS_VIDA/<int:id_hv>/estudios", methods=["POST"])
def registrar_estudio(id_hv):
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos:
            return jsonify({"mensaje": "JSON requerido"}), 400

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)

        cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE id_HV = %s", (id_hv,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "HOJA DE VIDA INEXISTENTE"}), 404

        sql = """INSERT INTO ESTUDIOS (hoja_vida_id, nivel, institucion, titulo, anio_graduacion) VALUES (%s, %s, %s, %s, %s)"""
        valores = (
            id_hv,
            datos.get("nivel"),
            datos.get("institucion"),
            datos.get("titulo"),
            datos.get("anio_graduacion"),
        )

        cursor.execute(sql, valores)
        conec.commit()
        id_estudio = cursor.lastrowid

        return jsonify({
            "mensaje": "ESTUDIO REGISTRADO",
            "id_estudio": id_estudio,
            "id_EST": id_estudio,
            "hoja_vida_id": id_hv,
        }), 201

    except Exception as error:
        print("ERROR REGISTRANDO ESTUDIO:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# LISTAR ESTUDIOS DE UNA HOJA DE VIDA
@app.route("/api/hojasvida/<int:id_hv>/estudios", methods=["GET"])
@app.route("/api/HOJAS_VIDA/<int:id_hv>/estudios", methods=["GET"])
def listar_estudios_hoja_vida(id_hv):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(dictionary=True)

        cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE id_HV = %s", (id_hv,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "HOJA DE VIDA INEXISTENTE"}), 404

        cursor.execute("SELECT id_EST, id_EST AS id, hoja_vida_id, nivel, institucion, titulo, anio_graduacion FROM ESTUDIOS WHERE hoja_vida_id = %s", (id_hv,))
        estudios = cursor.fetchall()

        return jsonify({"hoja_vida_id": id_hv, "estudios": estudios}), 200

    except Exception as error:
        print("ERROR LISTANDO ESTUDIOS:", error)
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# CONSULTAR ESTUDIO POR ID
@app.route("/api/estudios/<int:id_est>", methods=["GET"])
def obtener_estudio(id_est):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(dictionary=True)
        cursor.execute("SELECT id_EST, id_EST AS id, hoja_vida_id, nivel, institucion, titulo, anio_graduacion FROM ESTUDIOS WHERE id_EST = %s", (id_est,))
        estudio = cursor.fetchone()

        if not estudio:
            return jsonify({"mensaje": "ESTUDIO NO ENCONTRADO"}), 404

        return jsonify({"estudio": estudio}), 200

    except Exception as error:
        print("ERROR OBTENIENDO ESTUDIO:", error)
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# ACTUALIZAR ESTUDIO
@app.route("/api/estudios/<int:id_est>", methods=["PUT"])
def actualizar_estudio(id_est):
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos:
            return jsonify({"mensaje": "JSON requerido"}), 400

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)
        cursor.execute("SELECT id_EST FROM ESTUDIOS WHERE id_EST = %s", (id_est,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "ESTUDIO INEXISTENTE"}), 404

        sql = """UPDATE ESTUDIOS SET nivel = %s, institucion = %s, titulo = %s, anio_graduacion = %s WHERE id_EST = %s"""
        valores = (
            datos.get("nivel"),
            datos.get("institucion"),
            datos.get("titulo"),
            datos.get("anio_graduacion"),
            id_est,
        )

        cursor.execute(sql, valores)
        conec.commit()

        return jsonify({"mensaje": "ESTUDIO ACTUALIZADO", "id_estudio": id_est, "id_EST": id_est}), 200

    except Exception as error:
        print("ERROR ACTUALIZANDO ESTUDIO:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# ELIMINAR ESTUDIO
@app.route("/api/estudios/<int:id_est>", methods=["DELETE"])
def eliminar_estudio(id_est):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)
        cursor.execute("SELECT id_EST FROM ESTUDIOS WHERE id_EST = %s", (id_est,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "ESTUDIO INEXISTENTE"}), 404

        cursor.execute("DELETE FROM ESTUDIOS WHERE id_EST = %s", (id_est,))
        conec.commit()

        return jsonify({"mensaje": "ESTUDIO ELIMINADO", "id_estudio": id_est, "id_EST": id_est}), 200

    except Exception as error:
        print("ERROR ELIMINANDO ESTUDIO:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# EXPERIENCIAS
# REGISTRAR EXPERIENCIA
@app.route("/api/hojasvida/<int:id_hv>/experiencias", methods=["POST"])
@app.route("/api/HOJAS_VIDA/<int:id_hv>/EXPERIENCIAS", methods=["POST"])
def registrar_experiencia(id_hv):
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos:
            return jsonify({"mensaje": "JSON requerido"}), 400

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)
        cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE id_HV = %s", (id_hv,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "HOJA DE VIDA INEXISTENTE"}), 404

        sql = """INSERT INTO EXPERIENCIAS (hoja_vida_id, empresa, cargo, tiempo, funciones) VALUES (%s, %s, %s, %s, %s)"""
        valores = (
            id_hv,
            datos.get("empresa"),
            datos.get("cargo"),
            datos.get("tiempo"),
            datos.get("funciones"),
        )

        cursor.execute(sql, valores)
        conec.commit()
        id_experiencia = cursor.lastrowid

        return jsonify({
            "mensaje": "EXPERIENCIA REGISTRADA",
            "id_experiencia": id_experiencia,
            "id_EXP": id_experiencia,
            "hoja_vida_id": id_hv,
        }), 201

    except Exception as error:
        print("ERROR REGISTRANDO EXPERIENCIA:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# LISTAR EXPERIENCIAS DE UNA HOJA DE VIDA
@app.route("/api/hojasvida/<int:id_hv>/experiencias", methods=["GET"])
def listar_experiencias_hoja_vida(id_hv):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(dictionary=True)
        cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE id_HV = %s", (id_hv,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "HOJA DE VIDA INEXISTENTE"}), 404

        cursor.execute("SELECT id_EXP, id_EXP AS id, hoja_vida_id, empresa, cargo, tiempo, funciones FROM EXPERIENCIAS WHERE hoja_vida_id = %s", (id_hv,))
        resultado = cursor.fetchall()

        return jsonify({"hoja_vida_id": id_hv, "experiencias": resultado}), 200

    except Exception as error:
        print("ERROR LISTANDO EXPERIENCIAS:", error)
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# CONSULTAR EXPERIENCIA POR ID
@app.route("/api/experiencias/<int:id_exp>", methods=["GET"])
def obtener_experiencia(id_exp):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(dictionary=True)
        cursor.execute("SELECT id_EXP, id_EXP AS id, hoja_vida_id, empresa, cargo, tiempo, funciones FROM EXPERIENCIAS WHERE id_EXP = %s", (id_exp,))
        experiencia = cursor.fetchone()

        if not experiencia:
            return jsonify({"mensaje": "EXPERIENCIA NO ENCONTRADA"}), 404
        return jsonify({"experiencia": experiencia}), 200

    except Exception as error:
        print("ERROR OBTENIENDO EXPERIENCIA:", error)
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# ACTUALIZAR EXPERIENCIA
@app.route("/api/experiencias/<int:id_exp>", methods=["PUT"])
def actualizar_experiencia(id_exp):
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos:
            return jsonify({"mensaje": "JSON requerido"}), 400

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)
        cursor.execute("SELECT id_EXP FROM EXPERIENCIAS WHERE id_EXP = %s", (id_exp,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "EXPERIENCIA INEXISTENTE"}), 404

        sql = """UPDATE EXPERIENCIAS SET empresa = %s, cargo = %s, tiempo = %s, funciones = %s WHERE id_EXP = %s"""
        valores = (
            datos.get("empresa"),
            datos.get("cargo"),
            datos.get("tiempo"),
            datos.get("funciones"),
            id_exp,
        )

        cursor.execute(sql, valores)
        conec.commit()

        return jsonify({"mensaje": "EXPERIENCIA ACTUALIZADA", "id_experiencia": id_exp, "id_EXP": id_exp}), 200

    except Exception as error:
        print("ERROR ACTUALIZANDO EXPERIENCIA:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# ELIMINAR EXPERIENCIA
@app.route("/api/experiencias/<int:id_exp>", methods=["DELETE"])
def eliminar_experiencia(id_exp):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)
        cursor.execute("SELECT id_EXP FROM EXPERIENCIAS WHERE id_EXP = %s", (id_exp,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "EXPERIENCIA INEXISTENTE"}), 404

        cursor.execute("DELETE FROM EXPERIENCIAS WHERE id_EXP = %s", (id_exp,))
        conec.commit()

        return jsonify({"mensaje": "EXPERIENCIA ELIMINADA", "id_experiencia": id_exp, "id_EXP": id_exp}), 200

    except Exception as error:
        print("ERROR ELIMINANDO EXPERIENCIA:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()

# HABILIDADES
# REGISTRAR HABILIDAD
@app.route("/api/experiencias/<int:id_exp>/habilidades", methods=["POST"])
@app.route("/api/HABILIDADES/<int:id_exp>", methods=["POST"])
def registrar_habilidad(id_exp):
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos or "nombre" not in datos or not str(datos["nombre"]).strip():
            return jsonify({"mensaje": "NOMBRE FALTANTE"}), 400

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)
        cursor.execute("SELECT id_EXP FROM EXPERIENCIAS WHERE id_EXP = %s", (id_exp,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "EXPERIENCIA INEXISTENTE"}), 404

        sql = "INSERT INTO HABILIDADES (experiencia_id, nombre) VALUES (%s, %s)"
        cursor.execute(sql, (id_exp, datos.get("nombre").strip()))
        conec.commit()
        id_habilidad = cursor.lastrowid

        return jsonify({
            "mensaje": "HABILIDAD REGISTRADA",
            "id_habilidad": id_habilidad,
            "id_HAB": id_habilidad,
            "experiencia_id": id_exp,
        }), 201

    except Exception as error:
        print("ERROR REGISTRANDO HABILIDAD:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# LISTAR HABILIDADES DE UNA EXPERIENCIA
@app.route("/api/experiencias/<int:id_exp>/habilidades", methods=["GET"])
def listar_habilidades_experiencia(id_exp):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(dictionary=True)
        cursor.execute("SELECT id_EXP FROM EXPERIENCIAS WHERE id_EXP = %s", (id_exp,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "EXPERIENCIA INEXISTENTE"}), 404

        cursor.execute("SELECT id_HAB, id_HAB AS id, experiencia_id, nombre FROM HABILIDADES WHERE experiencia_id = %s", (id_exp,))
        resultado = cursor.fetchall()

        return jsonify({"experiencia_id": id_exp, "habilidades": resultado}), 200

    except Exception as error:
        print("ERROR LISTANDO HABILIDADES:", error)
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# ACTUALIZAR HABILIDAD
@app.route("/api/habilidades/<int:id_hab>", methods=["PUT"])
def actualizar_habilidad(id_hab):
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos or "nombre" not in datos or not str(datos["nombre"]).strip():
            return jsonify({"mensaje": "NOMBRE FALTANTE"}), 400

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)
        cursor.execute("SELECT id_HAB FROM HABILIDADES WHERE id_HAB = %s", (id_hab,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "HABILIDAD INEXISTENTE"}), 404

        sql = "UPDATE HABILIDADES SET nombre = %s WHERE id_HAB = %s"
        cursor.execute(sql, (datos.get("nombre").strip(), id_hab))
        conec.commit()

        return jsonify({"mensaje": "HABILIDAD ACTUALIZADA", "id_habilidad": id_hab, "id_HAB": id_hab}), 200

    except Exception as error:
        print("ERROR ACTUALIZANDO HABILIDAD:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# ELIMINAR HABILIDAD
@app.route("/api/habilidades/<int:id_hab>", methods=["DELETE"])
def eliminar_habilidad(id_hab):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)
        cursor.execute("SELECT id_HAB FROM HABILIDADES WHERE id_HAB = %s", (id_hab,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "HABILIDAD INEXISTENTE"}), 404

        sql = "DELETE FROM HABILIDADES WHERE id_HAB = %s"
        cursor.execute(sql, (id_hab,))
        conec.commit()

        return jsonify({"mensaje": "HABILIDAD ELIMINADA", "id_habilidad": id_hab, "id_HAB": id_hab}), 200

    except Exception as error:
        print("ERROR ELIMINANDO HABILIDAD:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()

# CURSOS
# REGISTRAR CURSO
@app.route("/api/hojasvida/<int:id_hv>/cursos", methods=["POST"])
@app.route("/api/CURSOS/<int:id_hv>", methods=["POST"])
def registrar_curso(id_hv):
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos or "nombre" not in datos or not str(datos["nombre"]).strip():
            return jsonify({"mensaje": "NOMBRE VACÍO"}), 400

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)
        cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE id_HV = %s", (id_hv,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "HOJA DE VIDA INEXISTENTE"}), 404

        sql = "INSERT INTO CURSOS (hoja_vida_id, nombre) VALUES (%s, %s)"
        cursor.execute(sql, (id_hv, datos.get("nombre").strip()))
        conec.commit()
        id_curso = cursor.lastrowid

        return jsonify({
            "mensaje": "CURSO REGISTRADO",
            "id_curso": id_curso,
            "id_CUR": id_curso,
            "hoja_vida_id": id_hv,
        }), 201

    except Exception as error:
        print("ERROR REGISTRANDO CURSO:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# LISTAR CURSOS DE UNA HOJA DE VIDA
@app.route("/api/hojasvida/<int:id_hv>/cursos", methods=["GET"])
def listar_cursos_hoja_vida(id_hv):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(dictionary=True)
        cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE id_HV = %s", (id_hv,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "HOJA DE VIDA INEXISTENTE"}), 404

        cursor.execute("SELECT id_CUR, id_CUR AS id, hoja_vida_id, nombre FROM CURSOS WHERE hoja_vida_id = %s", (id_hv,))
        resultado = cursor.fetchall()

        return jsonify({"hoja_vida_id": id_hv, "cursos": resultado}), 200

    except Exception as error:
        print("ERROR LISTANDO CURSOS:", error)
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# CONSULTAR CURSO POR ID
@app.route("/api/cursos/<int:id_cur>", methods=["GET"])
def obtener_curso(id_cur):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(dictionary=True)
        cursor.execute("SELECT id_CUR, id_CUR AS id, hoja_vida_id, nombre FROM CURSOS WHERE id_CUR = %s", (id_cur,))
        curso = cursor.fetchone()

        if not curso:
            return jsonify({"mensaje": "CURSO NO ENCONTRADO"}), 404
        return jsonify({"curso": curso}), 200

    except Exception as error:
        print("ERROR OBTENIENDO CURSO:", error)
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# ACTUALIZAR CURSO
@app.route("/api/cursos/<int:id_cur>", methods=["PUT"])
def actualizar_curso(id_cur):
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos or "nombre" not in datos or not str(datos["nombre"]).strip():
            return jsonify({"mensaje": "NOMBRE VACÍO"}), 400

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)
        cursor.execute("SELECT id_CUR FROM CURSOS WHERE id_CUR = %s", (id_cur,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "CURSO INEXISTENTE"}), 404

        sql = "UPDATE CURSOS SET nombre = %s WHERE id_CUR = %s"
        cursor.execute(sql, (datos.get("nombre").strip(), id_cur))
        conec.commit()

        return jsonify({"mensaje": "CURSO ACTUALIZADO", "id_curso": id_cur, "id_CUR": id_cur}), 200

    except Exception as error:
        print("ERROR ACTUALIZANDO CURSO:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# ELIMINAR CURSO
@app.route("/api/cursos/<int:id_cur>", methods=["DELETE"])
def eliminar_curso(id_cur):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(buffered=True)
        cursor.execute("SELECT id_CUR FROM CURSOS WHERE id_CUR = %s", (id_cur,))
        if not cursor.fetchone():
            return jsonify({"mensaje": "CURSO INEXISTENTE"}), 404

        sql = "DELETE FROM CURSOS WHERE id_CUR = %s"
        cursor.execute(sql, (id_cur,))
        conec.commit()

        return jsonify({"mensaje": "CURSO ELIMINADO", "id_curso": id_cur, "id_CUR": id_cur}), 200

    except Exception as error:
        print("ERROR ELIMINANDO CURSO:", error)
        if conec and conec.is_connected():
            conec.rollback()
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# HOJA DE VIDA COMPLETA
# CONSULTA HOJA DE VIDA COMPLETA
@app.route("/api/HOJAS_VIDA/<int:id>/completa", methods=["GET"])
@app.route("/api/hojasvida/<int:id>/completa", methods=["GET"])
def consultar_hoja_vida_completa(id):
    conec = None
    cursor = None
    try:
        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return jsonify({"mensaje": "//NO CONNECTION//"}), 500

        cursor = conec.cursor(dictionary=True)

        cursor.execute("SELECT id_HV, id_HV AS id, usuario_ID, nombre, edad, ciudad, correo, foto, foto AS fotografia, programa, ficha, jornada FROM HOJAS_VIDA WHERE id_HV = %s", (id,))
        hoja_vida = cursor.fetchone()

        if hoja_vida is None:
            return jsonify({"mensaje": "HOJA DE VIDA NO ENCONTRADA"}), 404

        estudios, cursos, experiencias, habilidades = cargar_detalles_hoja_vida(cursor, id)
        hoja_vida["estudios"] = estudios
        hoja_vida["cursos"] = cursos
        hoja_vida["experiencias"] = experiencias
        hoja_vida["habilidades"] = habilidades

        return jsonify({
            "hoja_de_vida": hoja_vida,
            "estudios": estudios,
            "cursos": cursos,
            "experiencias": experiencias,
            "habilidades": habilidades,
        }), 200

    except Exception as error:
        print("ERROR CONSULTANDO HOJA DE VIDA COMPLETA:", error)
        return jsonify({"mensaje": "SERVER FAILURE", "error": str(error)}), 500
    finally:
        if cursor:
            cursor.close()
        if conec and conec.is_connected():
            conec.close()


# INICIO DE LA APLICACIÓN
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
