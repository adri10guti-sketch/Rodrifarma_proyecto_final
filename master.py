from Modulos.conexiones_data_base import inicializar_bd, conectar

inicializar_bd()

# Prueba temporal: mostrar los usuarios guardados
with conectar() as conexion:
    for fila in conexion.execute("SELECT nombre, rol FROM usuarios"):
        print(fila["nombre"], "-", fila["rol"])