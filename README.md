# RODRIFARMA

Sistema de gestión de inventario y ventas para la botica RODRIFARMA (Cajamarca, Perú). Desarrollado en Python con SQLite y una interfaz web hecha con Flask, como proyecto final del curso Fundamentos de Programación (CIIN1205P) de la UPN.

## Problema que resuelve

La botica llevaba el ingreso de productos y el control de fechas de vencimiento a mano, en un cuaderno. Esto causaba búsquedas de 10 a 20 minutos, hojas perdidas o deterioradas, letra difícil de leer y ninguna alerta de productos por vencer y por eso RODRIFARMA automatiza ese proceso: registra productos, controla el stock, alerta sobre vencimientos y emite comprobantes de venta.

## Funcionalidades

1. Registrar producto recibido (el código ING-0001 se genera solo).
2. Buscar registro por código.
3. Mostrar listado de todos los registros (ordenado por nombre y fechas).
4. Registrar productos vendidos (con carrito, descuento y comprobante).
5. Lista de productos vendidos por día.
6. Ver productos vencidos y por vencer (3 meses o menos), con alerta de stock bajo (5 unidades o menos).
7. Actualizar precio unitario.
0. Salir (los datos se guardan automáticamente).

### Roles y permisos

- **Administradora:** tendriamos el acceso a todas las opciones que tiene nuestro listado.
- **Asistente:** si ingresamos de esta forma el acceso es limitado y solo nos permite acceder a las opciones 2, 3, 4 y 6.
- El inicio de sesión se da con un máximo 3 intentos si los agotamos nos niega el ingreso
- El rol de administradora no se puede crear: solopuede ingresa quien conoce sus credenciales.

### Reglas de negocio

- No se pueden vender productos vencidos ni cantidades mayores al stock.
- Descuento del 10% si la compra supera S/ 100.
- Precios con IGV incluido (18%).
- Boleta (serie B001) si el cliente da DNI de 8 dígitos; factura (serie F001) si da RUC de 11 dígitos.
- La venta que realicemos se guarda en una sola transacción: si algo falla, no se guarda nada.

## Estructura del proyecto

```
Rodrifarma proyecto/
├── master.py                    # Versión de consola (menú por texto)
├── app.py                       # Versión web con Flask (rutas)
├── rodrifarma.db                # Base de datos SQLite 
├── Modulos/
│   ├── conexiones_data_base.py  # Conexión, tablas y usuarios por defecto
│   ├── seguridad.py             # Registro, login, validaciones y permisos por rol
│   ├── gestion.py               # Inventario: opciones 1, 2, 3, 6 y 7
│   └── facturas_y_boletas.py    # Ventas y comprobantes: opciones 4 y 5
├── templates/                   # Pantallas HTML
└── static/
    └── style.css                # Estilos
```

La lógica del negocio está en `Modulos` y se comparte entre la versión de consola y la web. Las plantillas HTML solo muestran datos y recogen formularios.

## Base de datos (SQLite)

Cuatro tablas: `usuarios`, `productos`, `comprobantes` y `ventas`, relacionadas con claves foráneas.

## Cómo ejecutarlo

1. Instalar Python 3 y Flask: `pip install flask`
2. Versión web: `python app.py` y abrir http://127.0.0.1:5000
3. Versión de consola: `python master.py`

-La base de datos se crea sola la primera vez.

## Usuarios de prueba

- Administradora: nombre `maribel`, rol `administradora`, contraseña `mari67`.
- Asistente: nombre `tamara`, rol `asistente`, contraseña `3007ma`

(Las contraseñas están en `conexiones_data_base.py` y tmb en la tabla de ususarios.)

## Control de versiones

El desarrollo se registró con commits progresivos en Git y GitHub.

## Limitaciones y mejoras futuras

- Las contraseñas se guardan en texto plano; se podria usar hash.
- Agregar respaldo de datos en archivo de texto o CSV.
- Registrar lote y registro sanitario de cada producto.
- entre otros.
