from Modulos.conexiones_data_base import inicializar_bd
from Modulos.seguridad import pantalla_acceso

inicializar_bd()

usuario = pantalla_acceso()

if usuario is None:
    print("Hasta luego.")
else:
    print(f"Ingresaste como {usuario['nombre']} ({usuario['rol']})")