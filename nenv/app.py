from flask import Flask, request
from database import conectar_bd

app = Flask(__name__)

@app.route("/probar")
def probar_data():
    connect = conectar_bd()

    if connect.is_connected():
        connect.close()

    return {
        "mensaje": "//CONECTADO//"
    }

@app.route("/api/registrohv", methods=["POST"])
def registrohvida():
    conec = conectar_bd()
    cursor = conec.cursor(buffered=True)
    datos = request.json

    #VERIFICAR CORREO EXISTENTE
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
        }

    #REGISTRAR
    sql = """INSERT INTO HOJAS_VIDA
    (nombre, edad, ciudad, correo, foto, programa, ficha, jornada)VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""

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
    }


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

if __name__ == "__main__":
    app.run(debug=True)
