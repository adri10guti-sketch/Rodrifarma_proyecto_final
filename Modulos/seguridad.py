"""
seguridad.py
------------
Registro, inicio de sesión (máximo 3 intentos), validación de datos
y permisos por rol para el sistema de RODRIFARMA.
"""

import re

from Modulos.conexiones_data_base import conectar

# ---------------------------------------------------------------
# Constantes (si cambia una regla, se modifica solo aquí):
# ---------------------------------------------------------------
MAX_INTENTOS = 3
LONGITUD_PASSWORD = 6
MIN_LETRAS_PASSWORD = 1
MAX_LETRAS_PASSWORD = 4
ROLES_VALIDOS = ("administradora", "asistente")


# Opciones del menú que puede usar cada rol:
OPCIONES_POR_ROL = {
    "administradora": [1, 2, 3, 4, 5, 6, 7, 0],
    "asistente": [2, 3, 4, 6, 0],
}




# ---------------------------------------------------------------
# Validaciones de formato (devuelven True o False)
# ---------------------------------------------------------------
def validar_nombre(nombre):
    """4 a 12 letras minúsculas de la a-z, sin espacios ni números"""
    return re.fullmatch(r"[a-z]{4,12}", nombre) is not None

def validar_rol(rol):
    return rol in ROLES_VALIDOS

def validar_password(password):
    """6 caracteres alfanuméricos, con 1 a 4 letras (el resto números)"""
    if len(password) != LONGITUD_PASSWORD:
        return False
    if re.fullmatch(r"[A-Za-z0-9]+", password) is None:
        return False
    cantidad_letras = sum(1 for c in password if c.isalpha())
    return MIN_LETRAS_PASSWORD <= cantidad_letras <= MAX_LETRAS_PASSWORD





# ---------------------------------------------------------------
# Acceso a la base de datos
# ---------------------------------------------------------------
def buscar_usuario(nombre):
    """Devuelve la fila del usuario o None si no existe"""
    with conectar() as conexion:
        return conexion.execute(
            "SELECT nombre, rol, password FROM usuarios WHERE nombre = ?",
            (nombre,),
        ).fetchone()


def credenciales_correctas(nombre, rol, password):
    """True si nombre, rol y contraseña coinciden con un usuario guardado."""
    usuario = buscar_usuario(nombre)
    return (
        usuario is not None
        and usuario["rol"] == rol
        and usuario["password"] == password
    )


def guardar_usuario(nombre, rol, password):
    with conectar() as conexion:
        conexion.execute(
            "INSERT INTO usuarios (nombre, rol, password) VALUES (?, ?, ?)",
            (nombre, rol, password),
        )






# ---------------------------------------------------------------
# Entrada de datos
# ---------------------------------------------------------------
def pedir_datos():
    """Pide nombre, rol y contraseña este devuelve (nombre, rol, password)."""
    nombre = input("Nombre: ").strip()
    rol = input("Rol (administradora / asistente): ").strip().lower()
    password = input("Contraseña: ").strip()
    return nombre, rol, password





# ---------------------------------------------------------------
# Registro e inicio de sesión
# ---------------------------------------------------------------
def registrar_usuario():
    """
    Registro de un nuevo usuario (máximo 3 intentos):
    - Asistente: se crea si los datos son validos y el nombre esta libre.
    - Administradora: solo entra quien ya conoce nombre, rol y contraseña.
    Devuelve {'nombre', 'rol'} o None si se agotaron los intentos.
    """
    print("\n--- REGISTRO ---")
    print("Nombre: 4 a 12 letras minúsculas (a-z), sin espacios ni números.")
    print("Contraseña: 6 caracteres, con al menos 1 y máximo 4 letras. Ej.: ab1234")

    for intento in range(1, MAX_INTENTOS + 1):
        nombre, rol, password = pedir_datos()
        restantes = MAX_INTENTOS - intento

        if not validar_nombre(nombre):
            print(f"Nombre inválido----Intentos restantes: {restantes}")
        elif not validar_rol(rol):
            print(f"Rol inválido----Intentos restantes: {restantes}")
        elif not validar_password(password):
            print(f"Contraseña incorrecta----Intentos restantes: {restantes}")
        elif rol == "administradora":

            # El rol de administradora no se crea: se verifica
            if credenciales_correctas(nombre, rol, password):
                print("Registro exitoso")
                return {"nombre": nombre, "rol": rol}
            print(f"Acción inválida para ese rol----Intentos restantes: {restantes}")
        elif buscar_usuario(nombre) is not None:
            print(f"Ese nombre ya está registrado----Intentos restantes: {restantes}")
        else:
            guardar_usuario(nombre, rol, password)
            print("Registro exitoso")
            return {"nombre": nombre, "rol": rol}

    print("ACCESO DENEGADO :[")
    return None


def iniciar_sesion():
    """
    Inicio de sesión con máximo 3 intentos.
    Devuelve {'nombre', 'rol'} o None si se agotaron los intentos.
    """
    print("\n--- INICIAR SESIÓN ---")
    for intento in range(1, MAX_INTENTOS + 1):
        nombre, rol, password = pedir_datos()
        if credenciales_correctas(nombre, rol, password):
            print(f"Bienvenid@, {nombre}.")
            return {"nombre": nombre, "rol": rol}
        restantes = MAX_INTENTOS - intento
        print(f"El nombre, el rol o la contraseña no cumplen con los requisitos---Intentos restantes: {restantes}")

    print("ACCESO DENEGADO :[ ")
    return None


def pantalla_acceso():
    """Primera pantalla: registrarse o ya estoy registrado."""
    while True:
        print("\n=== BOTICA RODRIFARMA ===")
        print("1 - Registrarme")
        print("2 - Ya estoy registrado")
        print("0 - Salir")
        opcion = input("Elija una opción: ").strip()

        if opcion == "1":
            return registrar_usuario()
        if opcion == "2":
            return iniciar_sesion()
        if opcion == "0":
            return None
        print("Opción no válida.")


# ---------------------------------------------------------------
# Permisos
# ---------------------------------------------------------------
def tiene_permiso(rol, opcion):
    return opcion in OPCIONES_POR_ROL.get(rol, [])


def mensaje_restringido(opcion):
    return f"Acceso restringido: La opción {opcion} es exclusiva para la Administradora."