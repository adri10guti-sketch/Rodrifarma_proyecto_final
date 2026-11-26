"""
Ventas y comprobantes de RODRIFARMA:
  4 - Registrar productos vendidos (con boleta o factura para el cliente)
  5 - Lista de productos vendidos (por día)
"""
import re
from datetime import datetime

from Modulos.conexiones_data_base import conectar
from Modulos.gestion import (
    fecha_hoy,
    imprimir_tabla,
    meses_para_vencer,
    obtener_producto,
    pedir_cantidad,
)



# ---------------------------------------------------------------
# Datos fijos de la farmacia y reglas de cálculo:
# ---------------------------------------------------------------
NOMBRE_FARMACIA = "RODRIFARMA"
RUC_FARMACIA = "10405540687"
SERIE_BOLETA = "B001"      # Cliente con DNI
SERIE_FACTURA = "F001"     # Cliente con RUC
IGV = 0.18                 # Esto es cuando los precios de venta ya incluyen el IGV
UMBRAL_DESCUENTO = 100.00  # En caso de que su compras sea mayor a este monto reciben un descuento
PORCENTAJE_DESCUENTO = 10
ANCHO = 84                 # Ancho del comprobante en la consola




# ---------------------------------------------------------------
# Validaciones y entrada de datos del cliente:
# ---------------------------------------------------------------
def validar_nombre_cliente(nombre):
    """Más de 4 y menos de 20 caracteres: solo letras y espacios."""
    return re.fullmatch(r"[A-Za-zÁÉÍÓÚÜáéíóúüÑñ ]{5,19}", nombre) is not None


def validar_documento(documento):
    """DNI (8 dígitos) o RUC (11 dígitos)."""
    return re.fullmatch(r"\d{8}|\d{11}", documento) is not None


def pedir_nombre_cliente():
    while True:
        nombre = " ".join(input("Nombre del cliente: ").split())
        if validar_nombre_cliente(nombre):
            return nombre
        print(" Nombre inválido: use solo letras, más de 4 y menos de 20 caracteres.")


def pedir_documento():
    while True:
        documento = input("DNI (8 dígitos) o RUC (11 dígitos): ").strip()
        if validar_documento(documento):
            return documento
        print(" Documento inválido: el DNI tiene 8 dígitos y el RUC 11.")


def pedir_si_no(mensaje):
    while True:
        respuesta = input(f"{mensaje} (s/n): ").strip().lower()
        if respuesta in ("s", "si", "sí"):
            return True
        if respuesta in ("n", "no"):
            return False
        print("Responda con s o n.")


def mensaje_stock_insuficiente(disponible, nombre):
    if disponible <= 0:
        return f"Stock insuficiente----No quedan unidades disponibles de {nombre}"
    if disponible == 1:
        return f"Stock insuficiente----Solo queda 1 unidad disponible de {nombre}"
    return f"❌ Stock insuficiente----Solo quedan {disponible} unidades disponibles de {nombre}"




# ---------------------------------------------------------------
# Calculos (funciones puras: no usan la base de datos):
# ---------------------------------------------------------------
def calcular_totales(carrito):
    """
    Aqui vemos el subtotal, descuento, total a pagar, base imponible e IGV incluido.
    Los precios ya incluyen IGV, por eso: base = total / 1.18.
    """
    subtotal = round(sum(i["cantidad"] * i["precio"] for i in carrito), 2)
    descuento = 0.0
    if subtotal > UMBRAL_DESCUENTO:
        descuento = round(subtotal * PORCENTAJE_DESCUENTO / 100, 2)
    total = round(subtotal - descuento, 2)
    base = round(total / (1 + IGV), 2)
    igv = round(total - base, 2)
    return {"subtotal": subtotal, "descuento": descuento,
            "total": total, "base": base, "igv": igv}


def tipo_comprobante(documento):
    """RUC (11 dígitos) -> FACTURA; DNI (8 dígitos) -> BOLETA."""
    if len(documento) == 11:
        return "FACTURA", SERIE_FACTURA
    return "BOLETA DE VENTA", SERIE_BOLETA


def siguiente_numero(serie):
    """Siguiente numero correlativo de la serie: B001-0001, B001-0002, ..."""
    with conectar() as conexion:
        fila = conexion.execute(
            """SELECT MAX(CAST(SUBSTR(numero_comprobante, 6) AS INTEGER)) AS ultimo
               FROM comprobantes WHERE numero_comprobante LIKE ?""",
            (f"{serie}-%",),
        ).fetchone()
    return f"{serie}-{(fila['ultimo'] or 0) + 1:04d}"


