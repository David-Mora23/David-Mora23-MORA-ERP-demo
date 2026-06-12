"""
rrhh.py - Módulo de recursos humanos completo.
Gestión de empleados, asistencia, horas extras, incidencias y nómina.
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from database import get_db
from utils import (
    token_required, validate_required, registrar_log,
    rows_to_list, row_to_dict, error_response, success_response
)

rrhh_bp = Blueprint('rrhh', __name__, url_prefix='/api/rrhh')

# ═══════════════════════════════════════════════
#  Constantes de deducciones (Ecuador 2026)
# ═══════════════════════════════════════════════
TASA_IESS = 0.0945  # Aporte personal IESS Ecuador (9.45%)
DIAS_LABORABLES_MES = 23.83  # Promedio


def calcular_isr(ingreso_mensual):
    """Calcula ISR mensual basado en escala anual simplificada."""
    anual = ingreso_mensual * 12
    if anual <= 416220:
        return 0
    elif anual <= 624329:
        return round(((anual - 416220) * 0.15) / 12, 2)
    elif anual <= 867123:
        return round((31216 + (anual - 624329) * 0.20) / 12, 2)
    else:
        return round((79775 + (anual - 867123) * 0.25) / 12, 2)


# ═══════════════════════════════════════════════
#  EMPLEADOS
# ═══════════════════════════════════════════════

@rrhh_bp.route('/empleados', methods=['GET'])
@token_required
def listar_empleados():
    """Lista todos los empleados."""
    estado = request.args.get('estado')
    conn = get_db()

    if estado:
        empleados = conn.execute(
            'SELECT * FROM empleados WHERE estado = ? ORDER BY nombre', (estado,)
        ).fetchall()
    else:
        empleados = conn.execute('SELECT * FROM empleados ORDER BY nombre').fetchall()

    conn.close()
    return success_response(rows_to_list(empleados))


@rrhh_bp.route('/empleados', methods=['POST'])
@token_required
def crear_empleado():
    """Crea un nuevo empleado."""
    data = request.get_json()
    valid, msg = validate_required(data, ['nombre', 'puesto', 'salario', 'fecha_ingreso'])
    if not valid:
        return error_response(msg)

    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO empleados (nombre, cedula, email, puesto, departamento, tipo_contrato, horas_semanales, salario, fecha_ingreso, estado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['nombre'],
        data.get('cedula', ''),
        data.get('email', ''),
        data['puesto'],
        data.get('departamento', 'General'),
        data.get('tipo_contrato', 'fijo'),
        int(data.get('horas_semanales', 44)),
        float(data['salario']),
        data['fecha_ingreso'],
        data.get('estado', 'activo')
    ))
    conn.commit()
    emp_id = cursor.lastrowid
    empleado = conn.execute('SELECT * FROM empleados WHERE id = ?', (emp_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'EMPLEADO_CREADO', f'{data["nombre"]} - {data["puesto"]}')
    return success_response(row_to_dict(empleado), 'Empleado creado', 201)


@rrhh_bp.route('/empleados/<int:emp_id>', methods=['PUT'])
@token_required
def actualizar_empleado(emp_id):
    """Actualiza datos de un empleado."""
    data = request.get_json()
    if not data:
        return error_response('No se enviaron datos')

    conn = get_db()
    empleado = conn.execute('SELECT * FROM empleados WHERE id = ?', (emp_id,)).fetchone()
    if not empleado:
        conn.close()
        return error_response('Empleado no encontrado', 404)

    conn.execute('''
        UPDATE empleados SET nombre = ?, cedula = ?, email = ?, puesto = ?, departamento = ?,
               tipo_contrato = ?, horas_semanales = ?, salario = ?, fecha_ingreso = ?, estado = ?
        WHERE id = ?
    ''', (
        data.get('nombre', empleado['nombre']),
        data.get('cedula', empleado['cedula']),
        data.get('email', empleado['email']),
        data.get('puesto', empleado['puesto']),
        data.get('departamento', empleado['departamento']),
        data.get('tipo_contrato', empleado['tipo_contrato']),
        int(data.get('horas_semanales', empleado['horas_semanales'])),
        float(data.get('salario', empleado['salario'])),
        data.get('fecha_ingreso', empleado['fecha_ingreso']),
        data.get('estado', empleado['estado']),
        emp_id
    ))
    conn.commit()
    actualizado = conn.execute('SELECT * FROM empleados WHERE id = ?', (emp_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'EMPLEADO_ACTUALIZADO', f'ID {emp_id}: {actualizado["nombre"]}')
    return success_response(row_to_dict(actualizado), 'Empleado actualizado')


# ═══════════════════════════════════════════════
#  RESUMEN RRHH
# ═══════════════════════════════════════════════

@rrhh_bp.route('/resumen', methods=['GET'])
@token_required
def resumen_rrhh():
    """Resumen completo de RRHH con KPIs detallados."""
    conn = get_db()

    stats = conn.execute('''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN estado = 'activo' THEN 1 ELSE 0 END) as activos,
            COALESCE(SUM(CASE WHEN estado = 'activo' THEN salario ELSE 0 END), 0) as nomina_mensual
        FROM empleados
    ''').fetchone()

    asistencia_hoy = conn.execute('''
        SELECT COUNT(DISTINCT empleado_id) as total
        FROM asistencia WHERE fecha = date('now') AND tipo IN ('normal', 'tardanza')
    ''').fetchone()['total']

    promedio_salario = conn.execute('''
        SELECT COALESCE(AVG(salario), 0) as promedio FROM empleados WHERE estado = 'activo'
    ''').fetchone()['promedio']

    # KPIs nuevos
    faltas_mes = conn.execute('''
        SELECT COUNT(*) as total FROM asistencia
        WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
        AND tipo IN ('falta_justificada', 'falta_injustificada')
    ''').fetchone()['total']

    tardanzas_mes = conn.execute('''
        SELECT COUNT(*) as total FROM asistencia
        WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
        AND tipo = 'tardanza'
    ''').fetchone()['total']

    horas_extras_mes = conn.execute('''
        SELECT COALESCE(SUM(horas), 0) as total FROM horas_extras
        WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
    ''').fetchone()['total']

    incidencias_mes = conn.execute('''
        SELECT COUNT(*) as total FROM incidencias
        WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now')
    ''').fetchone()['total']

    incidencias_medicas = conn.execute('''
        SELECT COUNT(*) as total FROM incidencias
        WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now') AND tipo = 'medica'
    ''').fetchone()['total']

    conn.close()

    return success_response({
        'total_empleados': stats['total'],
        'activos': stats['activos'],
        'nomina_mensual': stats['nomina_mensual'],
        'promedio_salario': promedio_salario,
        'asistencia_hoy': asistencia_hoy,
        'faltas_mes': faltas_mes,
        'tardanzas_mes': tardanzas_mes,
        'horas_extras_mes': horas_extras_mes,
        'incidencias_mes': incidencias_mes,
        'incidencias_medicas': incidencias_medicas,
    })


# ═══════════════════════════════════════════════
#  ASISTENCIA
# ═══════════════════════════════════════════════

@rrhh_bp.route('/asistencia', methods=['POST'])
@token_required
def registrar_asistencia():
    """Registra entrada o salida de un empleado."""
    data = request.get_json()
    valid, msg = validate_required(data, ['empleado_id', 'fecha'])
    if not valid:
        return error_response(msg)

    empleado_id = int(data['empleado_id'])
    conn = get_db()

    empleado = conn.execute('SELECT id FROM empleados WHERE id = ?', (empleado_id,)).fetchone()
    if not empleado:
        conn.close()
        return error_response('Empleado no encontrado', 404)

    # Buscar registro existente del día
    registro = conn.execute(
        'SELECT * FROM asistencia WHERE empleado_id = ? AND fecha = ?',
        (empleado_id, data['fecha'])
    ).fetchone()

    if registro:
        # Actualizar salida si ya tiene entrada
        if 'salida' in data and data['salida']:
            # Calcular horas trabajadas
            horas_trab = 0
            horas_ext = 0
            if registro['entrada'] and data['salida']:
                try:
                    e_parts = registro['entrada'].split(':')
                    s_parts = data['salida'].split(':')
                    e_decimal = int(e_parts[0]) + int(e_parts[1]) / 60
                    s_decimal = int(s_parts[0]) + int(s_parts[1]) / 60
                    horas_trab = round(s_decimal - e_decimal, 2)
                    horas_ext = max(0, round(horas_trab - 8, 2))
                except (ValueError, IndexError):
                    pass

            conn.execute('''
                UPDATE asistencia SET salida = ?, horas_trabajadas = ?, horas_extra = ? WHERE id = ?
            ''', (data['salida'], horas_trab, horas_ext, registro['id']))
            conn.commit()
            asistencia = conn.execute('SELECT * FROM asistencia WHERE id = ?', (registro['id'],)).fetchone()
            conn.close()
            user_id = get_jwt_identity()
            registrar_log(int(user_id), 'ASISTENCIA_SALIDA', f'Empleado {empleado_id} - {data["fecha"]}')
            return success_response(row_to_dict(asistencia), 'Salida registrada')
        else:
            conn.close()
            return error_response('Ya existe registro de asistencia para esta fecha')
    else:
        # Crear nuevo registro de entrada
        entrada = data.get('entrada', '')
        tipo = data.get('tipo', 'normal')
        observacion = data.get('observacion', '')

        # Calcular horas si tiene entrada y salida
        horas_trab = 0
        horas_ext = 0
        salida = data.get('salida', '')
        if entrada and salida:
            try:
                e_parts = entrada.split(':')
                s_parts = salida.split(':')
                e_decimal = int(e_parts[0]) + int(e_parts[1]) / 60
                s_decimal = int(s_parts[0]) + int(s_parts[1]) / 60
                horas_trab = round(s_decimal - e_decimal, 2)
                horas_ext = max(0, round(horas_trab - 8, 2))
            except (ValueError, IndexError):
                pass

        cursor = conn.execute('''
            INSERT INTO asistencia (empleado_id, fecha, entrada, salida, horas_trabajadas, horas_extra, tipo, observacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (empleado_id, data['fecha'], entrada, salida, horas_trab, horas_ext, tipo, observacion))
        conn.commit()
        asist_id = cursor.lastrowid
        asistencia = conn.execute('''
            SELECT a.*, e.nombre as empleado_nombre
            FROM asistencia a JOIN empleados e ON a.empleado_id = e.id
            WHERE a.id = ?
        ''', (asist_id,)).fetchone()
        conn.close()

        user_id = get_jwt_identity()
        registrar_log(int(user_id), 'ASISTENCIA_ENTRADA', f'Empleado {empleado_id} - {data["fecha"]}')
        return success_response(row_to_dict(asistencia), 'Asistencia registrada', 201)


@rrhh_bp.route('/asistencia', methods=['GET'])
@token_required
def ver_asistencia():
    """Consulta asistencia por periodo o empleado."""
    empleado_id = request.args.get('empleado_id')
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    conn = get_db()

    query = '''
        SELECT a.*, e.nombre as empleado_nombre, e.puesto
        FROM asistencia a
        JOIN empleados e ON a.empleado_id = e.id
        WHERE 1=1
    '''
    params = []

    if empleado_id:
        query += ' AND a.empleado_id = ?'
        params.append(empleado_id)
    if desde:
        query += ' AND a.fecha >= ?'
        params.append(desde)
    if hasta:
        query += ' AND a.fecha <= ?'
        params.append(hasta)

    query += ' ORDER BY a.fecha DESC, e.nombre'
    asistencia = conn.execute(query, params).fetchall()
    conn.close()

    return success_response(rows_to_list(asistencia))


# ═══════════════════════════════════════════════
#  HORAS EXTRAS
# ═══════════════════════════════════════════════

@rrhh_bp.route('/horas-extras', methods=['GET'])
@token_required
def listar_horas_extras():
    """Lista horas extras con filtros opcionales."""
    empleado_id = request.args.get('empleado_id')
    periodo = request.args.get('periodo')  # formato YYYY-MM
    conn = get_db()

    query = '''
        SELECT he.*, e.nombre as empleado_nombre, e.puesto
        FROM horas_extras he
        JOIN empleados e ON he.empleado_id = e.id
        WHERE 1=1
    '''
    params = []

    if empleado_id:
        query += ' AND he.empleado_id = ?'
        params.append(empleado_id)
    if periodo:
        query += " AND strftime('%Y-%m', he.fecha) = ?"
        params.append(periodo)

    query += ' ORDER BY he.fecha DESC'
    registros = conn.execute(query, params).fetchall()
    conn.close()

    return success_response(rows_to_list(registros))


@rrhh_bp.route('/horas-extras', methods=['POST'])
@token_required
def registrar_horas_extras():
    """Registra horas extras de un empleado."""
    data = request.get_json()
    valid, msg = validate_required(data, ['empleado_id', 'fecha', 'horas'])
    if not valid:
        return error_response(msg)

    conn = get_db()
    emp = conn.execute('SELECT salario, horas_semanales FROM empleados WHERE id = ?',
                       (data['empleado_id'],)).fetchone()
    if not emp:
        conn.close()
        return error_response('Empleado no encontrado', 404)

    tipo = data.get('tipo', 'normal')
    horas = float(data['horas'])
    tarifa_hora = emp['salario'] / (emp['horas_semanales'] * 4.33)
    multiplicador = {'normal': 1.5, 'doble': 2.0, 'triple': 3.0}.get(tipo, 1.5)
    monto = round(tarifa_hora * horas * multiplicador, 2)

    cursor = conn.execute('''
        INSERT INTO horas_extras (empleado_id, fecha, horas, tipo, monto, aprobado, observacion)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (data['empleado_id'], data['fecha'], horas, tipo, monto,
          int(data.get('aprobado', 0)), data.get('observacion', '')))
    conn.commit()
    he_id = cursor.lastrowid
    registro = conn.execute('''
        SELECT he.*, e.nombre as empleado_nombre
        FROM horas_extras he JOIN empleados e ON he.empleado_id = e.id
        WHERE he.id = ?
    ''', (he_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'HORAS_EXTRAS_REGISTRADAS',
                  f'Empleado {data["empleado_id"]} - {horas}h {tipo} - ${monto}')
    return success_response(row_to_dict(registro), 'Horas extras registradas', 201)


@rrhh_bp.route('/horas-extras/<int:he_id>/aprobar', methods=['PUT'])
@token_required
def aprobar_horas_extras(he_id):
    """Aprueba o rechaza horas extras."""
    data = request.get_json()
    aprobado = int(data.get('aprobado', 1))

    conn = get_db()
    conn.execute('UPDATE horas_extras SET aprobado = ? WHERE id = ?', (aprobado, he_id))
    conn.commit()
    registro = conn.execute('SELECT * FROM horas_extras WHERE id = ?', (he_id,)).fetchone()
    conn.close()

    if not registro:
        return error_response('Registro no encontrado', 404)

    estado = 'aprobadas' if aprobado else 'rechazadas'
    user_id = get_jwt_identity()
    registrar_log(int(user_id), f'HORAS_EXTRAS_{estado.upper()}', f'ID {he_id}')
    return success_response(row_to_dict(registro), f'Horas extras {estado}')


# ═══════════════════════════════════════════════
#  INCIDENCIAS
# ═══════════════════════════════════════════════

@rrhh_bp.route('/incidencias', methods=['GET'])
@token_required
def listar_incidencias():
    """Lista incidencias con filtros opcionales."""
    empleado_id = request.args.get('empleado_id')
    tipo = request.args.get('tipo')
    periodo = request.args.get('periodo')
    conn = get_db()

    query = '''
        SELECT i.*, e.nombre as empleado_nombre, e.puesto
        FROM incidencias i
        JOIN empleados e ON i.empleado_id = e.id
        WHERE 1=1
    '''
    params = []

    if empleado_id:
        query += ' AND i.empleado_id = ?'
        params.append(empleado_id)
    if tipo:
        query += ' AND i.tipo = ?'
        params.append(tipo)
    if periodo:
        query += " AND strftime('%Y-%m', i.fecha) = ?"
        params.append(periodo)

    query += ' ORDER BY i.fecha DESC'
    registros = conn.execute(query, params).fetchall()
    conn.close()

    return success_response(rows_to_list(registros))


@rrhh_bp.route('/incidencias', methods=['POST'])
@token_required
def registrar_incidencia():
    """Registra una nueva incidencia."""
    data = request.get_json()
    valid, msg = validate_required(data, ['empleado_id', 'fecha', 'tipo', 'descripcion'])
    if not valid:
        return error_response(msg)

    conn = get_db()
    emp = conn.execute('SELECT id FROM empleados WHERE id = ?', (data['empleado_id'],)).fetchone()
    if not emp:
        conn.close()
        return error_response('Empleado no encontrado', 404)

    cursor = conn.execute('''
        INSERT INTO incidencias (empleado_id, fecha, tipo, descripcion, dias_ausencia, justificada, documento_soporte)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (data['empleado_id'], data['fecha'], data['tipo'], data['descripcion'],
          int(data.get('dias_ausencia', 0)), int(data.get('justificada', 0)),
          data.get('documento_soporte', '')))
    conn.commit()
    inc_id = cursor.lastrowid
    registro = conn.execute('''
        SELECT i.*, e.nombre as empleado_nombre
        FROM incidencias i JOIN empleados e ON i.empleado_id = e.id
        WHERE i.id = ?
    ''', (inc_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'INCIDENCIA_REGISTRADA',
                  f'Empleado {data["empleado_id"]} - {data["tipo"]} - {data["descripcion"][:50]}')
    return success_response(row_to_dict(registro), 'Incidencia registrada', 201)


# ═══════════════════════════════════════════════
#  NÓMINA
# ═══════════════════════════════════════════════

@rrhh_bp.route('/nomina', methods=['GET'])
@token_required
def listar_nomina():
    """Lista nóminas con filtro por periodo."""
    periodo = request.args.get('periodo')
    conn = get_db()

    query = '''
        SELECT n.*, e.nombre as empleado_nombre, e.cedula, e.puesto, e.departamento
        FROM nomina n
        JOIN empleados e ON n.empleado_id = e.id
        WHERE 1=1
    '''
    params = []

    if periodo:
        query += ' AND n.periodo = ?'
        params.append(periodo)

    query += ' ORDER BY n.periodo DESC, e.nombre'
    registros = conn.execute(query, params).fetchall()
    conn.close()

    return success_response(rows_to_list(registros))


@rrhh_bp.route('/nomina/<int:nom_id>', methods=['GET'])
@token_required
def detalle_nomina(nom_id):
    """Detalle de una nómina específica."""
    conn = get_db()
    registro = conn.execute('''
        SELECT n.*, e.nombre as empleado_nombre, e.cedula, e.puesto, e.departamento,
               e.tipo_contrato, e.horas_semanales, e.email
        FROM nomina n
        JOIN empleados e ON n.empleado_id = e.id
        WHERE n.id = ?
    ''', (nom_id,)).fetchone()
    conn.close()

    if not registro:
        return error_response('Nómina no encontrada', 404)

    return success_response(row_to_dict(registro))


@rrhh_bp.route('/nomina/generar', methods=['POST'])
@token_required
def generar_nomina():
    """Genera la nómina del periodo especificado para todos los empleados activos."""
    data = request.get_json()
    periodo = data.get('periodo')
    if not periodo:
        return error_response('El periodo es requerido (formato YYYY-MM)')

    conn = get_db()

    # Verificar si ya existe nómina para este periodo
    existente = conn.execute('SELECT COUNT(*) as c FROM nomina WHERE periodo = ?', (periodo,)).fetchone()['c']
    if existente > 0:
        conn.close()
        return error_response(f'Ya existe nómina generada para el periodo {periodo}. Elimínala primero si deseas regenerar.')

    empleados = conn.execute("SELECT * FROM empleados WHERE estado = 'activo'").fetchall()
    nominas_generadas = []

    for emp in empleados:
        salario_bruto = emp['salario']

        # Sumar horas extras aprobadas del periodo
        he_monto = conn.execute('''
            SELECT COALESCE(SUM(monto), 0) as total FROM horas_extras
            WHERE empleado_id = ? AND strftime('%Y-%m', fecha) = ? AND aprobado = 1
        ''', (emp['id'], periodo)).fetchone()['total']

        bonificaciones = float(data.get('bonificaciones', 0))
        total_ingresos = salario_bruto + he_monto + bonificaciones

        # Deducciones
        deduccion_iess = round(total_ingresos * TASA_IESS, 2)
        deduccion_sfs = 0.0 # Mantenemos a 0 por compatibilidad con esquema antiguo
        deduccion_afp = 0.0 # Mantenemos a 0 por compatibilidad con esquema antiguo
        deduccion_isr = calcular_isr(total_ingresos)
        otras_deducciones = float(data.get('otras_deducciones', 0))

        # Faltas injustificadas
        faltas = conn.execute('''
            SELECT COUNT(*) as total FROM asistencia
            WHERE empleado_id = ? AND strftime('%Y-%m', fecha) = ? AND tipo = 'falta_injustificada'
        ''', (emp['id'], periodo)).fetchone()['total']
        tarifa_diaria = salario_bruto / DIAS_LABORABLES_MES
        desc_faltas = round(faltas * tarifa_diaria, 2)

        total_deducciones = round(deduccion_iess + deduccion_isr + otras_deducciones + desc_faltas, 2)
        salario_neto = round(total_ingresos - total_deducciones, 2)

        cursor = conn.execute('''
            INSERT INTO nomina (empleado_id, periodo, salario_bruto, horas_extras_monto, bonificaciones,
                total_ingresos, deduccion_sfs, deduccion_afp, deduccion_iess, deduccion_isr, otras_deducciones,
                desc_faltas_injustificadas, total_deducciones, salario_neto, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendiente')
        ''', (emp['id'], periodo, salario_bruto, he_monto, bonificaciones, total_ingresos,
              deduccion_sfs, deduccion_afp, deduccion_iess, deduccion_isr, otras_deducciones, desc_faltas,
              total_deducciones, salario_neto))

        nom_id = cursor.lastrowid
        nomina = conn.execute('''
            SELECT n.*, e.nombre as empleado_nombre, e.cedula, e.puesto, e.departamento
            FROM nomina n JOIN empleados e ON n.empleado_id = e.id WHERE n.id = ?
        ''', (nom_id,)).fetchone()
        nominas_generadas.append(row_to_dict(nomina))

    conn.commit()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'NOMINA_GENERADA',
                  f'Periodo {periodo} - {len(nominas_generadas)} empleados')
    return success_response(nominas_generadas, f'Nómina generada para {len(nominas_generadas)} empleados', 201)


@rrhh_bp.route('/nomina/<int:nom_id>/pagar', methods=['PUT'])
@token_required
def pagar_nomina(nom_id):
    """Marca una nómina como pagada."""
    from datetime import datetime
    conn = get_db()

    nomina = conn.execute('SELECT * FROM nomina WHERE id = ?', (nom_id,)).fetchone()
    if not nomina:
        conn.close()
        return error_response('Nómina no encontrada', 404)

    fecha_pago = datetime.now().strftime('%Y-%m-%d')
    conn.execute('UPDATE nomina SET estado = ?, fecha_pago = ? WHERE id = ?',
                 ('pagada', fecha_pago, nom_id))
    conn.commit()
    actualizada = conn.execute('''
        SELECT n.*, e.nombre as empleado_nombre
        FROM nomina n JOIN empleados e ON n.empleado_id = e.id WHERE n.id = ?
    ''', (nom_id,)).fetchone()
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'NOMINA_PAGADA', f'ID {nom_id} - {actualizada["empleado_nombre"]}')
    return success_response(row_to_dict(actualizada), 'Nómina marcada como pagada')


@rrhh_bp.route('/nomina/pagar-periodo', methods=['PUT'])
@token_required
def pagar_periodo():
    """Marca todas las nóminas de un periodo como pagadas."""
    from datetime import datetime
    data = request.get_json()
    periodo = data.get('periodo')
    if not periodo:
        return error_response('Periodo requerido')

    conn = get_db()
    fecha_pago = datetime.now().strftime('%Y-%m-%d')
    conn.execute("UPDATE nomina SET estado = 'pagada', fecha_pago = ? WHERE periodo = ? AND estado = 'pendiente'",
                 (fecha_pago, periodo))
    conn.commit()

    total = conn.execute("SELECT COUNT(*) as c FROM nomina WHERE periodo = ? AND estado = 'pagada'",
                         (periodo,)).fetchone()['c']
    conn.close()

    user_id = get_jwt_identity()
    registrar_log(int(user_id), 'NOMINA_PERIODO_PAGADO', f'Periodo {periodo} - {total} nóminas')
    return success_response({'total_pagadas': total}, f'Periodo {periodo} pagado — {total} nóminas')


@rrhh_bp.route('/periodos-nomina', methods=['GET'])
@token_required
def periodos_disponibles():
    """Lista los periodos de nómina disponibles."""
    conn = get_db()
    periodos = conn.execute('''
        SELECT periodo, COUNT(*) as total_empleados,
               SUM(salario_neto) as total_neto,
               SUM(total_deducciones) as total_deducciones,
               MIN(estado) as estado_general
        FROM nomina GROUP BY periodo ORDER BY periodo DESC
    ''').fetchall()
    conn.close()
    return success_response(rows_to_list(periodos))
