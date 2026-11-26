"""
Operaciones de inventario de RODRIFARMA:
  1 - Registrar producto recibido
  2 - Buscar registro por código
  3 - Mostrar listado de todos los registros
  6 - Ver productos vencidos y por vencer
  7 - Actualizar precio unitario
(Las opciones 4 y 5, de ventas, se agregan en el siguiente paso.)
"""

import re
from datetime import datetime

from Modulos.conexiones_data_base import conectar



# ---------------------------------------------------------------
# Constantes que usaremos:
# ---------------------------------------------------------------
PRESENTACIONES = ("Caja", "Blíster", "Frasco", "Unidad")
PREFIJO_CODIGO = "ING-"
MESES_POR_VENCER = 3   # por vencer = vence dentro de 3 meses o menos
STOCK_BAJO = 5         # alerta si quedan 5 unidades o menos
PRECIO_MAXIMO = 10000
CANTIDAD_MAXIMA = 100000



# ---------------------------------------------------------------
# Utilidades generales
# ---------------------------------------------------------------
def fecha_hoy():
    """Fecha actual del sistema esta creada en formato DD/MM/AAAA(dias,mese,años)"""
    return datetime.now().strftime("%d/%m/%Y")


def imprimir_tabla(encabezados, filas):
    """Imprime una tabla de texto con columnas alineadas"""
    anchos = [max(len(str(valor)) for valor in columna)
              for columna in zip(encabezados, *filas)]
    linea = "+-" + "-+-".join("-" * ancho for ancho in anchos) + "-+"

    def formatear(fila):
        return "| " + " | ".join(str(v).ljust(a) for v, a in zip(fila, anchos)) + " |"

    print(linea)
    print(formatear(encabezados))
    print(linea)
    for fila in filas:
        print(formatear(fila))
    print(linea)


# ---------------------------------------------------------------
# Validaciones y entrada de datos:
# ---------------------------------------------------------------
def validar_nombre_producto(nombre):
    """3 a 40 caracteres: letras, números, espacios y . % / -"""
    return re.fullmatch(r"[A-Za-zÁÉÍÓÚÜáéíóúüÑñ0-9 .%/\-]{3,40}", nombre) is not None


def validar_vencimiento(texto):
    """Formato MM/AAAA con mes 01-12 y año entre 2000 y 2100."""
    if re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", texto) is None:
        return False
    return 2000 <= int(texto[3:]) <= 2100


def pedir_nombre_producto():
    while True:
        nombre = " ".join(input("Nombre y concentración (ej. Paracetamol 500mg): ").split())
        if validar_nombre_producto(nombre):
            return nombre
        print("Nombre inválido (3 a 40 caracteres: letras, números, espacios y . % / -).")


def pedir_presentacion():
    print("Presentación:")
    for numero, nombre in enumerate(PRESENTACIONES, start=1):
        print(f"  {numero} - {nombre}")
    while True:
        eleccion = input("Elija la presentación: ").strip()
        if eleccion.isdigit() and 1 <= int(eleccion) <= len(PRESENTACIONES):
            return PRESENTACIONES[int(eleccion) - 1]
        print("ERROR esta opción no válida =[ ")


def pedir_precio(mensaje="Precio unitario (S/): "):
    while True:
        try:
            precio = round(float(input(mensaje).strip().replace(",", ".")), 2)
        except ValueError:
            print("no es dificil amigo, ingresa un número válido (ej. 2.50).")
            continue
        if 0 < precio <= PRECIO_MAXIMO:
            return precio
        print(f"NOOOO... el precio debe ser mayor que 0 y menor o igual a {PRECIO_MAXIMO}!!!")


def pedir_cantidad(mensaje):
    while True:
        texto = input(mensaje).strip()
        if texto.isdigit() and 1 <= int(texto) <= CANTIDAD_MAXIMA:
            return int(texto)
        print(f"Ingrese un número entero entre 1 y {CANTIDAD_MAXIMA} =) ")


def pedir_vencimiento():
    while True:
        texto = input("Fecha de vencimiento (MM/AAAA): ").strip()
        if validar_vencimiento(texto):
            return texto
        print("Formato inválido----Use MM/AAAA, por ejemplo (08/2027) ")



# ---------------------------------------------------------------
# Acceso a datos:
# ---------------------------------------------------------------
def generar_codigo():
    """Crea el siguiente codigo automatico: ING-0001, ING-0002, ..."""
    with conectar() as conexion:
        fila = conexion.execute(
            "SELECT MAX(CAST(SUBSTR(codigo, 5) AS INTEGER)) AS ultimo FROM productos"
        ).fetchone()
    siguiente = (fila["ultimo"] or 0) + 1
    return f"{PREFIJO_CODIGO}{siguiente:04d}"


def obtener_producto(codigo):
    """Devuelve la fila del producto o None si no si este no existe"""
    with conectar() as conexion:
        return conexion.execute(
            "SELECT * FROM productos WHERE codigo = ?", (codigo,)
        ).fetchone()