# ---------------------------------------------------------------
# Carrito de la venta:
# ---------------------------------------------------------------
def agregar_producto(carrito):
    """Pide codigo y cantidad y lo agrega al carrito este es True si se agrego"""
    codigo = input("Código del producto (ej. ING-0001): ").strip().upper()
    producto = obtener_producto(codigo)

    if producto is None:
        print(f"Al parecer NO existe ningun producto con el codigo {codigo}.")
        return False

    if meses_para_vencer(producto["fecha_vencimiento"]) < 0:
        print(f"⛔ {producto['nombre']} está VENCIDO ({producto['fecha_vencimiento']}). No se puede vender.")
        return False

    ya_en_carrito = sum(i["cantidad"] for i in carrito if i["codigo"] == codigo)
    disponible = producto["stock"] - ya_en_carrito
    if disponible <= 0:
        print(mensaje_stock_insuficiente(disponible, producto["nombre"]))
        return False

    cantidad = pedir_cantidad("Cantidad de unidades vendidas: ")
    if cantidad > disponible:
        print(mensaje_stock_insuficiente(disponible, producto["nombre"]))
        return False

    for item in carrito:  # si ya estaba en el carrito, se suman las unidades
        if item["codigo"] == codigo:
            item["cantidad"] += cantidad
            item["stock_restante"] = disponible - cantidad
            return True

    carrito.append({
        "codigo": codigo,
        "nombre": producto["nombre"],
        "presentacion": producto["presentacion"],
        "vencimiento": producto["fecha_vencimiento"],
        "precio": producto["precio_unitario"],
        "cantidad": cantidad,
        "stock_restante": disponible - cantidad,
    })
    return True


def mostrar_carrito(carrito):
    imprimir_tabla(
        ["Producto", "Código", "Valor unit.", "Cant. vendida", "Stock tras la venta"],
        [(i["nombre"], i["codigo"], f"S/ {i['precio']:.2f}",
          i["cantidad"], i["stock_restante"]) for i in carrito],
    )




# ---------------------------------------------------------------
# Guardado en la base de datos (una sola transacción)
# ---------------------------------------------------------------
def guardar_venta(comprobante, carrito, totales):
    """
    Guarda comprobante + detalle y descuenta el stock en caso de que algo falle, no se guarda nada (rollback automático).
    """
    with conectar() as conexion:
        conexion.execute(
            """INSERT INTO comprobantes
               (numero_comprobante, cliente_nombre, cliente_documento, fecha_hora,
                subtotal, descuento, igv, total, vendedor)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (comprobante["numero"], comprobante["cliente"], comprobante["documento"],
             comprobante["fecha_hora"], totales["subtotal"], totales["descuento"],
             totales["igv"], totales["total"], comprobante["vendedor"]),
        )
        for item in carrito:
            actualizado = conexion.execute(
                "UPDATE productos SET stock = stock - ? WHERE codigo = ? AND stock >= ?",
                (item["cantidad"], item["codigo"], item["cantidad"]),
            )
            if actualizado.rowcount == 0:
                raise ValueError(mensaje_stock_insuficiente(0, item["nombre"]))
            conexion.execute(
                """INSERT INTO ventas
                   (numero_comprobante, codigo_producto, nombre_producto, cantidad_vendida,
                    precio_unitario, total_venta, fecha_venta, vendedor)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (comprobante["numero"], item["codigo"], item["nombre"], item["cantidad"],
                 item["precio"], round(item["cantidad"] * item["precio"], 2),
                 comprobante["fecha_hora"][:10], comprobante["vendedor"]),
            )




# ---------------------------------------------------------------
# Impresion del comprobante:
# ---------------------------------------------------------------
def linea_total(etiqueta, monto):
    print(f"{etiqueta:>{ANCHO - 14}} S/ {monto:>9.2f}")


