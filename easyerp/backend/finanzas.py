"""
finanzas.py - Módulo de finanzas y contabilidad.
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from database import get_db
from utils import (
    token_required, validate_required, registrar_log,
    rows_to_list, row_to_dict, error_response, success_response
)

finanzas_bp = Blueprint('finanzas', __name__, url_prefix='/api/finanzas')


def _flujo_mensual(conn, meses=6):
    rows = conn.execute('''
        SELECT strftime('%Y-%m', fecha) as mes,
               COALESCE(SUM(CASE WHEN tipo = 'ingreso' THEN monto ELSE 0 END), 0) as ingresos,
               COALESCE(SUM(CASE WHEN tipo = 'egreso' THEN monto ELSE 0 END), 0) as egresos
        FROM transacciones
        GROUP BY mes
        ORDER BY mes DESC
        LIMIT ?
    ''', (meses,)).fetchall()

    return [{
        'mes': r['mes'],
        'ingresos': r['ingresos'],
        'egresos': r['egresos'],
        'balance': r['ingresos'] - r['egresos'],
    } for r in rows]


@finanzas_bp.route('/transacciones', methods=['GET'])
@token_required
def listar_transacciones():
    """Lista todas las transacciones financieras."""
    conn = get_db()
    transacciones = conn.execute('''
        SELECT t.*, u.email as usuario_email
        FROM transacciones t
        LEFT JOIN usuarios u ON t.usuario_id = u.id
        ORDER BY t.fecha DESC
    ''').fetchall()
    conn.close()
    return success_response(rows_to_list(transacciones))


@finanzas_bp.route('/transacciones', methods=['POST'])
@token_required
def crear_transaccion():
    """Crea una nueva transacción financiera."""
    data = request.get_json()
    valid, msg = validate_required(data, ['tipo', 'descripcion', 'monto', 'fecha'])
    if not valid:
        return error_response(msg)

    tipo = data['tipo']
    if tipo not in ('ingreso', 'egreso'):
        return error_response('Tipo debe ser "ingreso" o "egreso"')

    try:
        monto = float(data['monto'])
        if monto <= 0:
            return error_response('El monto debe ser mayor a 0')
    except (ValueError, TypeError):
        return error_response('Monto inválido')

    user_id = get_jwt_identity()
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO transacciones (tipo, descripcion, monto, fecha, usuario_id) VALUES (?, ?, ?, ?, ?)',
        (tipo, data['descripcion'], monto, data['fecha'], user_id)
    )
    conn.commit()
    trans_id = cursor.lastrowid
    transaccion = conn.execute('SELECT * FROM transacciones WHERE id = ?', (trans_id,)).fetchone()
    conn.close()

    registrar_log(int(user_id), 'TRANSACCION_CREADA', f'{tipo} ${monto}: {data["descripcion"]}')
    return success_response(row_to_dict(transaccion), 'Transacción creada', 201)


@finanzas_bp.route('/resumen', methods=['GET'])
@token_required
def resumen_financiero():
    """Retorna resumen financiero: saldos y movimientos."""
    conn = get_db()

    cuentas = rows_to_list(conn.execute('SELECT * FROM cuentas ORDER BY tipo, nombre').fetchall())

    ingresos = conn.execute(
        "SELECT COALESCE(SUM(monto), 0) as total FROM transacciones WHERE tipo = 'ingreso'"
    ).fetchone()['total']

    egresos = conn.execute(
        "SELECT COALESCE(SUM(monto), 0) as total FROM transacciones WHERE tipo = 'egreso'"
    ).fetchone()['total']

    total_cuentas = conn.execute(
        "SELECT COALESCE(SUM(saldo), 0) as total FROM cuentas WHERE tipo IN ('activo', 'ingreso')"
    ).fetchone()['total']

    mes_row = conn.execute('''
        SELECT
            COALESCE(SUM(CASE WHEN tipo = 'ingreso' THEN monto END), 0) as ingresos,
            COALESCE(SUM(CASE WHEN tipo = 'egreso' THEN monto END), 0) as egresos
        FROM transacciones
        WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
    ''').fetchone()

    flujo = _flujo_mensual(conn)
    balance = ingresos - egresos
    mes_ing = mes_row['ingresos']
    mes_egr = mes_row['egresos']

    conn.close()

    return success_response({
        'cuentas': cuentas,
        'total_ingresos': ingresos,
        'total_egresos': egresos,
        'balance': balance,
        'saldo_cuentas': total_cuentas,
        'mes_actual': {
            'ingresos': mes_ing,
            'egresos': mes_egr,
            'balance': mes_ing - mes_egr,
        },
        'flujo_mensual': flujo,
        'nota_balance': (
            'El balance acumulado es Ingresos − Egresos de todas las transacciones. '
            'En los datos demo, la nómina mensual fija (~US$17,800) supera las ventas '
            'registradas en varios meses, por eso puede verse negativo. '
            'La liquidez en cuentas (activos) es independiente de este resultado.'
        ),
    })


@finanzas_bp.route('/reportes', methods=['GET'])
@token_required
def reporte_mensual():
    """Genera reporte mensual de transacciones."""
    mes = request.args.get('mes')  # formato: YYYY-MM
    conn = get_db()

    if mes:
        transacciones = conn.execute('''
            SELECT * FROM transacciones
            WHERE strftime('%Y-%m', fecha) = ?
            ORDER BY fecha DESC
        ''', (mes,)).fetchall()
    else:
        transacciones = conn.execute('''
            SELECT * FROM transacciones
            ORDER BY fecha DESC LIMIT 100
        ''').fetchall()

    ingresos = sum(t['monto'] for t in transacciones if t['tipo'] == 'ingreso')
    egresos = sum(t['monto'] for t in transacciones if t['tipo'] == 'egreso')

    conn.close()

    return success_response({
        'periodo': mes or 'últimos 100 registros',
        'transacciones': rows_to_list(transacciones),
        'total_ingresos': ingresos,
        'total_egresos': egresos,
        'balance': ingresos - egresos
    })
