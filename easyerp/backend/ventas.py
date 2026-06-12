"""
ventas.py - Módulo de ventas, clientes y facturación.
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from database import get_db
from utils import (
    token_required, validate_required, registrar_log,
    rows_to_list, row_to_dict, error_response, success_response
)

ventas_bp = Blueprint('ventas', __name__, url_prefix='/api/ventas')


@ventas_bp.route('/clientes', methods=['GET'])
@token_required
def listar_clientes():
    """Lista todos los clientes."""
    conn = get_db()
    clientes = conn.execute('SELECT * FROM clientes ORDER BY nombre').fetchall()
    conn.close()
    return success_response(rows_to_list(clientes))


@ventas_bp.route('/clientes', methods=['POST'])
@token_required
def crear_cliente():
    """Crea un nuevo cliente."""
    data = request.get_json()
    valid, msg = validate_required(data, ['nombre'])
    if not valid:
        return error_response(msg)

    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO clientes (nombre, email, telefono, direccion, ruc)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data['nombre'],
        data.get('email', ''),
        data.get('telefono', ''),
        data.get('direccion', ''),
        data.get('ruc', '')
    ))
    conn.commit()
    cliente_id = cursor.lastrowid
    cliente = conn.execute('SELECT * FROM clientes WHERE id = ?', (cliente_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'CLIENTE_CREADO', data['nombre'])
    return success_response(row_to_dict(cliente), 'Cliente creado', 201)


@ventas_bp.route('/facturas', methods=['GET'])
@token_required
def listar_facturas():
    """Lista todas las facturas."""
    estado = request.args.get('estado')
    conn = get_db()

    query = '''
        SELECT f.*, c.nombre as cliente_nombre
        FROM facturas f
        JOIN clientes c ON f.cliente_id = c.id
    '''
    if estado:
        facturas = conn.execute(query + ' WHERE f.estado = ? ORDER BY f.fecha DESC', (estado,)).fetchall()
    else:
        facturas = conn.execute(query + ' ORDER BY f.fecha DESC').fetchall()

    result = []
    for factura in facturas:
        fact_dict = dict(factura)
        items = conn.execute('''
            SELECT fi.*, p.nombre as producto_nombre, p.codigo as producto_codigo
            FROM items_factura fi
            JOIN productos p ON fi.producto_id = p.id
            WHERE fi.factura_id = ?
        ''', (factura['id'],)).fetchall()
        fact_dict['items'] = rows_to_list(items)
        result.append(fact_dict)

    conn.close()
    return success_response(result)


@ventas_bp.route('/facturas', methods=['POST'])
@token_required
def crear_factura():
    """Crea una nueva factura de venta."""
    data = request.get_json()
    valid, msg = validate_required(data, ['cliente_id', 'fecha', 'items'])
    if not valid:
        return error_response(msg)

    items = data['items']
    if not items or not isinstance(items, list):
        return error_response('La factura debe tener al menos un item')

    conn = get_db()

    cliente = conn.execute('SELECT id FROM clientes WHERE id = ?', (data['cliente_id'],)).fetchone()
    if not cliente:
        conn.close()
        return error_response('Cliente no encontrado', 404)

    total = 0
    for item in items:
        valid, msg = validate_required(item, ['producto_id', 'cantidad', 'precio_unitario'])
        if not valid:
            conn.close()
            return error_response(msg)

        producto = conn.execute('SELECT stock FROM productos WHERE id = ?', (item['producto_id'],)).fetchone()
        if not producto:
            conn.close()
            return error_response(f'Producto {item["producto_id"]} no encontrado', 404)

        if producto['stock'] < int(item['cantidad']):
            conn.close()
            return error_response(f'Stock insuficiente para producto {item["producto_id"]}')

        subtotal = int(item['cantidad']) * float(item['precio_unitario'])
        total += subtotal

    cursor = conn.execute(
        'INSERT INTO facturas (cliente_id, fecha, total, estado) VALUES (?, ?, ?, ?)',
        (data['cliente_id'], data['fecha'], total, data.get('estado', 'pendiente'))
    )
    factura_id = cursor.lastrowid

    for item in items:
        subtotal = int(item['cantidad']) * float(item['precio_unitario'])
        conn.execute('''
            INSERT INTO items_factura (factura_id, producto_id, cantidad, precio_unitario, subtotal)
            VALUES (?, ?, ?, ?, ?)
        ''', (factura_id, item['producto_id'], int(item['cantidad']),
              float(item['precio_unitario']), subtotal))

        # Descontar stock
        conn.execute(
            'UPDATE productos SET stock = stock - ? WHERE id = ?',
            (int(item['cantidad']), item['producto_id'])
        )
        conn.execute('''
            INSERT INTO movimientos_inventario (producto_id, tipo, cantidad, fecha, razon)
            VALUES (?, 'salida', ?, ?, ?)
        ''', (item['producto_id'], int(item['cantidad']), data['fecha'],
              f'Factura #{factura_id}'))

    conn.commit()
    factura = conn.execute('''
        SELECT f.*, c.nombre as cliente_nombre
        FROM facturas f JOIN clientes c ON f.cliente_id = c.id
        WHERE f.id = ?
    ''', (factura_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'FACTURA_CREADA', f'Factura #{factura_id} - Total: ${total}')
    return success_response(row_to_dict(factura), 'Factura creada', 201)


@ventas_bp.route('/reportes', methods=['GET'])
@token_required
def reportes_ventas():
    """Reportes de ventas por periodo, cliente o producto."""
    periodo = request.args.get('periodo')  # YYYY-MM
    cliente_id = request.args.get('cliente_id')
    conn = get_db()

    # Ventas por periodo
    if periodo:
        facturas = conn.execute('''
            SELECT f.*, c.nombre as cliente_nombre
            FROM facturas f JOIN clientes c ON f.cliente_id = c.id
            WHERE strftime('%Y-%m', f.fecha) = ? AND f.estado != 'anulada'
            ORDER BY f.fecha DESC
        ''', (periodo,)).fetchall()
    else:
        facturas = conn.execute('''
            SELECT f.*, c.nombre as cliente_nombre
            FROM facturas f JOIN clientes c ON f.cliente_id = c.id
            WHERE f.estado != 'anulada'
            ORDER BY f.fecha DESC LIMIT 50
        ''').fetchall()

    total_ventas = sum(f['total'] for f in facturas)

    # Top productos vendidos
    top_productos = conn.execute('''
        SELECT p.nombre, p.codigo, SUM(fi.cantidad) as total_vendido,
               SUM(fi.subtotal) as total_ingresos
        FROM items_factura fi
        JOIN productos p ON fi.producto_id = p.id
        JOIN facturas f ON fi.factura_id = f.id
        WHERE f.estado != 'anulada'
        GROUP BY p.id
        ORDER BY total_vendido DESC
        LIMIT 10
    ''').fetchall()

    # Ventas por cliente
    ventas_cliente = conn.execute('''
        SELECT c.nombre, COUNT(f.id) as num_facturas, SUM(f.total) as total_compras
        FROM facturas f
        JOIN clientes c ON f.cliente_id = c.id
        WHERE f.estado != 'anulada'
        GROUP BY c.id
        ORDER BY total_compras DESC
    ''').fetchall()

    conn.close()

    return success_response({
        'periodo': periodo or 'últimas 50 facturas',
        'facturas': rows_to_list(facturas),
        'total_ventas': total_ventas,
        'top_productos': rows_to_list(top_productos),
        'ventas_por_cliente': rows_to_list(ventas_cliente)
    })