# ---------------------------------------------------------------
# Opción 1: Registrar producto recibido
# ---------------------------------------------------------------
def registrar_producto():
    print("\n--- REGISTRAR PRODUCTO RECIBIDO ---")
    nombre = pedir_nombre_producto()
    presentacion = pedir_presentacion()
    precio = pedir_precio()
    stock = pedir_cantidad("Cantidad de unidades recibidas: ")
    vencimiento = pedir_vencimiento()

    codigo = generar_codigo()
    fecha_registro = fecha_hoy()

    with conectar() as conexion:
        conexion.execute(
            """INSERT INTO productos
               (codigo, nombre, presentacion, precio_unitario, stock,
                fecha_registro, fecha_vencimiento)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (codigo, nombre, presentacion, precio, stock, fecha_registro, vencimiento),
        )

    print("\n Este producto fue registrado correctamente")
    print(f"   Código generado : {codigo}")
    print(f"   Producto        : {nombre} ({presentacion})")
    print(f"   Precio unitario : S/ {precio:.2f}")
    print(f"   Stock inicial   : {stock}")
    print(f"   Fecha registro  : {fecha_registro}")
    print(f"   Vence           : {vencimiento}")



# ---------------------------------------------------------------
# Opción 2: Buscar registro por código
# ---------------------------------------------------------------
def buscar_por_codigo():
    print("\n--- BUSCAR REGISTRO POR CÓDIGO ---")
    codigo = input("Ingrese el código (ej. ING-0001): ").strip().upper()
    producto = obtener_producto(codigo)

    if producto is None:
        print(f"Que raro no existe ningún producto con el código {codigo} ")
        return

    print("\n Registro encontrado")
    print(f"   Código          : {producto['codigo']}")
    print(f"   Nombre          : {producto['nombre']}")
    print(f"   Presentación    : {producto['presentacion']}")
    print(f"   Precio unitario : S/ {producto['precio_unitario']:.2f}")
    print(f"   Stock           : {producto['stock']}")
    print(f"   Fecha registro  : {producto['fecha_registro']}")
    print(f"   Vence           : {producto['fecha_vencimiento']}")




# ---------------------------------------------------------------
# Opción 3: Mostrar listado de todos los registros
# ---------------------------------------------------------------
def mostrar_listado():
    print("\n--- LISTADO DE PRODUCTOS ---")
    # Las fechas se guardan como texto, para ordenarlas bien se reordenan como AAAA/MM/DD (registro) y AAAA/MM (vencimiento)
    with conectar() as conexion:
        productos = conexion.execute(
            """SELECT * FROM productos
               ORDER BY nombre COLLATE NOCASE,
                        SUBSTR(fecha_registro, 7, 4) || SUBSTR(fecha_registro, 4, 2)
                            || SUBSTR(fecha_registro, 1, 2),
                        SUBSTR(fecha_vencimiento, 4, 4) || SUBSTR(fecha_vencimiento, 1, 2)"""
        ).fetchall()

    if not productos:
        print("No hay productos registrados todavía")
        return

    filas = [
        (p["nombre"], p["presentacion"], p["fecha_registro"], p["fecha_vencimiento"],
         p["codigo"], f"S/ {p['precio_unitario']:.2f}", p["stock"])
        for p in productos
    ]
    imprimir_tabla(
        ["Nombre", "Present.", "F. registro", "F. vence", "Código", "P. unit.", "Stock"],
        filas,
    )
    print(f"Total de registros: {len(productos)}")




# ---------------------------------------------------------------
# Opción 6: Productos vencidos y por vencer
# ---------------------------------------------------------------
def meses_para_vencer(fecha_vencimiento, hoy=None):
    """
    Meses que faltan para el mes de vencimiento (MM/AAAA)
    Negativo = ya vencio--0 = vence este mismo mes
    Se asume que el producto vence el último día del mes indicado
    """
    hoy = hoy or datetime.now()
    mes, anio = int(fecha_vencimiento[:2]), int(fecha_vencimiento[3:])
    return (anio - hoy.year) * 12 + (mes - hoy.month)


def ver_vencimientos():
    print("\n--- PRODUCTOS VENCIDOS Y POR VENCER ---")
    with conectar() as conexion:
        productos = conexion.execute("SELECT * FROM productos").fetchall()

    filas = []
    for p in productos:
        meses = meses_para_vencer(p["fecha_vencimiento"])
        if meses < 0:
            estado = "VENCIDO"
        elif meses <= MESES_POR_VENCER:
            estado = "POR VENCER"
        else:
            continue
        filas.append((meses, p["nombre"], p["presentacion"], p["codigo"],
                      p["fecha_vencimiento"], p["stock"], estado))

    if filas:
        filas.sort(key=lambda f: f[0])  # primero los más vencidos
        imprimir_tabla(
            ["Nombre", "Present.", "Codigo", "F. vence", "Stock", "Estado"],
            [f[1:] for f in filas],
        )
    else:
        print("No hay productos vencidos ni por vencer =) ")

    # se incorporo una alerta adicional que indica cuando hay stock bajo:
    bajos = [p for p in productos if p["stock"] <= STOCK_BAJO]
    if bajos:
        print(f"\n Alerta de stock bajooo...!! ({STOCK_BAJO} unidades o menos):")
        imprimir_tabla(
            ["Nombre", "Codigo", "Stock"],
            [(p["nombre"], p["codigo"], p["stock"]) for p in bajos],
        )


# ---------------------------------------------------------------
# Opción 7: Actualizar precio unitario
# ---------------------------------------------------------------
def actualizar_precio():
    print("\n--- ACTUALIZAR PRECIO UNITARIO ---")
    codigo = input("Ingrese el codigo (ej. ING-0001): ").strip().upper()
    producto = obtener_producto(codigo)

    if producto is None:
        print(f"Al parecer NO existe ningun producto con el codigo {codigo}.")
        return

    print(f"Producto: {producto['nombre']} | Precio actual: S/ {producto['precio_unitario']:.2f}")
    nuevo = pedir_precio("Nuevo precio unitario (S/): ")

    with conectar() as conexion:
        conexion.execute(
            "UPDATE productos SET precio_unitario = ? WHERE codigo = ?",
            (nuevo, codigo),
        )
    print(f"Precio actualizado: S/ {producto['precio_unitario']:.2f} → S/ {nuevo:.2f}")