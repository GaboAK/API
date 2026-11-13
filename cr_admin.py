import os
import sys
from werkzeug.security import generate_password_hash
from database import conectar_bd


def admin():
    print("=== Creación de Usuario Administrativo / Reclutador ===")
    nombre = input("Ingrese su nombre: ").strip()
    correo = input("Ingrese su correo: ").strip().lower()
    contraseña = input("Ingrese su contraseña: ").strip()

    if not nombre or not correo or not contraseña:
        print("Error: Todos los campos son obligatorios.")
        return

    if len(contraseña) < 8 or len(contraseña) > 15:
        print("La contraseña debe tener entre 8 y 15 caracteres.")
        return

    print("Seleccione el rol:")
    print("1. Reclutador (por defecto)")
    print("2. Aprendiz")
    opcion_rol = input("Opción [1/2]: ").strip()
    rol = "Aprendiz" if opcion_rol == "2" else "Reclutador"

    conexion = conectar_bd()
    if not conexion or not conexion.is_connected():
        print("Error: No se pudo conectar a la base de datos.")
        return

    cursor = None
    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT id_USER FROM USUARIO WHERE correo_user = %s", (correo,))
        existente = cursor.fetchone()

        if existente:
            print("El correo ya está registrado.")
            return

        cursor.execute("SELECT id_USER FROM USUARIO WHERE nombre_user = %s", (nombre,))
        if cursor.fetchone():
            print("El nombre de usuario ya está registrado.")
            return

        password_hash = generate_password_hash(contraseña)
        sql = "INSERT INTO USUARIO (nombre_user, correo_user, contraseña, rol) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (nombre, correo, password_hash, rol))

        conexion.commit()
        print(f"Usuario '{nombre}' con rol '{rol}' creado con éxito.")

    except Exception as e:
        print("Error al crear el usuario:", e)
        if conexion and conexion.is_connected():
            conexion.rollback()
    finally:
        if cursor:
            cursor.close()
        if conexion and conexion.is_connected():
            conexion.close()


if __name__ == "__main__":
    admin()

