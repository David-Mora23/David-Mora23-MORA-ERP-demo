"""
utils.py - Funciones comunes, decoradores y utilidades para EasyERP.
"""

import logging
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from database import get_db

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('easyerp')

# Roles válidos del sistema
ROLES_VALIDOS = ['Admin', 'Gerente', 'Vendedor', 'Contador']


def row_to_dict(row):
    """Convierte una fila sqlite3.Row a diccionario."""
    if row is None:
        return None
    return dict(row)


def rows_to_list(rows):
    """Convierte una lista de filas sqlite3.Row a lista de diccionarios."""
    return [dict(r) for r in rows]


def registrar_log(usuario_id, accion, detalle=None):
    """Registra un cambio en la tabla de logs."""
    try:
        conn = get_db()
        conn.execute(
            'INSERT INTO logs (usuario_id, accion, detalle) VALUES (?, ?, ?)',
            (usuario_id, accion, detalle)
        )
        conn.commit()
        conn.close()
        logger.info(f"LOG [{usuario_id}] {accion}: {detalle}")
    except Exception as e:
        logger.error(f"Error al registrar log: {e}")


def token_required(fn):
    """Decorador que requiere un JWT válido para acceder a la ruta."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Token inválido o expirado', 'detalle': str(e)}), 401
    return wrapper


def role_required(*roles):
    """Decorador que verifica que el usuario tenga uno de los roles permitidos."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
                user_id = get_jwt_identity()
                conn = get_db()
                user = conn.execute(
                    'SELECT id, email, rol FROM usuarios WHERE id = ?', (user_id,)
                ).fetchone()
                conn.close()

                if not user:
                    return jsonify({'error': 'Usuario no encontrado'}), 404

                if user['rol'] not in roles:
                    return jsonify({'error': 'No tiene permisos para esta acción'}), 403

                return fn(*args, **kwargs)
            except Exception as e:
                return jsonify({'error': 'Token inválido o expirado'}), 401
        return wrapper
    return decorator


def get_current_user():
    """Obtiene el usuario actual a partir del JWT."""
    user_id = get_jwt_identity()
    conn = get_db()
    user = conn.execute(
        'SELECT id, email, rol, created_at FROM usuarios WHERE id = ?', (user_id,)
    ).fetchone()
    conn.close()
    return row_to_dict(user)


def validate_required(data, fields):
    """
    Valida que los campos requeridos estén presentes y no vacíos.
    Retorna (True, None) si es válido, o (False, mensaje_error).
    """
    if not data:
        return False, 'No se enviaron datos'

    missing = []
    for field in fields:
        if field not in data or data[field] is None or str(data[field]).strip() == '':
            missing.append(field)

    if missing:
        return False, f'Campos requeridos faltantes: {", ".join(missing)}'

    return True, None


def validate_email(email):
    """Validación básica de formato de email."""
    if not email or '@' not in email or '.' not in email.split('@')[-1]:
        return False
    return True


def validate_rol(rol):
    """Valida que el rol sea uno de los permitidos."""
    return rol in ROLES_VALIDOS


def error_response(message, status_code=400):
    """Respuesta de error estandarizada."""
    return jsonify({'error': message}), status_code


def success_response(data, message=None, status_code=200):
    """Respuesta de éxito estandarizada."""
    response = {'data': data}
    if message:
        response['message'] = message
    return jsonify(response), status_code
