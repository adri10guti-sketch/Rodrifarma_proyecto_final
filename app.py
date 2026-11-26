"""
app.py - esta es una version web (Flask) de RODRIFARMA.
Reutiliza la logica de Modulos/; aqui solo se reemplazan input()/print() por formularios.
"""
from datetime import datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for

from Modulos.conexiones_data_base import conectar, inicializar_bd
from Modulos import facturas_y_boletas as fac
from Modulos import gestion as ges
from Modulos import seguridad as seg

app = Flask(__name__)
app.secret_key = "cambia-esta-clave-secreta"  # necesaria para sesiones y mensajes flash
inicializar_bd()

#aqui mostramos:
# ---------------- Sesión y permisos ----------------
def requiere(opcion):
    """Protege una ruta: exige sesión iniciada y permiso para esa opción del menú."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            usuario = session.get("usuario")
            if not usuario:
                return redirect(url_for("login"))
            if not seg.tiene_permiso(usuario["rol"], opcion):
                flash(seg.mensaje_restringido(opcion), "error")
                return redirect(url_for("inicio"))
            return vista(*args, **kwargs)
        return envoltura
    return decorador


@app.context_processor
def datos_globales():
    usuario = session.get("usuario")
    permiso = lambda op: bool(usuario) and seg.tiene_permiso(usuario["rol"], op)
    return {"usuario": usuario, "permiso": permiso}


def intentos_agotados():
    return session.get("intentos", 0) >= seg.MAX_INTENTOS


def fallo_intento(mensaje):
    session["intentos"] = session.get("intentos", 0) + 1
    restantes = seg.MAX_INTENTOS - session["intentos"]
    if restantes <= 0:
        flash("ACCESO DENEGADO :[ (cierre el navegador o reinicie el servidor para volver a intentar)", "error")
    else:
        flash(f"{mensaje}---Intentos restantes: {restantes}", "error")


# ---------------- Acceso ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if intentos_agotados():
            flash("ACCESO DENEGADO :[", "error")
            return render_template("login.html")
        nombre = request.form["nombre"].strip()
        rol = request.form["rol"].strip().lower()
        password = request.form["password"].strip()
        if seg.credenciales_correctas(nombre, rol, password):
            session.clear()
            session["usuario"] = {"nombre": nombre, "rol": rol}
            return redirect(url_for("inicio"))
        fallo_intento("El nombre, el rol o la contraseña no cumplen con los requisitos")
    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        if intentos_agotados():
            flash("ACCESO DENEGADO :[", "error")
            return render_template("registro.html")
        nombre = request.form["nombre"].strip()
        rol = request.form["rol"].strip().lower()
        password = request.form["password"].strip()

        if not seg.validar_nombre(nombre):
            fallo_intento("Nombre inválido (4 a 12 letras minúsculas, sin espacios ni números)")
        elif not seg.validar_rol(rol):
            fallo_intento("Rol inválido")
        elif not seg.validar_password(password):
            fallo_intento("Contraseña incorrecta (6 caracteres, de 1 a 4 letras)")
        elif rol == "administradora":
            if seg.credenciales_correctas(nombre, rol, password):
                session.clear()
                session["usuario"] = {"nombre": nombre, "rol": rol}
                flash("Registro exitoso", "ok")
                return redirect(url_for("inicio"))
            fallo_intento("Acción inválida para ese rol")
        elif seg.buscar_usuario(nombre) is not None:
            fallo_intento("Ese nombre ya está registrado")
        else:
            seg.guardar_usuario(nombre, rol, password)
            session.clear()
            session["usuario"] = {"nombre": nombre, "rol": rol}
            flash("Registro exitoso", "ok")
            return redirect(url_for("inicio"))
    return render_template("registro.html")


@app.route("/salir")
def salir():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@requiere(0)
def inicio():
    return render_template("inicio.html")


# ---------------- 1: Registrar producto ----------------
@app.route("/productos/nuevo", methods=["GET", "POST"])
@requiere(1)
def producto_nuevo():
    if request.method == "POST":
        f = request.form
        nombre = " ".join(f["nombre"].split())
        presentacion = f["presentacion"]
        vencimiento = f["vencimiento"].strip()
        try:
            precio = round(float(f["precio"].replace(",", ".")), 2)
        except ValueError:
            precio = 0
        cantidad_txt = f["stock"].strip()

        if not ges.validar_nombre_producto(nombre):
            flash("Nombre inválido (3 a 40 caracteres: letras, números, espacios y . % / -).", "error")
        elif presentacion not in ges.PRESENTACIONES:
            flash("Presentación inválida.", "error")
        elif not 0 < precio <= ges.PRECIO_MAXIMO:
            flash(f"El precio debe ser mayor que 0 y menor o igual a {ges.PRECIO_MAXIMO}.", "error")
        elif not (cantidad_txt.isdigit() and 1 <= int(cantidad_txt) <= ges.CANTIDAD_MAXIMA):
            flash(f"La cantidad debe ser un entero entre 1 y {ges.CANTIDAD_MAXIMA}.", "error")
        elif not ges.validar_vencimiento(vencimiento):
            flash("Vencimiento inválido. Use MM/AAAA, por ejemplo 08/2027.", "error")
        else:
            codigo = ges.generar_codigo()
            with conectar() as c:
                c.execute(
                    """INSERT INTO productos (codigo, nombre, presentacion, precio_unitario,
                       stock, fecha_registro, fecha_vencimiento) VALUES (?,?,?,?,?,?,?)""",
                    (codigo, nombre, presentacion, precio, int(cantidad_txt),
                     ges.fecha_hoy(), vencimiento),
                )
            flash(f"Producto registrado con el código {codigo}.", "ok")
            return redirect(url_for("productos"))
    return render_template("producto_nuevo.html", presentaciones=ges.PRESENTACIONES)


# ---------------- 2 y 3: Buscar y listar ----------------
@app.route("/productos")
@requiere(3)
def productos():
    q = request.args.get("q", "").strip().upper()
    sql = "SELECT * FROM productos"
    params = ()
    if q:
        sql += " WHERE codigo = ?"
        params = (q,)
    sql += """ ORDER BY nombre COLLATE NOCASE,
               SUBSTR(fecha_registro,7,4)||SUBSTR(fecha_registro,4,2)||SUBSTR(fecha_registro,1,2),
               SUBSTR(fecha_vencimiento,4,4)||SUBSTR(fecha_vencimiento,1,2)"""
    with conectar() as c:
        filas = c.execute(sql, params).fetchall()
    if q and not filas:
        flash(f"No existe ningún producto con el código {q}.", "error")
    return render_template("productos.html", productos=filas, q=q, stock_bajo=ges.STOCK_BAJO)


# ---------------- 7: Actualizar precio ----------------
@app.route("/productos/<codigo>/precio", methods=["GET", "POST"])
@requiere(7)
def actualizar_precio(codigo):
    producto = ges.obtener_producto(codigo)
    if producto is None:
        flash("Producto no encontrado.", "error")
        return redirect(url_for("productos"))
    if request.method == "POST":
        try:
            nuevo = round(float(request.form["precio"].replace(",", ".")), 2)
        except ValueError:
            nuevo = 0
        if 0 < nuevo <= ges.PRECIO_MAXIMO:
            with conectar() as c:
                c.execute("UPDATE productos SET precio_unitario=? WHERE codigo=?", (nuevo, codigo))
            flash(f"Precio actualizado: S/ {producto['precio_unitario']:.2f} → S/ {nuevo:.2f}", "ok")
            return redirect(url_for("productos"))
        flash(f"El precio debe ser mayor que 0 y menor o igual a {ges.PRECIO_MAXIMO}.", "error")
    return render_template("precio.html", producto=producto)


# ---------------- 4: Registrar venta ----------------
def agregar_al_carrito(carrito, codigo, cantidad_txt):
    """Devuelve un mensaje de error, o None si se agregó."""
    codigo = codigo.strip().upper()
    producto = ges.obtener_producto(codigo)
    if producto is None:
        return f"No existe ningún producto con el código {codigo}."
    if ges.meses_para_vencer(producto["fecha_vencimiento"]) < 0:
        return f" {producto['nombre']} está VENCIDO ({producto['fecha_vencimiento']}). No se puede vender."
    if not (cantidad_txt.isdigit() and 1 <= int(cantidad_txt) <= ges.CANTIDAD_MAXIMA):
        return "Ingrese una cantidad entera válida."
    cantidad = int(cantidad_txt)
    disponible = producto["stock"] - sum(i["cantidad"] for i in carrito if i["codigo"] == codigo)
    if disponible <= 0 or cantidad > disponible:
        return fac.mensaje_stock_insuficiente(disponible, producto["nombre"])
    for item in carrito:
        if item["codigo"] == codigo:
            item["cantidad"] += cantidad
            item["stock_restante"] = disponible - cantidad
            return None
    carrito.append({
        "codigo": codigo, "nombre": producto["nombre"],
        "presentacion": producto["presentacion"], "vencimiento": producto["fecha_vencimiento"],
        "precio": producto["precio_unitario"], "cantidad": cantidad,
        "stock_restante": disponible - cantidad,
    })
    return None


@app.route("/vender", methods=["GET", "POST"])
@requiere(4)
def vender():
    carrito = session.get("carrito", [])
    if request.method == "POST":
        accion = request.form.get("accion")
        if accion == "agregar":
            error = agregar_al_carrito(carrito, request.form["codigo"], request.form["cantidad"].strip())
            if error:
                flash(error, "error")
        elif accion == "quitar":
            indice = int(request.form["indice"])
            if 0 <= indice < len(carrito):
                carrito.pop(indice)
        elif accion == "vaciar":
            carrito = []
        elif accion == "confirmar":
            cliente = " ".join(request.form["cliente"].split())
            documento = request.form["documento"].strip()
            if not carrito:
                flash("Agregue al menos un producto.", "error")
            elif not fac.validar_nombre_cliente(cliente):
                flash("Nombre del cliente inválido: solo letras, más de 4 y menos de 20 caracteres.", "error")
            elif not fac.validar_documento(documento):
                flash("Documento inválido: el DNI tiene 8 dígitos y el RUC 11.", "error")
            else:
                totales = fac.calcular_totales(carrito)
                _, serie = fac.tipo_comprobante(documento)
                comprobante = {
                    "numero": fac.siguiente_numero(serie), "cliente": cliente,
                    "documento": documento, "vendedor": session["usuario"]["nombre"],
                    "fecha_hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
                }
                try:
                    fac.guardar_venta(comprobante, carrito, totales)
                except ValueError as error:
                    flash(f"{error} La venta no se guardó.", "error")
                else:
                    session["carrito"] = []
                    return redirect(url_for("comprobante", numero=comprobante["numero"]))
        session["carrito"] = carrito
        return redirect(url_for("vender"))
    totales = fac.calcular_totales(carrito) if carrito else None
    return render_template("vender.html", carrito=carrito, totales=totales)


@app.route("/comprobante/<numero>")
@requiere(4)
def comprobante(numero):
    with conectar() as c:
        cab = c.execute("SELECT * FROM comprobantes WHERE numero_comprobante=?", (numero,)).fetchone()
        det = c.execute(
            """SELECT v.*, p.presentacion, p.fecha_vencimiento, p.stock
               FROM ventas v JOIN productos p ON p.codigo = v.codigo_producto
               WHERE v.numero_comprobante=? ORDER BY v.id_venta""", (numero,)).fetchall()
    if cab is None:
        flash("Comprobante no encontrado.", "error")
        return redirect(url_for("vender"))
    tipo, _ = fac.tipo_comprobante(cab["cliente_documento"])
    return render_template(
        "comprobante.html", c=cab, detalle=det, tipo=tipo,
        etiqueta_doc="RUC" if len(cab["cliente_documento"]) == 11 else "DNI",
        base=round(cab["total"] - cab["igv"], 2), farmacia=fac.NOMBRE_FARMACIA,
        ruc=fac.RUC_FARMACIA, pct=fac.PORCENTAJE_DESCUENTO, igv_pct=int(fac.IGV * 100),
    )


# ---------------- 5: Lista de ventas ----------------
@app.route("/ventas")
@requiere(5)
def ventas():
    texto = request.args.get("fecha", "")
    try:
        fecha = datetime.strptime(texto, "%Y-%m-%d").strftime("%d/%m/%Y") if texto else ges.fecha_hoy()
    except ValueError:
        flash("Fecha inválida.", "error")
        fecha = ges.fecha_hoy()
    with conectar() as c:
        filas = c.execute("SELECT * FROM ventas WHERE fecha_venta=? ORDER BY id_venta", (fecha,)).fetchall()
        resumen = c.execute(
            """SELECT COUNT(*) AS cantidad, COALESCE(SUM(total),0) AS total
               FROM comprobantes WHERE SUBSTR(fecha_hora,1,10)=?""", (fecha,)).fetchone()
    valor_input = datetime.strptime(fecha, "%d/%m/%Y").strftime("%Y-%m-%d")
    return render_template("ventas.html", ventas=filas, resumen=resumen, fecha=fecha,
                           valor_input=valor_input, unidades=sum(v["cantidad_vendida"] for v in filas))


# ---------------- 6: Vencimientos y stock bajo ----------------
@app.route("/vencimientos")
@requiere(6)
def vencimientos():
    with conectar() as c:
        todos = c.execute("SELECT * FROM productos").fetchall()
    alertas = []
    for p in todos:
        meses = ges.meses_para_vencer(p["fecha_vencimiento"])
        if meses < 0:
            alertas.append((meses, p, "VENCIDO"))
        elif meses <= ges.MESES_POR_VENCER:
            alertas.append((meses, p, "POR VENCER"))
    alertas.sort(key=lambda a: a[0])
    bajos = [p for p in todos if p["stock"] <= ges.STOCK_BAJO]
    return render_template("vencimientos.html", alertas=alertas, bajos=bajos,
                           meses=ges.MESES_POR_VENCER, stock_bajo=ges.STOCK_BAJO)


if __name__ == "__main__":
    app.run(debug=True)
