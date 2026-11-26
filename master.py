from Modulos.conexiones_data_base import inicializar_bd
from Modulos.seguridad import pantalla_acceso, tiene_permiso, mensaje_restringido
from Modulos import gestion, facturas_y_boletas

TEXTO_OPCIONES = {
    1: "Registrar producto recibido",
    2: "Buscar registro por código",
    3: "Mostrar listado de todos los registros",
    4: "Registrar productos vendidos",
    5: "Lista de productos vendidos",
    6: "Ver productos vencidos y por vencer",
    7: "Actualizar precio unitario",
    0: "Salir (guardado automático)",
}

# Cada acción recibe al usuario que inició sesión
ACCIONES = {
    1: lambda usuario: gestion.registrar_producto(),
    2: lambda usuario: gestion.buscar_por_codigo(),
    3: lambda usuario: gestion.mostrar_listado(),
    4: lambda usuario: facturas_y_boletas.registrar_venta(usuario["nombre"]),
    5: lambda usuario: facturas_y_boletas.lista_ventas(),
    6: lambda usuario: gestion.ver_vencimientos(),
    7: lambda usuario: gestion.actualizar_precio(),
}


def mostrar_menu(rol):
    print("\n=== MENÚ PRINCIPAL ===")
    for numero in (1, 2, 3, 4, 5, 6, 7, 0):
        if tiene_permiso(rol, numero):
            print(f"{numero} - {TEXTO_OPCIONES[numero]}")


def menu_principal(usuario):
    while True:
        mostrar_menu(usuario["rol"])
        entrada = input("Elija una opción: ").strip()

        if not entrada.isdigit() or int(entrada) not in TEXTO_OPCIONES:
            print("❌ Opción no válida.")
            continue

        opcion = int(entrada)
        if not tiene_permiso(usuario["rol"], opcion):
            print(mensaje_restringido(opcion))
        elif opcion == 0:
            print("Datos guardados. ¡Hasta luego!")
            break
        else:
            ACCIONES[opcion](usuario)


def main():
    inicializar_bd()
    usuario = pantalla_acceso()
    if usuario is None:
        print("Hasta luego.")
        return
    menu_principal(usuario)


if __name__ == "__main__":
    main()