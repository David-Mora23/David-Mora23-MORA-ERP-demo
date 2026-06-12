"""
auth.py - Módulo de autenticación: login, perfil y gestión de usuarios (Admin).
"""

import bcrypt
from flask import Blueprint, request
from flask_jwt_extended import create_access_token, get_jwt_identity
from database import get_db
from utils import (
    token_required, get_current_user, validate_required,
    validate_email, validate_rol, registrar_log, error_response,
    success_response, role_required, rows_to_list, row_to_dict
)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _crear_usuario_en_bd(email, password, rol):
    """Crea un usuario y retorna (user_dict, error_message)."""
    if not validate_email(email):
        return None, 'Formato de email inválido'

    if not validate_rol(rol):
        return None, 'Rol inválido. Roles permitidos: Admin, Gerente, Vendedor, Contador'

    if rol == 'Admin':
        return None, 'No se pueden crear usuarios Admin. Solo existe un administrador en el sistema.'

    if len(password) < 6:
        return None, 'La contraseña debe tener al menos 6 caracteres'

    conn = get_db()
    existing = conn.execute('SELECT id FROM usuarios WHERE email = ?', (email,)).fetchone()
    if existing:
        conn.close()
        return None, 'El email ya está registrado'

    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    cursor = conn.execute(
        'INSERT INTO usuarios (email, password_hash, rol) VALUES (?, ?, ?)',
        (email, password_hash, rol)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    return {'id': user_id, 'email': email, 'rol': rol}, None


@auth_bp.route('/registro', methods=['POST'])
@role_required('Admin')
def registro():
    """Registra un nuevo usuario. Solo accesible por Admin."""
    data = request.get_json()
    valid, msg = validate_required(data, ['email', 'password', 'rol'])
    if not valid:
        return error_response(msg)

    email = data['email'].strip().lower()
    user, err = _crear_usuario_en_bd(email, data['password'], data['rol'])
    if err:
        status = 409 if 'registrado' in err else 400
        return error_response(err, status)

    admin_id = get_jwt_identity()
    registrar_log(admin_id, 'REGISTRO', f'Nuevo usuario: {email} ({user["rol"]})')

    return success_response(user, 'Usuario registrado exitosamente', 201)


@auth_bp.route('/usuarios', methods=['GET'])
@role_required('Admin')
def listar_usuarios():
    """Lista todos los usuarios del sistema. Solo Admin."""
    conn = get_db()
    usuarios = conn.execute(
        'SELECT id, email, rol, created_at FROM usuarios ORDER BY created_at DESC'
    ).fetchall()
    conn.close()
    return success_response(rows_to_list(usuarios))


@auth_bp.route('/usuarios', methods=['POST'])
@role_required('Admin')
def crear_usuario():
    """Crea un nuevo usuario. Solo Admin."""
    data = request.get_json()
    valid, msg = validate_required(data, ['email', 'password', 'rol'])
    if not valid:
        return error_response(msg)

    email = data['email'].strip().lower()
    user, err = _crear_usuario_en_bd(email, data['password'], data['rol'])
    if err:
        status = 409 if 'registrado' in err else 400
        return error_response(err, status)

    admin_id = get_jwt_identity()
    registrar_log(admin_id, 'CREAR_USUARIO', f'Usuario creado: {email} ({user["rol"]})')

    return success_response(user, 'Usuario creado exitosamente', 201)


@auth_bp.route('/usuarios/<int:user_id>', methods=['PUT'])
@role_required('Admin')
def actualizar_usuario(user_id):
    """Actualiza email, rol y/o contraseña de un usuario. Solo Admin."""
    data = request.get_json()
    if not data:
        return error_response('No se enviaron datos')

    admin_id = int(get_jwt_identity())
    conn = get_db()
    usuario = conn.execute(
        'SELECT id, email, rol FROM usuarios WHERE id = ?', (user_id,)
    ).fetchone()

    if not usuario:
        conn.close()
        return error_response('Usuario no encontrado', 404)

    nuevo_email = data.get('email', usuario['email']).strip().lower()
    nuevo_rol = data.get('rol', usuario['rol'])
    nueva_password = data.get('password', '').strip()

    if not validate_email(nuevo_email):
        conn.close()
        return error_response('Formato de email inválido')

    if not validate_rol(nuevo_rol):
        conn.close()
        return error_response('Rol inválido. Roles permitidos: Admin, Gerente, Vendedor, Contador')

    if usuario['rol'] == 'Admin' and nuevo_rol != 'Admin':
        conn.close()
        return error_response('El rol del administrador del sistema no puede cambiarse')

    if nuevo_rol == 'Admin' and usuario['rol'] != 'Admin':
        conn.close()
        return error_response('No se puede asignar rol Admin. Solo existe un administrador.')

    if user_id == admin_id and nuevo_rol != 'Admin':
        conn.close()
        return error_response('No puedes cambiar tu propio rol de Administrador')

    if nuevo_email != usuario['email']:
        duplicado = conn.execute(
            'SELECT id FROM usuarios WHERE email = ? AND id != ?', (nuevo_email, user_id)
        ).fetchone()
        if duplicado:
            conn.close()
            return error_response('El email ya está en uso por otro usuario', 409)

    if nueva_password and len(nueva_password) < 6:
        conn.close()
        return error_response('La contraseña debe tener al menos 6 caracteres')

    if nueva_password:
        password_hash = bcrypt.hashpw(
            nueva_password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')
        conn.execute(
            'UPDATE usuarios SET email = ?, rol = ?, password_hash = ? WHERE id = ?',
            (nuevo_email, nuevo_rol, password_hash, user_id)
        )
    else:
        conn.execute(
            'UPDATE usuarios SET email = ?, rol = ? WHERE id = ?',
            (nuevo_email, nuevo_rol, user_id)
        )

    conn.commit()
    actualizado = conn.execute(
        'SELECT id, email, rol, created_at FROM usuarios WHERE id = ?', (user_id,)
    ).fetchone()
    conn.close()

    registrar_log(
        admin_id, 'ACTUALIZAR_USUARIO',
        f'Usuario {user_id} actualizado: {nuevo_email} ({nuevo_rol})'
    )

    return success_response(row_to_dict(actualizado), 'Usuario actualizado exitosamente')


@auth_bp.route('/usuarios/<int:user_id>', methods=['DELETE'])
@role_required('Admin')
def eliminar_usuario(user_id):
    """Elimina un usuario. No permite borrar Admin ni la propia cuenta."""
    admin_id = int(get_jwt_identity())

    if user_id == admin_id:
        return error_response('No puedes eliminar tu propia cuenta de administrador', 403)

    conn = get_db()
    usuario = conn.execute(
        'SELECT id, email, rol FROM usuarios WHERE id = ?', (user_id,)
    ).fetchone()

    if not usuario:
        conn.close()
        return error_response('Usuario no encontrado', 404)

    if usuario['rol'] == 'Admin':
        conn.close()
        return error_response('El administrador del sistema no puede ser eliminado', 403)

    conn.execute('DELETE FROM usuarios WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    registrar_log(
        admin_id, 'ELIMINAR_USUARIO',
        f'Usuario eliminado: {usuario["email"]} ({usuario["rol"]})'
    )

    return success_response({'id': user_id}, 'Usuario eliminado exitosamente')


@auth_bp.route('/login', methods=['POST'])
def login():
    """Autentica un usuario y retorna un token JWT."""
    data = request.get_json()

    valid, msg = validate_required(data, ['email', 'password'])
    if not valid:
        return error_response(msg)

    email = data['email'].strip().lower()
    password = data['password']

    conn = get_db()
    user = conn.execute(
        'SELECT id, email, password_hash, rol FROM usuarios WHERE email = ?', (email,)
    ).fetchone()
    conn.close()

    if not user:
        return error_response('Credenciales inválidas', 401)

    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return error_response('Credenciales inválidas', 401)

    access_token = create_access_token(identity=str(user['id']))

    registrar_log(user['id'], 'LOGIN', f'Inicio de sesión: {email}')

    return success_response({
        'access_token': access_token,
        'user': {
            'id': user['id'],
            'email': user['email'],
            'rol': user['rol']
        }
    }, 'Inicio de sesión exitoso')


@auth_bp.route('/me', methods=['GET'])
@token_required
def me():
    """Retorna la información del usuario autenticado."""
    user = get_current_user()
    if not user:
        return error_response('Usuario no encontrado', 404)
    return success_response(user)


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """Registra cierre de sesión en auditoría."""
    user_id = get_jwt_identity()
    user = get_current_user()
    email = user['email'] if user else user_id
    registrar_log(int(user_id), 'LOGOUT', f'Cierre de sesión: {email}')
    return success_response(None, 'Sesión cerrada')
