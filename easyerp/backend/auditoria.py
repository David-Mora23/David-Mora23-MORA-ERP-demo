"""
auditoria.py - Registro de actividad del sistema (solo Admin).
"""

from flask import Blueprint, request
from database import get_db
from utils import role_required, rows_to_list, success_response

auditoria_bp = Blueprint('auditoria', __name__, url_prefix='/api/auditoria')


@auditoria_bp.route('/logs', methods=['GET'])
@role_required('Admin')
def listar_logs():
    """Lista logs de auditoría con filtros opcionales."""
    accion = request.args.get('accion', '').strip()
    usuario_id = request.args.get('usuario_id', '').strip()
    desde = request.args.get('desde', '').strip()
    hasta = request.args.get('hasta', '').strip()
    limite = min(int(request.args.get('limite', 200)), 500)

    conn = get_db()
    query = '''
        SELECT l.id, l.usuario_id, l.accion, l.detalle, l.created_at,
               u.email as usuario_email, u.rol as usuario_rol
        FROM logs l
        LEFT JOIN usuarios u ON l.usuario_id = u.id
        WHERE 1=1
    '''
    params = []

    if accion:
        query += ' AND l.accion LIKE ?'
        params.append(f'%{accion}%')
    if usuario_id:
        query += ' AND l.usuario_id = ?'
        params.append(int(usuario_id))
    if desde:
        query += ' AND date(l.created_at) >= date(?)'
        params.append(desde)
    if hasta:
        query += ' AND date(l.created_at) <= date(?)'
        params.append(hasta)

    query += ' ORDER BY l.created_at DESC LIMIT ?'
    params.append(limite)

    logs = conn.execute(query, params).fetchall()

    stats = conn.execute('''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN accion = 'LOGIN' THEN 1 ELSE 0 END) as logins,
            SUM(CASE WHEN date(created_at) = date('now') THEN 1 ELSE 0 END) as hoy
        FROM logs
    ''').fetchone()

    acciones = rows_to_list(conn.execute('''
        SELECT accion, COUNT(*) as total
        FROM logs GROUP BY accion ORDER BY total DESC LIMIT 15
    ''').fetchall())

    conn.close()

    return success_response({
        'logs': rows_to_list(logs),
        'stats': dict(stats),
        'acciones_top': acciones,
    })
