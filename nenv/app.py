from flask import Flask, request, jsonify
from database import conectar_bd

app = Flask(__name__)

#PRUEBAS
@app.route("/probar")
def probar_data():
    connect = conectar_bd()

    if connect.is_connected():
        connect.close()

    return {
        "mensaje": "\\CONECTED.=!//"
    }

@app.route("/api/registrohv", methods=["POST"])
def registrohvida():
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)
    datos = request.json

    # VERIFICAR CORREO EXISTENTE
    sql_consulta = "SELECT id_HV FROM HOJAS_VIDA WHERE correo = %s"
    cursor.execute(sql_consulta, (datos["correo"],))
    usuario_existente = cursor.fetchone()

    if usuario_existente:
        id_existente = usuario_existente[0]
        cursor.close()
        conec.close()
        return {
            "mensaje": "Usuario Ya Existente",
            "id": id_existente
        }, 400

    # REGISTRAR
    sql = """INSERT INTO HOJAS_VIDA
    (nombre, edad, ciudad, correo, foto, programa, ficha, jornada) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""

    valor = (
        datos["nombre"],
        datos["edad"],
        datos["ciudad"],
        datos["correo"],
        datos.get("foto"),
        datos["programa"],
        datos["ficha"],
        datos["jornada"]
    )

    cursor.execute(sql, valor)
    conec.commit()

    id_generado = cursor.lastrowid

    cursor.close()
    conec.close()

    return {
        "mensaje": "¡Hoja De Vida Creada!",
        "id": id_generado
    }, 201


@app.route("/api/hojasvida", methods=["GET"])
def listar_hojasvida():
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    sql = "SELECT * FROM HOJAS_VIDA"
    cursor.execute(sql)
    datos = cursor.fetchall()

    columnas = [columna[0] for columna in cursor.description]
    resultado = []

    for lista in datos:
        hoja_vida = dict(zip(columnas, lista))
        resultado.append(hoja_vida)

    cursor.close()
    conec.close()

    return {
        "hojas_vida": resultado
    }

#

#REGISTRO ESTUDIO HV
@app.route("/api/hojasvida/<int:id_hv>/estudios", methods=["POST"])
def registrar_estudio(id_hv):
    datos = request.json
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    #VERIFICAR EXISTENCIA HV
    cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE id_HV = %s", (id_hv,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "Hoja de Vida No Existe"}, 404

    sql = """INSERT INTO ESTUDIOS (hoja_vida_id, institucion, titulo, anio_graduacion)
             VALUES (%s, %s, %s, %s)"""
    valores = (
        id_hv,
        datos.get("institucion"),
        datos.get("titulo"),
        datos.get("anio_graduacion")
    )

    cursor.execute(sql, valores)
    conec.commit()
    id_estudio = cursor.lastrowid

    cursor.close()
    conec.close()

    return {
        "mensaje": "Estudio Registrado",
        "id_estudio": id_estudio
    }, 201


#CONSULTA TODOS ESTUDIOS HV
@app.route("/api/hojasvida/<int:id_hv>/estudios", methods=["GET"])
def listar_estudios_hoja_vida(id_hv):
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    sql = "SELECT * FROM ESTUDIOS WHERE hoja_vida_id = %s"
    cursor.execute(sql, (id_hv,))
    datos = cursor.fetchall()

    columnas = [columna[0] for columna in cursor.description]
    resultado = [dict(zip(columnas, fila)) for fila in datos]

    cursor.close()
    conec.close()

    return {
        "hoja_vida_id": id_hv,
        "estudios": resultado
    }


#CONSULTA ESTUDIO ID
@app.route("/api/estudios/<int:id_est>", methods=["GET"])
def obtener_estudio(id_est):
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    sql = "SELECT * FROM ESTUDIOS WHERE id_EST = %s"
    cursor.execute(sql, (id_est,))
    estudio = cursor.fetchone()

    if not estudio:
        cursor.close()
        conec.close()
        return {"mensaje": "Estudio No Encontrado"}, 404

    columnas = [columna[0] for columna in cursor.description]
    resultado = dict(zip(columnas, estudio))

    cursor.close()
    conec.close()

    return {
        "estudio": resultado
    }


#ACTUALIZAR ESTUDIO
@app.route("/api/estudios/<int:id_est>", methods=["PUT"])
def actualizar_estudio(id_est):
    datos = request.json
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    #VERIFICAR EXISTENCIA ESTUDIO
    cursor.execute("SELECT id_EST FROM ESTUDIOS WHERE id_EST = %s", (id_est,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "Estudio No Existe"}, 404

    sql = """UPDATE ESTUDIOS 
             SET institucion = %s, titulo = %s, anio_graduacion = %s 
             WHERE id_EST = %s"""
    valores = (
        datos.get("institucion"),
        datos.get("titulo"),
        datos.get("anio_graduacion"),
        id_est
    )

    cursor.execute(sql, valores)
    conec.commit()

    cursor.close()
    conec.close()

    return {
        "mensaje": "Estudio Actualizado"
    }


#ELIMINAR ESTUDIO
@app.route("/api/estudios/<int:id_est>", methods=["DELETE"])
def eliminar_estudio(id_est):
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    #VALIDAR EXISTENCIA ESTUDIO
    cursor.execute("SELECT id_EST FROM ESTUDIOS WHERE id_EST = %s", (id_est,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "Estudio No Existe"}, 404

    sql = "DELETE FROM ESTUDIOS WHERE id_EST = %s"
    cursor.execute(sql, (id_est,))
    conec.commit()

    cursor.close()
    conec.close()

    return {
        "mensaje": "Estudio Eliminado"
    }

#EXPERIENCIA

#REGISTRAR EXP
@app.route("/api/hojasvida/<int:id_hv>/experiencias", methods=["POST"])
def registrar_experiencia(id_hv):
    datos = request.json
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    #VERIFICAR EXISTENCIA EXP
    cursor.execute("SELECT id_HV FROM HOJAS_VIDA WHERE id_HV = %s", (id_hv,))
    if not cursor.fetchone():
        cursor.close()
        conec.close()
        return {"mensaje": "Hoja de Vida No Existe"}, 404

    sql = """INSERT INTO EXPERIENCIAS (hoja_vida_id, empresa, cargo, tiempo, funciones)
             VALUES (%s, %s, %s, %s, %s)"""
    valores = (
        id_hv,
        datos.get("empresa"),
        datos.get("cargo"),
        datos.get("tiempo"),
        datos.get("funciones")
    )

    cursor.execute(sql, valores)
    conec.commit()
    id_experiencia = cursor.lastrowid

    cursor.close()
    conec.close()

    return {
        "mensaje": "Experiencia Registrada",
        "id_experiencia": id_experiencia
    }, 201


#CONSUTLRA TODAS LAS EXP
@app.route("/api/hojasvida/<int:id_hv>/experiencias", methods=["GET"])
def listar_experiencias_hoja_vida(id_hv):
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    sql = "SELECT * FROM EXPERIENCIAS WHERE hoja_vida_id = %s"
    cursor.execute(sql, (id_hv,))
    datos = cursor.fetchall()

    columnas = [columna[0] for columna in cursor.description]
    resultado = [dict(zip(columnas, fila)) for fila in datos]

    cursor.close()
    conec.close()

    return {
        "hoja_vida_id": id_hv,
        "experiencias": resultado
    }


#CONSULTAR EXP POR ID
@app.route("/api/experiencias/<int:id_exp>", methods=["GET"])
def obtener_experiencia(id_exp):
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)

    sql = "SELECT * FROM EXPERIENCIAS WHERE id_EXP = %s"
    cursor.execute(sql, (id_exp,))
    experiencia = cursor.fetchone()

    if not experiencia:
        cursor.close()
        conec.close()
        return {"mensaje": "Experiencia No Encontrada"}, 404

    columnas = [columna[0] for columna in cursor.description]
    resultado = dict(zip(columnas, experiencia))

    cursor.close()
    conec.close()

    return {
        "experiencia": resultado
    }

#
if __name__ == "__main__":
    app.run(debug=True)