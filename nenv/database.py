import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def conectar_bd():
    try:
        conexion = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "HojaDeVida"),
            charset="utf8mb4",
            collation="utf8mb4_general_ci",
        )
        return conexion
    except mysql.connector.Error as err:
        print(f"Error al conectar con la base de datos: {err}")
        return None
