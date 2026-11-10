CREATE DATABASE HojaDeVida;
use HojaDeVida;

Drop database HojaDeVida;

CREATE TABLE HOJAS_VIDA (
    id_HV INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    edad INT,
    ciudad VARCHAR(100),
    correo VARCHAR(150) NOT NULL,
    foto VARCHAR(255),
    programa VARCHAR(150),
    ficha VARCHAR(20),
    jornada VARCHAR(50)
);

CREATE TABLE ESTUDIOS (
    id_EST INT AUTO_INCREMENT PRIMARY KEY,
    hoja_vida_id INT NOT NULL,
    institucion VARCHAR(150),
    titulo VARCHAR(150),
    anio_graduacion INT,
    FOREIGN KEY (hoja_vida_id) REFERENCES HOJAS_VIDA(id_HV)
);

CREATE TABLE CURSOS (
    id_CUR INT AUTO_INCREMENT PRIMARY KEY,
    hoja_vida_id INT NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    FOREIGN KEY (hoja_vida_id) REFERENCES HOJAS_VIDA(id_HV)
);

CREATE TABLE EXPERIENCIAS (
    id_EXP INT AUTO_INCREMENT PRIMARY KEY,
    hoja_vida_id INT NOT NULL,
    empresa VARCHAR(150) NOT NULL,
    cargo VARCHAR(100),
    tiempo VARCHAR(100),
    funciones TEXT,
    FOREIGN KEY (hoja_vida_id) REFERENCES HOJAS_VIDA(id_HV)
);

CREATE TABLE HABILIDADES (
    id_HAB INT AUTO_INCREMENT PRIMARY KEY,
    experiencia_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    FOREIGN KEY (experiencia_id) REFERENCES EXPERIENCIAS(id_EXP)
);

CREATE TABLE IF NOT EXISTS USUARIO (
id_USER INT AUTO_INCREMENT PRIMARY KEY,
nombre_user VARCHAR(100) NOT NULL,
correo_user VARCHAR(150) NOT NULL UNIQUE,
contraseña VARCHAR(255) NOT NULL,
rol ENUM('Aprendiz','Reclutador') NOT NULL DEFAULT 'Aprendiz',
estado TINYINT(1) DEFAULT 1,
fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE HOJAS_VIDA                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         
ADD COLUMN usuario_ID INT NULL UNIQUE,
ADD CONSTRAINT hoja_usuario
FOREIGN KEY (usuario_ID) REFERENCES USUARIO(id_USER)
;
