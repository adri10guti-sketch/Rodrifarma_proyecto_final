"""
conexiones_data_base.py
----------------------------------------------------------------------
base de datos SQLite de RODRIFARMA: conexion, creación de tablas y usuarios por defecto
Ningún otro módulo debe escribir sqlite3.connect(); todos usan conectar().
"""

import sqlite3
from pathlib import Path

# La base de datos queda en la raíz del proyecto (junto a master.py)
RUTA_BD = Path(__file__).resolve().parent.parent / "rodrifarma.db"


def conectar():
    """Devuelve una conexión lista para usar (claves foráneas activas)"""
    conexion = sqlite3.connect(RUTA_BD)
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.row_factory = sqlite3.Row  
    return conexion


def crear_tablas():
    """Crea las tablas si todavía no existen"""
    with conectar() as conexion:
        conexion.executescript(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                nombre   TEXT PRIMARY KEY,
                rol      TEXT NOT NULL CHECK (rol IN ('administradora', 'asistente')),
                password TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS productos (
                codigo            TEXT PRIMARY KEY,          -- ING-0001
                nombre            TEXT NOT NULL,             -- Paracetamol 500mg
                presentacion      TEXT NOT NULL DEFAULT 'Unidad',
                precio_unitario   REAL NOT NULL CHECK (precio_unitario > 0),
                stock             INTEGER NOT NULL CHECK (stock >= 0),
                fecha_registro    TEXT NOT NULL,             -- DD/MM/AAAA
                fecha_vencimiento TEXT NOT NULL              -- MM/AAAA
            );

            CREATE TABLE IF NOT EXISTS comprobantes (
                numero_comprobante TEXT PRIMARY KEY,         -- B001-0001
                cliente_nombre     TEXT NOT NULL,
                cliente_documento  TEXT NOT NULL,            -- DNI o RUC
                fecha_hora         TEXT NOT NULL,            -- DD/MM/AAAA HH:MM
                subtotal           REAL NOT NULL,
                descuento          REAL NOT NULL DEFAULT 0,
                igv                REAL NOT NULL,
                total              REAL NOT NULL,
                vendedor           TEXT NOT NULL,
                FOREIGN KEY (vendedor) REFERENCES usuarios(nombre)
            );

            CREATE TABLE IF NOT EXISTS ventas (
                id_venta           INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_comprobante TEXT NOT NULL,
                codigo_producto    TEXT NOT NULL,
                nombre_producto    TEXT NOT NULL,
                cantidad_vendida   INTEGER NOT NULL CHECK (cantidad_vendida > 0),
                precio_unitario    REAL NOT NULL,
                total_venta        REAL NOT NULL,
                fecha_venta        TEXT NOT NULL,            -- DD/MM/AAAA
                vendedor           TEXT NOT NULL,
                FOREIGN KEY (numero_comprobante) REFERENCES comprobantes(numero_comprobante),
                FOREIGN KEY (codigo_producto)    REFERENCES productos(codigo),
                FOREIGN KEY (vendedor)           REFERENCES usuarios(nombre)
            );
            """
        )


def insertar_usuarios_por_defecto():
    """Inserta a la administradora y a la asistente (solo si no existen)"""
    usuarios = [
        ("maribel", "administradora", "mari67"),
        ("tamara", "asistente", "3007ma"),
    ]
    with conectar() as conexion:
        conexion.executemany(
            "INSERT OR IGNORE INTO usuarios (nombre, rol, password) VALUES (?, ?, ?)",
            usuarios,
        )


def inicializar_bd():
    """Punto de entrada: deja la base de datos lista para trabajar"""
    crear_tablas()
    insertar_usuarios_por_defecto()


if __name__ == "__main__":
    inicializar_bd()
    print(f"Base de datos lista en: {RUTA_BD}")