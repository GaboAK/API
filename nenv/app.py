from flask import Flask, request, jsonify
from flask_cors import CORS
from database import conectar_bd
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

#PAL CORS
CORS(app, origins=["http://localhost:5173"])

#PRUEBA
@app.route("/probar", methods=["GET"])
def probar_data():
    conec = None
    try:
        conec = conectar_bd()
        if conec and conec.is_connected():
            return {"mensaje": "//CONNECTED=!//"}, 200
        return {"mensaje": "//NO CONNECTION//"}, 500
    except Exception as error:
        print("/probar FAILED", error)
        return {
            "mensaje": "//NO CONNECTION//",
            "error": str(error),
        }, 500
    finally:
        if conec and conec.is_connected():
            conec.close()


@app.route("/", methods=["GET"])
def inicio():
    return "API FUNCTIONAL"

#//10 Noviembre 2026
#REGISTRO USUARIO
@app.route("/api/registrousuario", methods=["POST"])
def registro_usuario():
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos:
            return {"mensaje": "JSON UNIQUE"}, 400

        #NOdRMALIZAR
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

        #Xin Dato Vacio
        campos = [
            "nombre_user",
            "correo_user",
            "contraseña",
        ]
        for campo in campos:
            if campo not in datos or datos[campo] is None or str(datos[campo]).strip() == "":
                return {"mensaje": f"CAMPO VACÍO: {campo}"}, 400

        #CONTRASEÑA Y REQUISITOS
        contrasena_texto = str(datos["contraseña"]).strip()
        if len(contrasena_texto) < 8 or len(contrasena_texto) > 15:
            return {
                "mensaje": "LA CONTRASEÑA DEBE TENER ENTRE 8 Y 15 CARACTERES"
            }, 400
    #
        contraseña_encriptada = generate_password_hash(contrasena_texto)

        #ROL DEFECTO "APRENDIZ
        rol = datos.get("rol")
        if not rol or str(rol).strip() == "":
            rol = "Aprendiz"
        elif rol not in ["Aprendiz", "Reclutador"]:
            rol = "Aprendiz"

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return {"mensaje": "//NO CONNECTION//"}, 500

        cursor = conec.cursor(buffered=True)

        #CORREO Y REGISTRO 
        # 
        cursor.execute(
            "SELECT id_USER FROM USUARIO WHERE correo_user = %s",
            (datos["correo_user"].strip(),),
        )
        if cursor.fetchone():
            return {"mensaje": "CORREO YA REGISTRADO"}, 409

        #VERIFICAR
        cursor.execute(
            "SELECT id_USER FROM USUARIO WHERE nombre_user = %s",
            (datos["nombre_user"].strip(),),
        )
        if cursor.fetchone():
            return {"mensaje": "USUARIO YA REGISTRADO"}, 409

        #REGISTRAR
        #AGREGAR USUARIO
        sql = """INSERT INTO USUARIO (nombre_user, correo_user, contraseña, rol) VALUES (%s, %s, %s, %s)"""
        valores = (
            datos["nombre_user"].strip(),
            datos["correo_user"].strip(),
            contraseña_encriptada,
            rol,
        )

        cursor.execute(sql, valores)
        conec.commit()
        id_generado = cursor.lastrowid
        return {"mensaje": "USUARIO REGISTRADO", "id": id_generado}, 201

    except Exception as error:
        print("ERROR REGISTRANDO USUARIO:", error)
        if conec:
            try:
                conec.rollback()
            except Exception:
                pass
        return {
            "mensaje": "SERVER FAILURE",
            "error": str(error),
        }, 500
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conec and conec.is_connected():
            try:
                conec.close()
            except Exception:
                pass

@app.route("/api/login", methods=["POST"])
def login():
    pass

