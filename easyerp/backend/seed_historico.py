"""
seed_historico.py - Agrega datos históricos mensuales (2025-2026) a la BD del ERP.
Esto permite que el chatbot IA haga proyecciones basadas en tendencias.
Ejecutar UNA VEZ: python seed_historico.py
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'erp.db')


def seed_historico():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Verificar si ya hay datos históricos (más de 5 facturas)
    count = cursor.execute('SELECT COUNT(*) as c FROM facturas').fetchone()['c']
    if count > 10:
        print("[SEED] Ya hay datos históricos suficientes. Omitiendo.")
        conn.close()
        return

    print("[SEED] Insertando datos históricos 2025-2026...")

    # Obtener IDs existentes
    clientes = [r['id'] for r in cursor.execute('SELECT id FROM clientes').fetchall()]
    productos = cursor.execute('SELECT id, precio_venta, precio_costo FROM productos').fetchall()

    if not clientes or not productos:
        print("[SEED] Error: no hay clientes o productos. Ejecuta primero app.py para crear datos base.")
        conn.close()
        return

    # ── Ventas mensuales (Ene 2025 - May 2026) ──
    # Tendencia creciente con estacionalidad
    meses_ventas = {
        '2025-01': {'min_facturas': 3, 'max_facturas': 5, 'multiplier': 0.8},
        '2025-02': {'min_facturas': 3, 'max_facturas': 5, 'multiplier': 0.85},
        '2025-03': {'min_facturas': 4, 'max_facturas': 6, 'multiplier': 0.9},
        '2025-04': {'min_facturas': 4, 'max_facturas': 6, 'multiplier': 0.95},
        '2025-05': {'min_facturas': 5, 'max_facturas': 7, 'multiplier': 1.0},
        '2025-06': {'min_facturas': 5, 'max_facturas': 8, 'multiplier': 1.05},
        '2025-07': {'min_facturas': 4, 'max_facturas': 6, 'multiplier': 0.95},
        '2025-08': {'min_facturas': 5, 'max_facturas': 7, 'multiplier': 1.0},
        '2025-09': {'min_facturas': 6, 'max_facturas': 8, 'multiplier': 1.1},
        '2025-10': {'min_facturas': 6, 'max_facturas': 9, 'multiplier': 1.15},
        '2025-11': {'min_facturas': 7, 'max_facturas': 10, 'multiplier': 1.25},
        '2025-12': {'min_facturas': 8, 'max_facturas': 12, 'multiplier': 1.4},
        '2026-01': {'min_facturas': 5, 'max_facturas': 7, 'multiplier': 1.1},
        '2026-02': {'min_facturas': 5, 'max_facturas': 8, 'multiplier': 1.15},
        '2026-03': {'min_facturas': 6, 'max_facturas': 9, 'multiplier': 1.2},
        '2026-04': {'min_facturas': 6, 'max_facturas': 9, 'multiplier': 1.25},
        '2026-05': {'min_facturas': 7, 'max_facturas': 10, 'multiplier': 1.3},
    }

    total_facturas_creadas = 0
    total_transacciones_creadas = 0

    for mes_str, config in meses_ventas.items():
        year, month = int(mes_str[:4]), int(mes_str[5:])
        num_facturas = random.randint(config['min_facturas'], config['max_facturas'])

        mes_ingresos = 0
        mes_egresos = 0

        for _ in range(num_facturas):
            # Fecha aleatoria en el mes
            day = random.randint(1, 28)
            fecha = f"{year}-{month:02d}-{day:02d}"

            # Cliente aleatorio
            cliente_id = random.choice(clientes)

            # 1-3 productos por factura
            num_items = random.randint(1, 3)
            total_factura = 0
            items_factura = []

            for _ in range(num_items):
                prod = random.choice(productos)
                cantidad = random.randint(1, 5)
                precio = prod['precio_venta'] * config['multiplier']
                subtotal = round(cantidad * precio, 2)
                total_factura += subtotal
                items_factura.append({
                    'producto_id': prod['id'],
                    'cantidad': cantidad,
                    'precio_unitario': round(precio, 2),
                    'subtotal': subtotal
                })

            total_factura = round(total_factura, 2)
            estado = random.choice(['pagada', 'pagada', 'pagada', 'pendiente'])

            # Insertar factura
            cursor.execute(
                'INSERT INTO facturas (cliente_id, fecha, total, estado) VALUES (?, ?, ?, ?)',
                (cliente_id, fecha, total_factura, estado)
            )
            factura_id = cursor.lastrowid

            # Insertar items
            for item in items_factura:
                cursor.execute('''
                    INSERT INTO items_factura (factura_id, producto_id, cantidad, precio_unitario, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                ''', (factura_id, item['producto_id'], item['cantidad'],
                      item['precio_unitario'], item['subtotal']))

            total_facturas_creadas += 1
            mes_ingresos += total_factura

        # ── Transacciones financieras del mes ──
        # Ingreso por ventas del mes
        if mes_ingresos > 0:
            cursor.execute(
                'INSERT INTO transacciones (tipo, descripcion, monto, fecha, usuario_id) VALUES (?, ?, ?, ?, ?)',
                ('ingreso', f'Ventas del mes {mes_str}', round(mes_ingresos, 2), f'{year}-{month:02d}-28', 1)
            )
            total_transacciones_creadas += 1

        # Egresos del mes (gastos operativos: 30-45% de ingresos)
        gastos_operativos = round(mes_ingresos * random.uniform(0.30, 0.45), 2)
        if gastos_operativos > 0:
            cursor.execute(
                'INSERT INTO transacciones (tipo, descripcion, monto, fecha, usuario_id) VALUES (?, ?, ?, ?, ?)',
                ('egreso', f'Gastos operativos {mes_str}', gastos_operativos, f'{year}-{month:02d}-25', 1)
            )
            total_transacciones_creadas += 1

        # Nómina mensual
        nomina = cursor.execute('SELECT COALESCE(SUM(salario), 0) as total FROM empleados WHERE estado = "activo"').fetchone()['total']
        if nomina > 0:
            cursor.execute(
                'INSERT INTO transacciones (tipo, descripcion, monto, fecha, usuario_id) VALUES (?, ?, ?, ?, ?)',
                ('egreso', f'Nomina {mes_str}', nomina, f'{year}-{month:02d}-30', 1)
            )
            total_transacciones_creadas += 1

        mes_egresos = gastos_operativos + nomina

        print(f"  {mes_str}: {num_facturas} facturas, Ingresos: ${mes_ingresos:,.2f}, Egresos: ${mes_egresos:,.2f}")

    # ── Órdenes de compra históricas ──
    proveedores = [r['id'] for r in cursor.execute('SELECT id FROM proveedores').fetchall()]
    meses_compras = ['2025-02', '2025-05', '2025-08', '2025-11', '2026-01', '2026-04']

    for mes_str in meses_compras:
        year, month = int(mes_str[:4]), int(mes_str[5:])
        proveedor_id = random.choice(proveedores)
        total_orden = round(random.uniform(2000, 8000), 2)

        cursor.execute(
            'INSERT INTO ordenes_compra (proveedor_id, fecha, estado, total) VALUES (?, ?, ?, ?)',
            (proveedor_id, f'{year}-{month:02d}-15', 'recibida', total_orden)
        )

    # ── Registros de asistencia ──
    empleados = [r['id'] for r in cursor.execute('SELECT id FROM empleados').fetchall()]
    for emp_id in empleados:
        for day_offset in range(0, 30, random.choice([1, 2])):
            fecha = (datetime.now() - timedelta(days=day_offset)).strftime('%Y-%m-%d')
            hora_entrada = f"0{random.randint(7,9)}:{random.randint(0,59):02d}"
            hora_salida = f"{random.randint(17,19)}:{random.randint(0,59):02d}"
            cursor.execute(
                'INSERT INTO asistencia (empleado_id, fecha, entrada, salida) VALUES (?, ?, ?, ?)',
                (emp_id, fecha, hora_entrada, hora_salida)
            )

    conn.commit()
    conn.close()

    print(f"\n[SEED] Datos historicos insertados correctamente:")
    print(f"  - {total_facturas_creadas} facturas")
    print(f"  - {total_transacciones_creadas} transacciones")
    print(f"  - {len(meses_compras)} ordenes de compra")
    print(f"  - Registros de asistencia para {len(empleados)} empleados")


if __name__ == '__main__':
    seed_historico()
