"""
compras.py - Módulo de compras y proveedores.
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from database import get_db
from utils import (
    token_required, validate_required, registrar_log,
    rows_to_list, row_to_dict, error_response, success_response
)

compras_bp = Blueprint('compras', __name__, url_prefix='/api/compras')


@compras_bp.route('/proveedores', methods=['GET'])
@token_required
def listar_proveedores():
    """Lista todos los proveedores."""
    conn = get_db()
    proveedores = conn.execute('SELECT * FROM proveedores ORDER BY nombre').fetchall()
    conn.close()
    return success_response(rows_to_list(proveedores))


@compras_bp.route('/proveedores', methods=['POST'])
@token_required
def crear_proveedor():
    """Crea un nuevo proveedor."""
    data = request.get_json()
    valid, msg = validate_required(data, ['nombre'])
    if not valid:
        return error_response(msg)

    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO proveedores (nombre, contacto, email, telefono, direccion)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data['nombre'],
        data.get('contacto', ''),
        data.get('email', ''),
        data.get('telefono', ''),
        data.get('direccion', '')
    ))
    conn.commit()
    prov_id = cursor.lastrowid
    proveedor = conn.execute('SELECT * FROM proveedores WHERE id = ?', (prov_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'PROVEEDOR_CREADO', data['nombre'])
    return success_response(row_to_dict(proveedor), 'Proveedor creado', 201)


@compras_bp.route('/ordenes', methods=['GET'])
@token_required
def listar_ordenes():
    """Lista el historial de órdenes de compra."""
    estado = request.args.get('estado')
    conn = get_db()

    query = '''
        SELECT o.*, p.nombre as proveedor_nombre
        FROM ordenes_compra o
        JOIN proveedores p ON o.proveedor_id = p.id
    '''
    if estado:
        ordenes = conn.execute(query + ' WHERE o.estado = ? ORDER BY o.fecha DESC', (estado,)).fetchall()
    else:
        ordenes = conn.execute(query + ' ORDER BY o.fecha DESC').fetchall()

    result = []
    for orden in ordenes:
        orden_dict = dict(orden)
        items = conn.execute('''
            SELECT io.*, pr.nombre as producto_nombre, pr.codigo as producto_codigo
            FROM items_orden io
            JOIN productos pr ON io.producto_id = pr.id
            WHERE io.orden_id = ?
        ''', (orden['id'],)).fetchall()
        orden_dict['items'] = rows_to_list(items)
        result.append(orden_dict)

    conn.close()
    return success_response(result)


@compras_bp.route('/ordenes', methods=['POST'])
@token_required
def crear_orden():
    """Crea una nueva orden de compra."""
    data = request.get_json()
    valid, msg = validate_required(data, ['proveedor_id', 'fecha', 'items'])
    if not valid:
        return error_response(msg)

    items = data['items']
    if not items or not isinstance(items, list):
        return error_response('La orden debe tener al menos un item')

    conn = get_db()

    proveedor = conn.execute('SELECT id FROM proveedores WHERE id = ?', (data['proveedor_id'],)).fetchone()
    if not proveedor:
        conn.close()
        return error_response('Proveedor no encontrado', 404)

    total = 0
    for item in items:
        valid, msg = validate_required(item, ['producto_id', 'cantidad', 'precio_unitario'])
        if not valid:
            conn.close()
            return error_response(msg)
        total += int(item['cantidad']) * float(item['precio_unitario'])

    cursor = conn.execute(
        'INSERT INTO ordenes_compra (proveedor_id, fecha, estado, total) VALUES (?, ?, ?, ?)',
        (data['proveedor_id'], data['fecha'], 'pendiente', total)
    )
    orden_id = cursor.lastrowid

    for item in items:
        conn.execute(
            'INSERT INTO items_orden (orden_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)',
            (orden_id, item['producto_id'], int(item['cantidad']), float(item['precio_unitario']))
        )

    conn.commit()
    orden = conn.execute('''
        SELECT o.*, p.nombre as proveedor_nombre
        FROM ordenes_compra o
        JOIN proveedores p ON o.proveedor_id = p.id
        WHERE o.id = ?
    ''', (orden_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'ORDEN_COMPRA_CREADA', f'Orden #{orden_id} - Total: ${total}')
    return success_response(row_to_dict(orden), 'Orden de compra creada', 201)


@compras_bp.route('/ordenes/<int:orden_id>', methods=['PUT'])
@token_required
def actualizar_orden(orden_id):
    """Actualiza el estado de una orden de compra."""
    data = request.get_json()
    valid, msg = validate_required(data, ['estado'])
    if not valid:
        return error_response(msg)

    estado = data['estado']
    if estado not in ('pendiente', 'recibida', 'cancelada'):
        return error_response('Estado inválido')

    conn = get_db()
    orden = conn.execute('SELECT * FROM ordenes_compra WHERE id = ?', (orden_id,)).fetchone()
    if not orden:
        conn.close()
        return error_response('Orden no encontrada', 404)

    # Si se marca como recibida, actualizar stock de productos
    if estado == 'recibida' and orden['estado'] != 'recibida':
        items = conn.execute('SELECT * FROM items_orden WHERE orden_id = ?', (orden_id,)).fetchall()
        for item in items:
            conn.execute(
                'UPDATE productos SET stock = stock + ? WHERE id = ?',
                (item['cantidad'], item['producto_id'])
            )
            conn.execute('''
                INSERT INTO movimientos_inventario (producto_id, tipo, cantidad, fecha, razon)
                VALUES (?, 'entrada', ?, date('now'), ?)
            ''', (item['producto_id'], item['cantidad'], f'Orden de compra #{orden_id}'))

    conn.execute('UPDATE ordenes_compra SET estado = ? WHERE id = ?', (estado, orden_id))
    conn.commit()
    orden = conn.execute('SELECT * FROM ordenes_compra WHERE id = ?', (orden_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'ORDEN_ACTUALIZADA', f'Orden #{orden_id} -> {estado}')
    return success_response(row_to_dict(orden), f'Orden actualizada a {estado}')
