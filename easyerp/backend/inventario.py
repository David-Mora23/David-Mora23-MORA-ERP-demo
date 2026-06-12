"""
inventario.py - Módulo de inventario y almacén.
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from database import get_db
from utils import (
    token_required, validate_required, registrar_log,
    rows_to_list, row_to_dict, error_response, success_response
)

inventario_bp = Blueprint('inventario', __name__, url_prefix='/api/inventario')

STOCK_MINIMO = 10  # Umbral para alertas de stock bajo


@inventario_bp.route('/productos', methods=['GET'])
@token_required
def listar_productos():
    """Lista todos los productos del inventario."""
    categoria = request.args.get('categoria')
    conn = get_db()

    if categoria:
        productos = conn.execute(
            'SELECT * FROM productos WHERE categoria = ? ORDER BY nombre', (categoria,)
        ).fetchall()
    else:
        productos = conn.execute('SELECT * FROM productos ORDER BY nombre').fetchall()

    conn.close()
    return success_response(rows_to_list(productos))


@inventario_bp.route('/productos', methods=['POST'])
@token_required
def crear_producto():
    """Crea un nuevo producto en el inventario."""
    data = request.get_json()
    valid, msg = validate_required(data, ['codigo', 'nombre', 'precio_costo', 'precio_venta'])
    if not valid:
        return error_response(msg)

    conn = get_db()

    existing = conn.execute('SELECT id FROM productos WHERE codigo = ?', (data['codigo'],)).fetchone()
    if existing:
        conn.close()
        return error_response('El código de producto ya existe', 409)

    cursor = conn.execute('''
        INSERT INTO productos (codigo, nombre, descripcion, precio_costo, precio_venta, stock, categoria)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['codigo'],
        data['nombre'],
        data.get('descripcion', ''),
        float(data['precio_costo']),
        float(data['precio_venta']),
        int(data.get('stock', 0)),
        data.get('categoria', 'General')
    ))
    conn.commit()
    prod_id = cursor.lastrowid
    producto = conn.execute('SELECT * FROM productos WHERE id = ?', (prod_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'PRODUCTO_CREADO', f'{data["codigo"]} - {data["nombre"]}')
    return success_response(row_to_dict(producto), 'Producto creado', 201)


@inventario_bp.route('/productos/<int:producto_id>', methods=['PUT'])
@token_required
def actualizar_producto(producto_id):
    """Actualiza un producto (stock, precios, etc.)."""
    data = request.get_json()
    conn = get_db()

    producto = conn.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
    if not producto:
        conn.close()
        return error_response('Producto no encontrado', 404)

    campos = []
    valores = []
    for campo in ['nombre', 'descripcion', 'precio_costo', 'precio_venta', 'stock', 'categoria']:
        if campo in data:
            campos.append(f'{campo} = ?')
            valores.append(data[campo])

    if not campos:
        conn.close()
        return error_response('No hay campos para actualizar')

    valores.append(producto_id)
    conn.execute(f'UPDATE productos SET {", ".join(campos)} WHERE id = ?', valores)
    conn.commit()

    producto = conn.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'PRODUCTO_ACTUALIZADO', f'ID {producto_id}')
    return success_response(row_to_dict(producto), 'Producto actualizado')


@inventario_bp.route('/alertas', methods=['GET'])
@token_required
def alertas_stock():
    """Retorna productos con stock bajo el umbral mínimo."""
    umbral = int(request.args.get('umbral', STOCK_MINIMO))
    conn = get_db()
    productos = conn.execute(
        'SELECT * FROM productos WHERE stock <= ? ORDER BY stock ASC', (umbral,)
    ).fetchall()
    conn.close()
    return success_response(rows_to_list(productos))


@inventario_bp.route('/movimientos', methods=['POST'])
@token_required
def registrar_movimiento():
    """Registra una entrada o salida de inventario."""
    data = request.get_json()
    valid, msg = validate_required(data, ['producto_id', 'tipo', 'cantidad', 'fecha'])
    if not valid:
        return error_response(msg)

    tipo = data['tipo']
    if tipo not in ('entrada', 'salida'):
        return error_response('Tipo debe ser "entrada" o "salida"')

    cantidad = int(data['cantidad'])
    if cantidad <= 0:
        return error_response('La cantidad debe ser mayor a 0')

    producto_id = int(data['producto_id'])
    conn = get_db()

    producto = conn.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
    if not producto:
        conn.close()
        return error_response('Producto no encontrado', 404)

    if tipo == 'salida' and producto['stock'] < cantidad:
        conn.close()
        return error_response(f'Stock insuficiente. Disponible: {producto["stock"]}')

    # Actualizar stock
    nuevo_stock = producto['stock'] + cantidad if tipo == 'entrada' else producto['stock'] - cantidad
    conn.execute('UPDATE productos SET stock = ? WHERE id = ?', (nuevo_stock, producto_id))

    cursor = conn.execute('''
        INSERT INTO movimientos_inventario (producto_id, tipo, cantidad, fecha, razon)
        VALUES (?, ?, ?, ?, ?)
    ''', (producto_id, tipo, cantidad, data['fecha'], data.get('razon', '')))
    conn.commit()
    mov_id = cursor.lastrowid
    movimiento = conn.execute('''
        SELECT m.*, p.nombre as producto_nombre, p.codigo as producto_codigo
        FROM movimientos_inventario m
        JOIN productos p ON m.producto_id = p.id
        WHERE m.id = ?
    ''', (mov_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'MOVIMIENTO_INVENTARIO', f'{tipo} {cantidad} unidades producto {producto_id}')
    return success_response(row_to_dict(movimiento), 'Movimiento registrado', 201)