#/////////////////////////////////////////////////////
@app.route("/api/registrohv", methods=["POST"])
def registrohvida():
    conec = None
    cursor = None
    try:
        datos = request.get_json(silent=True)
        if not datos:
            return {"mensaje": "JSON UNIQUE"}, 400

        campos = [
            "nombre",
            "edad",
            "ciudad",
            "correo",
            "programa",
            "ficha",
            "jornada",
        ]
        for campo in campos:
            if campo not in datos:
                return {"mensaje": f"CAMPO VACÍO: {campo}"}, 400

        conec = conectar_bd()
        if conec is None or not conec.is_connected():
            return {"mensaje": "//NO CONNECTION//"}, 500

        cursor = conec.cursor(buffered=True)

        #VERIFICAR CORREO
        cursor.execute(
            "SELECT id FROM hojas_vida WHERE correo = %s", (datos["correo"],)
        )
        if cursor.fetchone():
            return {"mensaje": "CORREO YA REGISTRADO"}, 409

        #AGREGAR HV
        sql = """INSERT INTO hojas_vida (nombre, edad, ciudad, correo, fotografia, programa, ficha, jornada) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        valores = (
            datos["nombre"],
            datos["edad"],
            datos["ciudad"],
            datos["correo"],
            datos.get("fotografia") or datos.get("foto"),
            datos["programa"],
            datos["ficha"],
            datos["jornada"],
        )

        cursor.execute(sql, valores)
        conec.commit()
        id_generado = cursor.lastrowid
        return {"mensaje": "HOJA DE VIDA CREADA", "id": id_generado}, 201

    except Exception as error:
        print("ERROR REGISTRANDO HOJA DE VIDA:", error)
        if conec:
            try:
                conec.rollback()
            except Exception:
                pass
        return {
            "mensaje": "SERVER FAILURE",
            "error": str(error),
        }, 500
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conec and conec.is_connected():
            try:
                conec.close()
            except Exception:
                pass

#HV
@app.route("/api/hojasdevida", methods=["GET"])
@app.route("/api/hojasvida", methods=["GET"])

#CONSULTA HV
def obtener_hojasvida():
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)

    cursor.execute("SELECT * FROM hojas_vida")
    hojasdevida = cursor.fetchall()

    cursor.close()
    conec.close()
    return jsonify({"hojas_vida": hojasdevida}), 200

#HV POR ID
@app.route("/api/hojasdevida/<int:id>", methods=["GET"])
def obtener_hojasvidaid(id):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)

    cursor.execute("SELECT * FROM hojas_vida WHERE id = %s", (id,))
    hoja = cursor.fetchone()

    cursor.close()
    conec.close()

    if hoja is None:
        return {"mensaje": "HOJA DE VIDA NO ENCONTRADA"}, 404
    return hoja, 200

#ACTUALIZAR HV
@app.route("/api/actualizarhv/<int:id>", methods=["PUT"])
def actualizar_hv(id):
    datos = request.get_json()
    if not datos:
        return {"mensaje": "JSON UNIQUE"}, 400

    campos = [
        "nombre",
        "edad",
        "ciudad",
        "correo",
        "programa",
        "ficha",
        "jornada",
    ]
    for campo in campos:
        if campo not in datos:
            return {"mensaje": f"CAMPO VACÍO: {campo}"}, 400

    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM hojas_vida WHERE id = %s", (id,))
    if cursor.fetchone() is None:
        cursor.close()
        conec.close()
        return {"mensaje": "HOJA DE VIDA NO ENCONTRADA"}, 404

    cursor.execute(
        "SELECT id FROM hojas_vida WHERE correo = %s AND id != %s",
        (datos["correo"], id),
    )
    if cursor.fetchone() is not None:
        cursor.close()
        conec.close()
        return {
            "mensaje": "CORREO YA EXISTENTE"
        }, 409

    sql = """UPDATE hojas_vida SET nombre = %s, edad = %s, ciudad = %s, correo = %s, fotografia = %s, programa = %s, ficha = %s, jornada = %s WHERE id = %s"""
    valores = (
        datos["nombre"],
        datos["edad"],
        datos["ciudad"],
        datos["correo"],
        datos.get("fotografia") or datos.get("foto"),
        datos["programa"],
        datos["ficha"],
        datos["jornada"],
        id,
    )

    cursor.execute(sql, valores)
    conec.commit()

    cursor.close()
    conec.close()
    return {"mensaje": "HOJA DE VIDA ACTUALIZADA", "id": id}, 200
#ELIMINAR HOJA DE VIDA
@app.route("/api/eliminarhv/<int:id>", methods=["DELETE"])

def eliminar_hv(id):
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM hojas_vida WHERE id = %s", (id,))
    if cursor.fetchone() is None:
        cursor.close()
        conec.close()
        return {"mensaje": "HOJA DE VIDA NO ECONTRADA"}, 404

    cursor.execute("DELETE FROM hojas_vida WHERE id = %s", (id,))
    conec.commit()

    cursor.close()
    conec.close()
    return {"mensaje": "HOJA DE VIDA ELIMINADA", "id": id}, 200

# ESTUDIOS
@app.route("/api/hojasvida/<int:id_hv>/estudios", methods=["POST"])
@app.route("/api/HOJAS_VIDA/<int:id_hv>/estudios", methods=["POST"])

#REGISTRO ESTUDIO
def registrar_estudio(id_hv):
    datos = request.get_json()
    if not datos:
        return {"mensaje": "JSON UNIQUE"}, 400

    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM hojas_vida WHERE id = %s", (id_hv,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "HOJA DE VIDA INEXISTENTE"}, 404

    sql = """INSERT INTO estudios (hoja_vida_id, nivel, institucion, titulo, anio_graduacion) VALUES (%s, %s, %s, %s, %s)"""
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

    cursor.close()
    conec.close()

    return {
        "mensaje": "ESTUDIO REGISTRADO",
        "id_estudio": id_estudio,
        "hoja_vida_id": id_hv,
    }, 201


@app.route("/api/hojasvida/<int:id_hv>/estudios", methods=["GET"])
@app.route("/api/HOJAS_VIDA/<int:id_hv>/estudios", methods=["GET"])

def listar_estudios_hoja_vida(id_hv):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)

    cursor.execute("SELECT id FROM hojas_vida WHERE id = %s", (id_hv,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "HOJA DE VIDA INEXISTNETE"}, 404

    cursor.execute(
        "SELECT * FROM estudios WHERE hoja_vida_id = %s", (id_hv,)
    )
    estudios = cursor.fetchall()

    cursor.close()
    conec.close()

    return {"hoja_vida_id": id_hv, "estudios": estudios}, 200

#
@app.route("/api/estudios/<int:id_est>", methods=["GET"])
#CONSULTA ESTUDIO ID
def obtener_estudio(id_est):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)

    cursor.execute("SELECT * FROM estudios WHERE id = %s", (id_est,))
    estudio = cursor.fetchone()

    cursor.close()
    conec.close()

    if not estudio:
        return {"mensaje": "ESTUDIO NO ENCONTRADO"}, 404

    return {"estudio": estudio}, 200


@app.route("/api/estudios/<int:id_est>", methods=["PUT"])
def actualizar_estudio(id_est):
    datos = request.get_json()
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM estudios WHERE id = %s", (id_est,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "ESTUDIO INEXISTENTE"}, 404

    sql = """UPDATE estudios SET nivel = %s, institucion = %s, titulo = %s, anio_graduacion = %s WHERE id = %s"""
    valores = (
        datos.get("nivel"),
        datos.get("institucion"),
        datos.get("titulo"),
        datos.get("anio_graduacion"),
        id_est,
    )

    cursor.execute(sql, valores)
    conec.commit()

    cursor.close()
    conec.close()

    return {"mensaje": "ESTUDIO ACTUALIZADO"}

#ELIMINAR ESTUDIO
@app.route("/api/estudios/<int:id_est>", methods=["DELETE"])

def eliminar_estudio(id_est):
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM estudios WHERE id = %s", (id_est,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "ESTUDIO NOT EXISTS"}, 404

    cursor.execute("DELETE FROM estudios WHERE id = %s", (id_est,))
    conec.commit()

    cursor.close()
    conec.close()

    return {"mensaje": "ESTUDIO DELETED"}

# EXPERIENCIAS
@app.route("/api/hojasvida/<int:id_hv>/experiencias", methods=["POST"])
@app.route("/api/HOJAS_VIDA/<int:id_hv>/EXPERIENCIAS", methods=["POST"])
#
#REGISTRAR EXP
def registrar_experiencia(id_hv):
    datos = request.get_json()
    if not datos:
        return {"mensaje": "JSON UNIQUE"}, 400

    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM hojas_vida WHERE id = %s", (id_hv,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "HOJA DE VIDA INEXISTENTE"}, 404

    sql = """INSERT INTO experiencias (hoja_vida_id, empresa, cargo, tiempo, funciones) VALUES (%s, %s, %s, %s, %s)"""
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

    cursor.close()
    conec.close()

    return {
        "mensaje": "EXPERIENCIA REGISTRADA",
        "id_experiencia": id_experiencia,
        "hoja_vida_id": id_hv,
    }, 201


@app.route("/api/hojasvida/<int:id_hv>/experiencias", methods=["GET"])
def listar_experiencias_hoja_vida(id_hv):
    
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM experiencias WHERE hoja_vida_id = %s", (id_hv,)
    )
    resultado = cursor.fetchall()
    cursor.close()
    conec.close()

    return {"hoja_vida_id": id_hv, "experiencias": resultado}, 200


@app.route("/api/experiencias/<int:id_exp>", methods=["GET"])

def obtener_experiencia(id_exp):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)
    cursor.execute("SELECT * FROM experiencias WHERE id = %s", (id_exp,))
    experiencia = cursor.fetchone()

    cursor.close()
    conec.close()

    if not experiencia:
        return {"mensaje": "EXPERIENCIA NO ENCNONTRADA"}, 404
    return {"experiencia": experiencia}, 200

#ACTUALIZAR EXP
@app.route("/api/experiencias/<int:id_exp>", methods=["PUT"])
def actualizar_experiencia(id_exp):
    datos = request.get_json()
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM experiencias WHERE id = %s", (id_exp,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "EXPERIENCIA INEXISTENTE"}, 404

    sql = """UPDATE experiencias SET empresa = %s, cargo = %s, tiempo = %s, funciones = %s WHERE id = %s"""
    valores = (
        datos.get("empresa"),
        datos.get("cargo"),
        datos.get("tiempo"),
        datos.get("funciones"),
        id_exp,
    )

    cursor.execute(sql, valores)
    conec.commit()
    cursor.close()
    conec.close()

    return {"mensaje": "EXPERIENCIA ACTUALIZADO"}

#ELIMINAR EXP
@app.route("/api/experiencias/<int:id_exp>", methods=["DELETE"])
def eliminar_experiencia(id_exp):
    
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)
    cursor.execute("SELECT id FROM experiencias WHERE id = %s", (id_exp,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "EXPERIENCIA INEXISTENTE"}, 404

    cursor.execute("DELETE FROM experiencias WHERE id = %s", (id_exp,))
    conec.commit()

    cursor.close()
    conec.close()
    return {"mensaje": "EXPERIENCIA ELIMINADA"}

# HABILIDADES
@app.route("/api/experiencias/<int:id_exp>/habilidades", methods=["POST"])
@app.route("/api/HABILIDADES/<int:id_exp>", methods=["POST"])

#REGISTRAR HABILIDAD
def registrar_habilidad(id_exp):
    datos = request.get_json()
    if not datos or "nombre" not in datos:
        return {"mensaje": "NOMBRE FALTANTE"}, 400

    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM experiencias WHERE id = %s", (id_exp,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "EXPERIENCIA INEXISTENTE"}, 404

    sql = "INSERT INTO habilidades (experiencia_id, nombre) VALUES (%s, %s)"
    cursor.execute(sql, (id_exp, datos.get("nombre")))
    conec.commit()
    id_habilidad = cursor.lastrowid

    cursor.close()
    conec.close()

    return {
        "mensaje": "HABILIDAD REGISTRADA",
        "id_habilidad": id_habilidad,
        "experiencia_id": id_exp,
    }, 201


@app.route("/api/experiencias/<int:id_exp>/habilidades", methods=["GET"])
#CONSULTA EXP
def listar_habilidades_experiencia(id_exp):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM habilidades WHERE experiencia_id = %s", (id_exp,))
    resultado = cursor.fetchall()

    cursor.close()
    conec.close()
    return {"experiencia_id": id_exp, "habilidades": resultado}, 200

@app.route("/api/habilidades/<int:id_hab>", methods=["PUT"])

#ACTUALIZAR HABILIDAD
def actualizar_habilidad(id_hab):
    datos = request.get_json()
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM habilidades WHERE id = %s", (id_hab,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "HABILIDAD INEXISTENTE"}, 404

    sql = "UPDATE habilidades SET nombre = %s WHERE id = %s"
    cursor.execute(sql, (datos.get("nombre"), id_hab))
    conec.commit()

    cursor.close()
    conec.close()

    return {"mensaje": "HABILIDAD ACTUALIZADA"}

#ELIMINAR HABILIDAD
@app.route("/api/habilidades/<int:id_hab>", methods=["DELETE"])

def eliminar_habilidad(id_hab):
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM habilidades WHERE id = %s", (id_hab,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "Habilidad No Existe"}, 404

    sql = "DELETE FROM habilidades WHERE id = %s"
    cursor.execute(sql, (id_hab,))
    conec.commit()

    cursor.close()
    conec.close()

    return {"mensaje": "HABILIDAD ELIMINADA"}



#CURSOS
@app.route("/api/hojasvida/<int:id_hv>/cursos", methods=["POST"])
@app.route("/api/CURSOS/<int:id_hv>", methods=["POST"])

#REGISTRAR CURSO
def registrar_curso(id_hv):
    datos = request.get_json()
    if not datos or "nombre" not in datos:
        return {"mensaje": "NOMBRE VACÍO"}, 400
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM hojas_vida WHERE id = %s", (id_hv,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "HOJA DE VIDA INEXISTENTE"}, 404

    sql = "INSERT INTO cursos (hoja_vida_id, nombre) VALUES (%s, %s)"
    cursor.execute(sql, (id_hv, datos.get("nombre")))
    conec.commit()
    id_curso = cursor.lastrowid

    cursor.close()
    conec.close()

    return {
        "mensaje": "CURSO REGISTRADo",
        "id_curso": id_curso,
        "hoja_vida_id": id_hv,
    }, 201

#OBTENER CURSO
@app.route("/api/hojasvida/<int:id_hv>/cursos", methods=["GET"])

def listar_cursos_hoja_vida(id_hv):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)

    cursor.execute("SELECT * FROM cursos WHERE hoja_vida_id = %s", (id_hv,))
    resultado = cursor.fetchall()

    cursor.close()
    conec.close()
    return {"hoja_vida_id": id_hv, "cursos": resultado}, 200

@app.route("/api/cursos/<int:id_cur>", methods=["GET"])
def obtener_curso(id_cur):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)

    cursor.execute("SELECT * FROM cursos WHERE id = %s", (id_cur,))
    curso = cursor.fetchone()

    cursor.close()
    conec.close()

    if not curso:
        return {"mensaje": "CURSO NO ENCONTRADO"}, 404
    return {"curso": curso}, 200

#ACTUALIZAR CURSO
@app.route("/api/cursos/<int:id_cur>", methods=["PUT"])
def actualizar_curso(id_cur):
    datos = request.get_json()
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM cursos WHERE id = %s", (id_cur,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "Curso No Existe"}, 404

    sql = "UPDATE cursos SET nombre = %s WHERE id = %s"
    cursor.execute(sql, (datos.get("nombre"), id_cur))
    conec.commit()

    cursor.close()
    conec.close()
    return {"mensaje": "CURSO ACUTUALIZAO"}

#ELIMINAR CURSO
@app.route("/api/cursos/<int:id_cur>", methods=["DELETE"])
def eliminar_curso(id_cur):
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    cursor.execute("SELECT id FROM cursos WHERE id = %s", (id_cur,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "CURSO INEXISTENTE"}, 404

    sql = "DELETE FROM cursos WHERE id = %s"
    cursor.execute(sql, (id_cur,))
    conec.commit()

    cursor.close()
    conec.close()
    return {"mensaje": "CURSO ELIMINADO"}

#HOJA DE VIDA
@app.route("/api/HOJAS_VIDA/<int:id>/completa", methods=["GET"])
@app.route("/api/hojasvida/<int:id>/completa", methods=["GET"])

#CONSULTA HV COMPLET
def consultar_hoja_vida_completa(id):
    conec = conectar_bd()
    cursor = conec.cursor(dictionary=True)

    cursor.execute("SELECT * FROM hojas_vida WHERE id = %s", (id,))
    hoja_vida = cursor.fetchone()

    if hoja_vida is None:
        cursor.close()
        conec.close()
        return {"mensaje": "HOJA DE VIDA NO ENCONTRADA"}, 404

    cursor.execute("SELECT * FROM estudios WHERE hoja_vida_id = %s", (id,))
    estudios = cursor.fetchall()

    cursor.execute("SELECT * FROM cursos WHERE hoja_vida_id = %s", (id,))
    cursos = cursor.fetchall()

    cursor.execute("SELECT * FROM experiencias WHERE hoja_vida_id = %s", (id,))
    experiencias = cursor.fetchall()

    for experiencia in experiencias:
        cursor.execute("SELECT id, experiencia_id, nombre FROM habilidades WHERE experiencia_id = %s",(experiencia["id"],),) 
        experiencia["habilidades"] = cursor.fetchall()

    cursor.close()
    conec.close()

    return {
        "hoja_de_vida": hoja_vida,
        "estudios": estudios,
        "cursos": cursos,
        "experiencias": experiencias,
    }, 200


#FLASK
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)