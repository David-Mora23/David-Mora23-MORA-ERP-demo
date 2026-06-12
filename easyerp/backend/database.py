"""
database.py - Inicialización y gestión de la base de datos SQLite para EasyERP.
"""

import sqlite3
import os
from datetime import datetime, date

# Ruta absoluta de la base de datos
DB_PATH = os.path.join(os.path.dirname(__file__), 'erp.db')


def get_db():
    """Obtiene una conexión a la base de datos con row_factory para dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Crea todas las tablas del sistema ERP."""
    conn = get_db()
    cursor = conn.cursor()

    # --- Tabla de usuarios ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL CHECK(rol IN ('Admin', 'Gerente', 'Vendedor', 'Contador')),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    ''')

    # --- Tabla de log de cambios ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            accion TEXT NOT NULL,
            detalle TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')

    # --- Módulo Finanzas ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cuentas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('activo', 'pasivo', 'ingreso', 'gasto')),
            saldo REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT NOT NULL CHECK(tipo IN ('ingreso', 'egreso')),
            descripcion TEXT NOT NULL,
            monto REAL NOT NULL,
            fecha TEXT NOT NULL,
            usuario_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')

    # --- Módulo Inventario ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            precio_costo REAL NOT NULL DEFAULT 0,
            precio_venta REAL NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            categoria TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimientos_inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('entrada', 'salida')),
            cantidad INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            razon TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    ''')

    # --- Módulo Compras ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            contacto TEXT,
            email TEXT,
            telefono TEXT,
            direccion TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ordenes_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'pendiente' CHECK(estado IN ('pendiente', 'recibida', 'cancelada')),
            total REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items_orden (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orden_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL,
            FOREIGN KEY (orden_id) REFERENCES ordenes_compra(id),
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    ''')

    # --- Módulo Ventas ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT,
            telefono TEXT,
            direccion TEXT,
            ruc TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            total REAL NOT NULL DEFAULT 0,
            estado TEXT NOT NULL DEFAULT 'pendiente' CHECK(estado IN ('pendiente', 'pagada', 'anulada')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items_factura (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (factura_id) REFERENCES facturas(id),
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    ''')

    # ═══════════════════════════════════════════════
    #  Módulo RRHH — Ampliado
    # ═══════════════════════════════════════════════

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cedula TEXT,
            email TEXT,
            puesto TEXT,
            departamento TEXT DEFAULT 'General',
            tipo_contrato TEXT DEFAULT 'fijo' CHECK(tipo_contrato IN ('fijo', 'temporal', 'medio_tiempo')),
            horas_semanales INTEGER DEFAULT 44,
            salario REAL NOT NULL DEFAULT 0,
            fecha_ingreso TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'activo' CHECK(estado IN ('activo', 'inactivo')),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS asistencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            entrada TEXT,
            salida TEXT,
            horas_trabajadas REAL DEFAULT 0,
            horas_extra REAL DEFAULT 0,
            tipo TEXT DEFAULT 'normal' CHECK(tipo IN ('normal', 'tardanza', 'falta_justificada', 'falta_injustificada')),
            observacion TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (empleado_id) REFERENCES empleados(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS horas_extras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            horas REAL NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'normal' CHECK(tipo IN ('normal', 'doble', 'triple')),
            monto REAL NOT NULL DEFAULT 0,
            aprobado INTEGER NOT NULL DEFAULT 0,
            observacion TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (empleado_id) REFERENCES empleados(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incidencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('medica', 'personal', 'disciplinaria', 'accidente', 'otra')),
            descripcion TEXT NOT NULL,
            dias_ausencia INTEGER DEFAULT 0,
            justificada INTEGER DEFAULT 0,
            documento_soporte TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (empleado_id) REFERENCES empleados(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nomina (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empleado_id INTEGER NOT NULL,
            periodo TEXT NOT NULL,
            salario_bruto REAL NOT NULL DEFAULT 0,
            horas_extras_monto REAL NOT NULL DEFAULT 0,
            bonificaciones REAL NOT NULL DEFAULT 0,
            total_ingresos REAL NOT NULL DEFAULT 0,
            deduccion_sfs REAL NOT NULL DEFAULT 0,
            deduccion_afp REAL NOT NULL DEFAULT 0,
            deduccion_iess REAL NOT NULL DEFAULT 0,
            deduccion_isr REAL NOT NULL DEFAULT 0,
            otras_deducciones REAL NOT NULL DEFAULT 0,
            desc_faltas_injustificadas REAL NOT NULL DEFAULT 0,
            total_deducciones REAL NOT NULL DEFAULT 0,
            salario_neto REAL NOT NULL DEFAULT 0,
            estado TEXT NOT NULL DEFAULT 'pendiente' CHECK(estado IN ('pendiente', 'pagada')),
            fecha_pago TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (empleado_id) REFERENCES empleados(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("[DB] Base de datos inicializada correctamente.")


def seed_db():
    """Inserta datos de ejemplo si la base de datos está vacía."""
    import bcrypt
    import random

    conn = get_db()
    cursor = conn.cursor()

    # Verificar si ya hay datos
    cursor.execute("SELECT COUNT(*) as count FROM usuarios")
    if cursor.fetchone()['count'] > 0:
        conn.close()
        print("[DB] Datos de ejemplo ya existen, omitiendo seed.")
        return

    print("[DB] Insertando datos de ejemplo...")

    # --- Usuarios de prueba ---
    usuarios = [
        ('admin@erp.com',    'Admin'),
        ('gerente@erp.com',  'Gerente'),
        ('vendedor@erp.com', 'Vendedor'),
        ('contador@erp.com', 'Contador'),
    ]
    password = 'password123'
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    for email, rol in usuarios:
        cursor.execute(
            'INSERT INTO usuarios (email, password_hash, rol) VALUES (?, ?, ?)',
            (email, password_hash, rol)
        )

    # --- Cuentas financieras ---
    cuentas = [
        ('Caja General', 'activo', 50000.00),
        ('Banco Principal', 'activo', 120000.00),
        ('Cuentas por Cobrar', 'activo', 15000.00),
        ('Cuentas por Pagar', 'pasivo', 8000.00),
        ('Ventas', 'ingreso', 0),
        ('Gastos Operativos', 'gasto', 0),
    ]
    for nombre, tipo, saldo in cuentas:
        cursor.execute(
            'INSERT INTO cuentas (nombre, tipo, saldo) VALUES (?, ?, ?)',
            (nombre, tipo, saldo)
        )

    # --- Transacciones de ejemplo ---
    transacciones = [
        ('ingreso', 'Venta de productos - Enero', 25000.00, '2026-01-15', 1),
        ('egreso', 'Pago de servicios básicos', 3500.00, '2026-01-20', 3),
    ]
    for tipo, desc, monto, fecha, uid in transacciones:
        cursor.execute(
            'INSERT INTO transacciones (tipo, descripcion, monto, fecha, usuario_id) VALUES (?, ?, ?, ?, ?)',
            (tipo, desc, monto, fecha, uid)
        )

    # --- Productos ---
    productos = [
        ('PROD-001', 'Laptop HP 15"', 'Laptop empresarial 8GB RAM', 450.00, 699.99, 25, 'Electrónica'),
        ('PROD-002', 'Mouse Inalámbrico', 'Mouse ergonómico Bluetooth', 12.00, 24.99, 150, 'Accesorios'),
        ('PROD-003', 'Teclado Mecánico', 'Teclado RGB switches blue', 35.00, 79.99, 80, 'Accesorios'),
        ('PROD-004', 'Monitor 24"', 'Monitor Full HD IPS', 120.00, 199.99, 40, 'Electrónica'),
        ('PROD-005', 'Impresora Láser', 'Impresora monocromática', 180.00, 299.99, 15, 'Electrónica'),
        ('PROD-006', 'Escritorio Oficina', 'Escritorio de madera 120cm', 85.00, 149.99, 20, 'Mobiliario'),
        ('PROD-007', 'Silla Ergonómica', 'Silla con soporte lumbar', 95.00, 179.99, 30, 'Mobiliario'),
        ('PROD-008', 'Cable HDMI 2m', 'Cable HDMI 4K', 3.00, 9.99, 200, 'Accesorios'),
        ('PROD-009', 'USB 32GB', 'Memoria flash USB 3.0', 5.00, 12.99, 3, 'Accesorios'),
        ('PROD-010', 'Webcam HD', 'Cámara web 1080p', 25.00, 49.99, 45, 'Electrónica'),
    ]
    for cod, nom, desc, pc, pv, stock, cat in productos:
        cursor.execute(
            'INSERT INTO productos (codigo, nombre, descripcion, precio_costo, precio_venta, stock, categoria) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (cod, nom, desc, pc, pv, stock, cat)
        )

    # --- Clientes ---
    clientes = [
        ('Empresa ABC S.A.', 'contacto@abc.com', '555-0101', 'Av. Principal 100', '20123456789'),
        ('Comercial XYZ', 'ventas@xyz.com', '555-0102', 'Calle Comercio 50', '20987654321'),
        ('Tech Solutions', 'info@techsol.com', '555-0103', 'Zona Industrial', '20456789123'),
        ('Distribuidora Norte', 'norte@dist.com', '555-0104', 'Av. Norte 200', '20789123456'),
        ('Servicios Integrales', 'admin@servint.com', '555-0105', 'Centro Empresarial', '20321654987'),
    ]
    for nom, email, tel, dir_, ruc in clientes:
        cursor.execute(
            'INSERT INTO clientes (nombre, email, telefono, direccion, ruc) VALUES (?, ?, ?, ?, ?)',
            (nom, email, tel, dir_, ruc)
        )

    # --- Proveedores ---
    proveedores = [
        ('TechSupply Corp', 'Juan Pérez', 'compras@techsupply.com', '555-0201', 'Parque Industrial A'),
        ('OfficeMax Distribuidora', 'María López', 'pedidos@officemax.com', '555-0202', 'Zona Franca B'),
        ('Mobiliario Express', 'Carlos Ruiz', 'ventas@mobiliario.com', '555-0203', 'Av. Industrial 300'),
    ]
    for nom, cont, email, tel, dir_ in proveedores:
        cursor.execute(
            'INSERT INTO proveedores (nombre, contacto, email, telefono, direccion) VALUES (?, ?, ?, ?, ?)',
            (nom, cont, email, tel, dir_)
        )

    # ═══════════════════════════════════════════════
    #  Empleados con campos nuevos
    # ═══════════════════════════════════════════════
    empleados = [
        ('Ana García',        '001-1234567-8', 'ana@erp.com',      'Gerente General',   'Administración', 'fijo',      44, 5500.00, '2024-03-15'),
        ('Luis Martínez',     '001-2345678-9', 'luis@erp.com',     'Vendedor Senior',   'Ventas',         'fijo',      44, 3200.00, '2024-06-01'),
        ('Carmen Díaz',       '001-3456789-0', 'carmen@erp.com',   'Contadora',         'Finanzas',       'fijo',      44, 3800.00, '2024-01-10'),
        ('Roberto Sánchez',   '001-4567890-1', 'roberto@erp.com',  'Almacenero',        'Almacén',        'fijo',      44, 2500.00, '2025-02-20'),
        ('Patricia Vega',     '001-5678901-2', 'patricia@erp.com', 'Asistente RRHH',    'RRHH',           'fijo',      44, 2800.00, '2025-08-05'),
    ]
    for nom, ced, email, puesto, depto, contrato, horas, sal, fecha in empleados:
        cursor.execute('''
            INSERT INTO empleados (nombre, cedula, email, puesto, departamento, tipo_contrato, horas_semanales, salario, fecha_ingreso)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nom, ced, email, puesto, depto, contrato, horas, sal, fecha))

    # ═══════════════════════════════════════════════
    #  Asistencia de ejemplo (último mes)
    # ═══════════════════════════════════════════════
    from datetime import timedelta
    hoy = datetime.now()

    emp_ids = [1, 2, 3, 4, 5]
    for emp_id in emp_ids:
        for day_offset in range(0, 25):
            fecha = (hoy - timedelta(days=day_offset)).strftime('%Y-%m-%d')
            dia_semana = (hoy - timedelta(days=day_offset)).weekday()
            if dia_semana >= 5:  # Sábado/Domingo
                continue

            # Variaciones realistas
            r = random.random()
            if r < 0.05:  # 5% falta injustificada
                cursor.execute('''
                    INSERT INTO asistencia (empleado_id, fecha, entrada, salida, horas_trabajadas, horas_extra, tipo, observacion)
                    VALUES (?, ?, NULL, NULL, 0, 0, 'falta_injustificada', 'No se presentó sin aviso')
                ''', (emp_id, fecha))
            elif r < 0.10:  # 5% falta justificada
                cursor.execute('''
                    INSERT INTO asistencia (empleado_id, fecha, entrada, salida, horas_trabajadas, horas_extra, tipo, observacion)
                    VALUES (?, ?, NULL, NULL, 0, 0, 'falta_justificada', 'Permiso aprobado')
                ''', (emp_id, fecha))
            elif r < 0.20:  # 10% tardanza
                entrada_h = random.randint(9, 10)
                entrada_m = random.randint(0, 59)
                salida_h = random.randint(17, 19)
                salida_m = random.randint(0, 59)
                horas_trab = round((salida_h + salida_m / 60) - (entrada_h + entrada_m / 60), 2)
                horas_ext = max(0, round(horas_trab - 8, 2))
                cursor.execute('''
                    INSERT INTO asistencia (empleado_id, fecha, entrada, salida, horas_trabajadas, horas_extra, tipo, observacion)
                    VALUES (?, ?, ?, ?, ?, ?, 'tardanza', 'Llegó tarde')
                ''', (emp_id, fecha, f'{entrada_h:02d}:{entrada_m:02d}', f'{salida_h:02d}:{salida_m:02d}', horas_trab, horas_ext))
            else:  # Normal
                entrada_h = random.randint(7, 8)
                entrada_m = random.randint(0, 30)
                salida_h = random.randint(17, 19)
                salida_m = random.randint(0, 59)
                horas_trab = round((salida_h + salida_m / 60) - (entrada_h + entrada_m / 60), 2)
                horas_ext = max(0, round(horas_trab - 8, 2))
                cursor.execute('''
                    INSERT INTO asistencia (empleado_id, fecha, entrada, salida, horas_trabajadas, horas_extra, tipo, observacion)
                    VALUES (?, ?, ?, ?, ?, ?, 'normal', NULL)
                ''', (emp_id, fecha, f'{entrada_h:02d}:{entrada_m:02d}', f'{salida_h:02d}:{salida_m:02d}', horas_trab, horas_ext))

    # ═══════════════════════════════════════════════
    #  Horas extras de ejemplo
    # ═══════════════════════════════════════════════
    horas_extras_data = [
        (2, '2026-06-02', 2.0,  'normal', 0, 1, 'Cierre de ventas mensual'),
        (2, '2026-06-05', 3.0,  'doble',  0, 1, 'Inventario de fin de mes'),
        (1, '2026-06-03', 1.5,  'normal', 0, 1, 'Reunión con directiva'),
        (3, '2026-06-04', 2.0,  'normal', 0, 1, 'Cierre contable'),
        (4, '2026-06-06', 4.0,  'doble',  0, 1, 'Descarga de mercancía urgente'),
        (5, '2026-06-02', 1.0,  'normal', 0, 1, 'Procesamiento de nómina'),
        (2, '2026-05-15', 2.5,  'normal', 0, 1, 'Evento especial de ventas'),
        (3, '2026-05-28', 3.0,  'normal', 0, 1, 'Auditoría interna'),
        (1, '2026-05-20', 2.0,  'doble',  0, 1, 'Planificación estratégica'),
        (4, '2026-05-10', 3.5,  'normal', 0, 0, 'Reorganización de almacén'),
    ]
    for emp_id, fecha, horas, tipo, monto, aprobado, obs in horas_extras_data:
        # Calcular monto basado en salario del empleado
        sal = cursor.execute('SELECT salario, horas_semanales FROM empleados WHERE id = ?', (emp_id,)).fetchone()
        tarifa_hora = sal['salario'] / (sal['horas_semanales'] * 4.33)
        multiplicador = {'normal': 1.5, 'doble': 2.0, 'triple': 3.0}[tipo]
        monto_calc = round(tarifa_hora * horas * multiplicador, 2)
        cursor.execute('''
            INSERT INTO horas_extras (empleado_id, fecha, horas, tipo, monto, aprobado, observacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (emp_id, fecha, horas, tipo, monto_calc, aprobado, obs))

    # ═══════════════════════════════════════════════
    #  Incidencias de ejemplo
    # ═══════════════════════════════════════════════
    incidencias_data = [
        (2, '2026-05-20', 'medica',       'Consulta médica programada — Certificado presentado', 1, 1, 'certificado_medico.pdf'),
        (4, '2026-06-01', 'personal',     'Trámite legal — Citación judicial',                   1, 1, 'citacion.pdf'),
        (3, '2026-05-15', 'medica',       'Cirugía menor — Reposo médico',                       3, 1, 'orden_medica.pdf'),
        (1, '2026-06-05', 'personal',     'Fallecimiento de familiar directo',                   3, 1, 'acta_defuncion.pdf'),
        (5, '2026-05-28', 'disciplinaria','Llegadas tardías reiteradas — Amonestación verbal',   0, 0, None),
        (2, '2026-06-08', 'accidente',    'Resbalón en piso mojado — Sin lesión grave',          0, 1, 'reporte_accidente.pdf'),
        (4, '2026-05-05', 'medica',       'Gripe fuerte — Reposo en casa',                       2, 1, 'receta_medica.pdf'),
        (5, '2026-06-03', 'otra',         'Capacitación externa obligatoria',                    1, 1, 'constancia_capacitacion.pdf'),
    ]
    for emp_id, fecha, tipo, desc, dias, justificada, doc in incidencias_data:
        cursor.execute('''
            INSERT INTO incidencias (empleado_id, fecha, tipo, descripcion, dias_ausencia, justificada, documento_soporte)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (emp_id, fecha, tipo, desc, dias, justificada, doc))

    # ═══════════════════════════════════════════════
    #  Nóminas de ejemplo (últimos 2 meses)
    # ═══════════════════════════════════════════════
    periodos = ['2026-04', '2026-05']
    for periodo in periodos:
        for emp_id in emp_ids:
            sal = cursor.execute('SELECT salario FROM empleados WHERE id = ?', (emp_id,)).fetchone()['salario']

            # Horas extras del periodo
            he_monto = cursor.execute('''
                SELECT COALESCE(SUM(monto), 0) as total FROM horas_extras
                WHERE empleado_id = ? AND strftime('%Y-%m', fecha) = ? AND aprobado = 1
            ''', (emp_id, periodo)).fetchone()['total']

            bonificaciones = 0.0
            total_ingresos = sal + he_monto + bonificaciones

            # Deducciones
            deduccion_sfs = round(total_ingresos * 0.0304, 2)
            deduccion_afp = round(total_ingresos * 0.0287, 2)
            deduccion_iess = round(total_ingresos * 0.0945, 2)

            # ISR simplificado (escala RD)
            ingreso_anual = total_ingresos * 12
            if ingreso_anual <= 416220:
                deduccion_isr = 0
            elif ingreso_anual <= 624329:
                deduccion_isr = round(((ingreso_anual - 416220) * 0.15) / 12, 2)
            elif ingreso_anual <= 867123:
                deduccion_isr = round((31216 + (ingreso_anual - 624329) * 0.20) / 12, 2)
            else:
                deduccion_isr = round((79775 + (ingreso_anual - 867123) * 0.25) / 12, 2)

            # Faltas injustificadas
            faltas = cursor.execute('''
                SELECT COUNT(*) as total FROM asistencia
                WHERE empleado_id = ? AND strftime('%Y-%m', fecha) = ? AND tipo = 'falta_injustificada'
            ''', (emp_id, periodo)).fetchone()['total']
            tarifa_diaria = sal / 23.83  # promedio días laborables
            desc_faltas = round(faltas * tarifa_diaria, 2)

            total_deducciones = round(deduccion_sfs + deduccion_afp + deduccion_iess + deduccion_isr + desc_faltas, 2)
            salario_neto = round(total_ingresos - total_deducciones, 2)

            cursor.execute('''
                INSERT INTO nomina (empleado_id, periodo, salario_bruto, horas_extras_monto, bonificaciones,
                    total_ingresos, deduccion_sfs, deduccion_afp, deduccion_iess, deduccion_isr, otras_deducciones,
                    desc_faltas_injustificadas, total_deducciones, salario_neto, estado, fecha_pago)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pagada', ?)
            ''', (emp_id, periodo, sal, he_monto, bonificaciones, total_ingresos,
                  deduccion_sfs, deduccion_afp, deduccion_iess, deduccion_isr, 0, desc_faltas,
                  total_deducciones, salario_neto, f'{periodo}-30'))

    conn.commit()
    conn.close()
    print("[DB] Datos de ejemplo insertados correctamente.")
    print("[DB] Usuarios: admin@erp.com / gerente@erp.com / vendedor@erp.com / contador@erp.com (password: password123)")


if __name__ == '__main__':
    init_db()
    seed_db()