def imprimir_comprobante(comprobante, carrito, totales):
    tipo, _ = tipo_comprobante(comprobante["documento"])
    etiqueta_doc = "RUC" if len(comprobante["documento"]) == 11 else "DNI"

    print("\n" + "=" * ANCHO)
    print(NOMBRE_FARMACIA.center(ANCHO))
    print(f"RUC: {RUC_FARMACIA}".center(ANCHO))
    print(tipo.center(ANCHO))
    print(f"N° {comprobante['numero']}".center(ANCHO))
    print("=" * ANCHO)
    print(f"Cliente     : {comprobante['cliente']}")
    print(f"{etiqueta_doc:<12}: {comprobante['documento']}")
    print(f"Fecha y hora: {comprobante['fecha_hora']}")
    print(f"Vendedor(a) : {comprobante['vendedor']}")
    print("-" * ANCHO)

    imprimir_tabla(
        ["Código", "Producto", "Present.", "F. venc.", "Cant.", "P. unit.", "Subtotal"],
        [(i["codigo"], i["nombre"], i["presentacion"], i["vencimiento"], i["cantidad"],
          f"{i['precio']:.2f}", f"{i['cantidad'] * i['precio']:.2f}") for i in carrito],
    )

    linea_total("Subtotal general:", totales["subtotal"])
    if totales["descuento"] > 0:
        linea_total(f"Descuento ({PORCENTAJE_DESCUENTO}%):", -totales["descuento"])
    linea_total("TOTAL A PAGAR:", totales["total"])
    print("-" * ANCHO)
    linea_total("Op. gravada (base imponible):", totales["base"])
    linea_total(f"IGV {int(IGV * 100)}% (incluido en el precio):", totales["igv"])
    print("=" * ANCHO)
    print("¡Gracias por su compra!".center(ANCHO))
    print("=" * ANCHO)

    print("\nStock restante (control interno):")
    imprimir_tabla(
        ["Código", "Producto", "Stock disponible"],
        [(i["codigo"], i["nombre"], i["stock_restante"]) for i in carrito],
    )


# ---------------------------------------------------------------
# Opción 4: Registrar productos vendidos:
# ---------------------------------------------------------------
def registrar_venta(vendedor):
    print("\n--- REGISTRAR PRODUCTOS VENDIDOS ---")
    carrito = []

    while True:
        if agregar_producto(carrito):
            print("\nProductos de esta venta:")
            mostrar_carrito(carrito)
        if not pedir_si_no("¿Agregar otro producto?"):
            break

    if not carrito:
        print("Venta cancelada: no se agrego ningun producto")
        return

    print("\n--- DATOS DEL CLIENTE ---")
    cliente = pedir_nombre_cliente()
    documento = pedir_documento()

    totales = calcular_totales(carrito)
    print(f"\nSubtotal: S/ {totales['subtotal']:.2f} | "
          f"Descuento: S/ {totales['descuento']:.2f} | "
          f"Total a pagar: S/ {totales['total']:.2f}")
    if not pedir_si_no("¿Confirmar la venta?"):
        print("Venta cancelada----No se modifico el stock")
        return

    _, serie = tipo_comprobante(documento)
    comprobante = {
        "numero": siguiente_numero(serie),
        "cliente": cliente,
        "documento": documento,
        "fecha_hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "vendedor": vendedor,
    }

    try:
        guardar_venta(comprobante, carrito, totales)
    except ValueError as error:
        print(f"{error}\nLa venta no se guardo")
        return

    imprimir_comprobante(comprobante, carrito, totales)




# ---------------------------------------------------------------
# Opción 5: Lista de productos vendidos:
# ---------------------------------------------------------------
def pedir_fecha_consulta():
    """Enter = hoy. También acepta una fecha DD/MM/AAAA de días anteriores """
    while True:
        texto = input("Fecha a consultar (DD/MM/AAAA) o Enter para hoy: ").strip()
        if texto == "":
            return fecha_hoy()
        try:
            return datetime.strptime(texto, "%d/%m/%Y").strftime("%d/%m/%Y")
        except ValueError:
            print("Fecha inválida-----Use DD/MM/AAAA, por ejemplo (25/11/2026)")


def lista_ventas():
    print("\n--- LISTA DE PRODUCTOS VENDIDOS ---")
    fecha = pedir_fecha_consulta()

    with conectar() as conexion:
        ventas = conexion.execute(
            "SELECT * FROM ventas WHERE fecha_venta = ? ORDER BY id_venta", (fecha,)
        ).fetchall()
        resumen = conexion.execute(
            """SELECT COUNT(*) AS cantidad, COALESCE(SUM(total), 0) AS total
               FROM comprobantes WHERE SUBSTR(fecha_hora, 1, 10) = ?""",
            (fecha,),
        ).fetchone()

    print(f"\nVentas del {fecha}")
    if not ventas:
        print("No se registraron ventas en esa fecha")
        return

    imprimir_tabla(
        ["Comprobante", "Código", "Producto", "Cant.", "P. unit.", "Subtotal", "Vendedor(a)"],
        [(v["numero_comprobante"], v["codigo_producto"], v["nombre_producto"],
          v["cantidad_vendida"], f"S/ {v['precio_unitario']:.2f}",
          f"S/ {v['total_venta']:.2f}", v["vendedor"]) for v in ventas],
    )
    unidades = sum(v["cantidad_vendida"] for v in ventas)
    print(f"Comprobantes emitidos : {resumen['cantidad']}")
    print(f"Unidades vendidas     : {unidades}")
    print(f"TOTAL VENDIDO (con descuentos aplicados): S/ {resumen['total']:.2f}")