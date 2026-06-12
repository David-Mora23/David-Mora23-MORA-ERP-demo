"""
chatbot.py - Módulo de chatbot IA para EasyERP.
Soporta OpenAI (ChatGPT) y Google Gemini con cambio manual y respaldo automático.
"""

import os
import traceback
from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity
from database import get_db
from utils import token_required, error_response, success_response, logger

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api')

_openai_client = None
_gemini_client = None

PROVIDER_LABELS = {
    'openai': 'ChatGPT',
    'gemini': 'Gemini',
    'auto': 'Auto (respaldo)',
}


def _load_env():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


def _get_openai_client():
    global _openai_client
    if _openai_client is not None:
        return _openai_client

    _load_env()
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key or api_key == 'TU_API_KEY_AQUI':
        raise ValueError('OPENAI_API_KEY no configurada')

    from openai import OpenAI
    _openai_client = OpenAI(api_key=api_key)
    logger.info("Cliente OpenAI inicializado correctamente.")
    return _openai_client


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client

    _load_env()
    api_key = os.getenv('GEMINI_API_KEY', '').strip()
    if not api_key or api_key == 'TU_API_KEY_AQUI':
        raise ValueError('GEMINI_API_KEY no configurada')

    from google import genai
    _gemini_client = genai.Client(api_key=api_key)
    logger.info("Cliente Gemini inicializado correctamente.")
    return _gemini_client


def _provider_disponible(provider):
    _load_env()
    if provider == 'openai':
        key = os.getenv('OPENAI_API_KEY', '').strip()
        return bool(key and key != 'TU_API_KEY_AQUI')
    if provider == 'gemini':
        key = os.getenv('GEMINI_API_KEY', '').strip()
        return bool(key and key != 'TU_API_KEY_AQUI')
    return False


def _is_quota_error(error_msg):
    error_upper = str(error_msg).upper()
    return any(token in error_upper for token in (
        'QUOTA', 'RATE', '429', 'RESOURCE_EXHAUSTED', 'INSUFFICIENT_QUOTA'
    ))


def _is_auth_error(error_msg):
    error_upper = str(error_msg).upper()
    return any(token in error_upper for token in (
        'API_KEY', 'UNAUTHORIZED', 'INVALID_API_KEY', 'PERMISSION'
    ))


def _recopilar_contexto_erp():
    """Ejecuta consultas resumidas a la BD para dar contexto al modelo."""
    conn = get_db()
    contexto_partes = []

    try:
        productos = conn.execute(
            'SELECT COUNT(*) as total, SUM(stock) as stock_total FROM productos'
        ).fetchone()
        stock_bajo = conn.execute(
            'SELECT COUNT(*) as total FROM productos WHERE stock <= 5'
        ).fetchone()
        top_productos = conn.execute(
            'SELECT nombre, codigo, stock, precio_venta, precio_costo, categoria FROM productos ORDER BY stock ASC LIMIT 10'
        ).fetchall()

        contexto_partes.append(
            f"INVENTARIO:\n"
            f"  - Total productos: {productos['total']}\n"
            f"  - Stock total acumulado: {productos['stock_total'] or 0} unidades\n"
            f"  - Productos con stock bajo (<=5): {stock_bajo['total']}\n"
            f"  - Listado de productos (ordenados por menor stock):"
        )
        for p in top_productos:
            margen = ((p['precio_venta'] - p['precio_costo']) / p['precio_costo'] * 100) if p['precio_costo'] > 0 else 0
            contexto_partes.append(
                f"    * {p['nombre']} ({p['codigo']}) - Stock: {p['stock']}, "
                f"Costo: ${p['precio_costo']:.2f}, Venta: ${p['precio_venta']:.2f}, "
                f"Margen: {margen:.1f}%, Categoria: {p['categoria']}"
            )

        ventas_mensuales = conn.execute('''
            SELECT strftime('%Y-%m', f.fecha) as mes,
                   COUNT(f.id) as num_facturas,
                   COALESCE(SUM(f.total), 0) as monto_total
            FROM facturas f
            WHERE f.estado != 'anulada'
            GROUP BY mes
            ORDER BY mes
        ''').fetchall()

        facturas_total = conn.execute(
            'SELECT COUNT(*) as total, COALESCE(SUM(total), 0) as monto_total FROM facturas WHERE estado != "anulada"'
        ).fetchone()
        facturas_pendientes = conn.execute(
            'SELECT COUNT(*) as total FROM facturas WHERE estado = "pendiente"'
        ).fetchone()
        clientes = conn.execute('SELECT COUNT(*) as total FROM clientes').fetchone()
        top_clientes = conn.execute('''
            SELECT c.nombre, COUNT(f.id) as num_facturas, COALESCE(SUM(f.total), 0) as total_compras
            FROM clientes c LEFT JOIN facturas f ON c.id = f.cliente_id AND f.estado != 'anulada'
            GROUP BY c.id ORDER BY total_compras DESC LIMIT 5
        ''').fetchall()

        contexto_partes.append(
            f"\nVENTAS:\n"
            f"  - Total facturas: {facturas_total['total']}\n"
            f"  - Monto total vendido: ${facturas_total['monto_total']:.2f}\n"
            f"  - Facturas pendientes: {facturas_pendientes['total']}\n"
            f"  - Total clientes: {clientes['total']}\n"
            f"  - Ventas por mes (historico):"
        )
        for vm in ventas_mensuales:
            contexto_partes.append(
                f"    * {vm['mes']}: {vm['num_facturas']} facturas, ${vm['monto_total']:.2f}"
            )
        contexto_partes.append("  - Top clientes:")
        for c in top_clientes:
            contexto_partes.append(
                f"    * {c['nombre']} - {c['num_facturas']} facturas, ${c['total_compras']:.2f}"
            )

        top_vendidos = conn.execute('''
            SELECT p.nombre, p.codigo, SUM(fi.cantidad) as total_vendido,
                   SUM(fi.subtotal) as total_ingresos
            FROM items_factura fi
            JOIN productos p ON fi.producto_id = p.id
            JOIN facturas f ON fi.factura_id = f.id
            WHERE f.estado != 'anulada'
            GROUP BY p.id
            ORDER BY total_vendido DESC
            LIMIT 5
        ''').fetchall()

        if top_vendidos:
            contexto_partes.append("  - Productos mas vendidos:")
            for tv in top_vendidos:
                contexto_partes.append(
                    f"    * {tv['nombre']} ({tv['codigo']}): {tv['total_vendido']} uds, ${tv['total_ingresos']:.2f}"
                )

        ingresos = conn.execute(
            'SELECT COALESCE(SUM(monto), 0) as total FROM transacciones WHERE tipo = "ingreso"'
        ).fetchone()
        egresos = conn.execute(
            'SELECT COALESCE(SUM(monto), 0) as total FROM transacciones WHERE tipo = "egreso"'
        ).fetchone()
        cuentas = conn.execute('SELECT nombre, tipo, saldo FROM cuentas').fetchall()
        trans_mensuales = conn.execute('''
            SELECT strftime('%Y-%m', fecha) as mes, tipo,
                   COALESCE(SUM(monto), 0) as total
            FROM transacciones
            GROUP BY mes, tipo
            ORDER BY mes
        ''').fetchall()

        contexto_partes.append(
            f"\nFINANZAS:\n"
            f"  - Total ingresos: ${ingresos['total']:.2f}\n"
            f"  - Total egresos: ${egresos['total']:.2f}\n"
            f"  - Balance neto: ${(ingresos['total'] - egresos['total']):.2f}\n"
            f"  - Cuentas:"
        )
        for cuenta in cuentas:
            contexto_partes.append(
                f"    * {cuenta['nombre']} ({cuenta['tipo']}): ${cuenta['saldo']:.2f}"
            )
        if trans_mensuales:
            contexto_partes.append("  - Transacciones por mes:")
            for tm in trans_mensuales:
                contexto_partes.append(
                    f"    * {tm['mes']} ({tm['tipo']}): ${tm['total']:.2f}"
                )

        proveedores = conn.execute('SELECT COUNT(*) as total FROM proveedores').fetchone()
        ordenes = conn.execute(
            'SELECT COUNT(*) as total, COALESCE(SUM(total), 0) as monto FROM ordenes_compra'
        ).fetchone()
        ordenes_pendientes = conn.execute(
            'SELECT COUNT(*) as total FROM ordenes_compra WHERE estado = "pendiente"'
        ).fetchone()

        contexto_partes.append(
            f"\nCOMPRAS:\n"
            f"  - Proveedores: {proveedores['total']}\n"
            f"  - Ordenes totales: {ordenes['total']} (${ordenes['monto']:.2f})\n"
            f"  - Ordenes pendientes: {ordenes_pendientes['total']}"
        )

        empleados = conn.execute(
            'SELECT COUNT(*) as total FROM empleados WHERE estado = "activo"'
        ).fetchone()
        nomina = conn.execute(
            'SELECT COALESCE(SUM(salario), 0) as total FROM empleados WHERE estado = "activo"'
        ).fetchone()
        lista_empleados = conn.execute(
            'SELECT nombre, puesto, salario, estado FROM empleados ORDER BY salario DESC'
        ).fetchall()

        contexto_partes.append(
            f"\nRECURSOS HUMANOS:\n"
            f"  - Empleados activos: {empleados['total']}\n"
            f"  - Nomina mensual total: ${nomina['total']:.2f}\n"
            f"  - Listado de empleados:"
        )
        for emp in lista_empleados:
            contexto_partes.append(
                f"    * {emp['nombre']} - {emp['puesto']}, ${emp['salario']:.2f}/mes ({emp['estado']})"
            )

    except Exception as e:
        logger.error(f"Error recopilando contexto ERP: {e}")
        contexto_partes.append(f"\nError parcial al obtener datos: {e}")
    finally:
        conn.close()

    return '\n'.join(contexto_partes)


SYSTEM_PROMPT = """Eres el asistente IA de EasyERP, un sistema de planificacion de recursos empresariales.
Tu nombre es "ERP Assistant". Responde SIEMPRE en espanol.

REGLAS ESTRICTAS:
1. Se CONCISO y DIRECTO. Maximo 3-4 oraciones por respuesta, a menos que el usuario pida detalle.
2. Usa los datos reales del ERP que se te proporcionan como contexto. NO inventes datos.
3. Si te preguntan algo que no esta en los datos del contexto, dilo honestamente.
4. Formatea numeros con formato monetario cuando aplique ($X,XXX.XX).
5. Puedes usar emojis para hacer la respuesta mas visual, pero no abuses.
6. Si el usuario te saluda, responde brevemente y ofrece ayuda sobre el ERP.
7. No reveles informacion tecnica sobre la base de datos ni sobre como funcionas internamente.
8. Enfocate en dar insights utiles y accionables sobre los datos del negocio.
9. Si te piden PROYECCIONES o PREDICCIONES, usa los datos historicos mensuales para calcular tendencias.
   Puedes hacer regresion lineal simple o promedios para estimar meses futuros.
10. Cuando hagas proyecciones, aclara que son ESTIMACIONES basadas en datos historicos.

DATOS ACTUALES DEL ERP:
{contexto}
"""


def _historial_a_mensajes(historial):
    messages = []
    for msg in historial[-6:]:
        role = msg.get('role', 'user')
        if role in ('model', 'assistant'):
            role = 'assistant'
        else:
            role = 'user'
        content = msg.get('content', '').strip()
        if content:
            messages.append({'role': role, 'content': content})
    return messages


def _historial_a_prompt(historial, user_message):
    prompt_parts = []
    for msg in historial[-6:]:
        role_label = "Usuario" if msg.get('role') == 'user' else "Asistente"
        prompt_parts.append(f"{role_label}: {msg.get('content', '')}")
    prompt_parts.append(f"Usuario: {user_message}")
    prompt_parts.append("Asistente:")
    return "\n".join(prompt_parts)


def _call_openai(system_instruction, historial, user_message):
    client = _get_openai_client()
    model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    messages = [{'role': 'system', 'content': system_instruction}]
    messages.extend(_historial_a_mensajes(historial))
    messages.append({'role': 'user', 'content': user_message})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=800,
    )

    if response.choices and response.choices[0].message.content:
        return response.choices[0].message.content.strip()
    return 'No pude generar una respuesta. Intenta reformular tu pregunta.'


def _call_gemini(system_instruction, historial, user_message):
    from google.genai import types

    client = _get_gemini_client()
    models = [
        os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'),
        'gemini-2.0-flash-lite',
    ]
    full_prompt = _historial_a_prompt(historial, user_message)
    last_error = None

    for model_name in models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                    max_output_tokens=800,
                )
            )
            if response and response.text:
                return response.text.strip()
            return 'No pude generar una respuesta. Intenta reformular tu pregunta.'
        except Exception as e:
            last_error = e
            if _is_quota_error(str(e)):
                raise
            logger.warning(f"Gemini {model_name} fallo: {str(e)[:120]}")

    if last_error:
        raise last_error
    return 'No pude generar una respuesta. Intenta reformular tu pregunta.'


def _orden_proveedores(provider_preferido):
    _load_env()
    default_order = os.getenv('CHAT_PROVIDER_ORDER', 'gemini,openai').split(',')
    default_order = [p.strip() for p in default_order if p.strip() in ('gemini', 'openai')]

    if provider_preferido == 'auto':
        return default_order or ['gemini', 'openai']

    return [provider_preferido]


def _generar_respuesta(provider_preferido, historial, user_message, system_instruction):
    providers = _orden_proveedores(provider_preferido)
    available = [p for p in providers if _provider_disponible(p)]

    if not available:
        raise ValueError(
            'Ningun proveedor de IA configurado. Agrega OPENAI_API_KEY o GEMINI_API_KEY en .env'
        )

    errors = []
    for idx, provider in enumerate(available):
        try:
            if provider == 'openai':
                text = _call_openai(system_instruction, historial, user_message)
            else:
                text = _call_gemini(system_instruction, historial, user_message)

            return {
                'response': text,
                'provider': provider,
                'provider_label': PROVIDER_LABELS[provider],
                'fallback': idx > 0,
                'fallback_from': available[0] if idx > 0 else None,
            }
        except ValueError as e:
            errors.append(f"{provider}: {e}")
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Proveedor {provider} fallo: {error_msg[:150]}")
            errors.append(f"{provider}: {error_msg[:120]}")

            if provider_preferido != 'auto' or not _is_quota_error(error_msg):
                if idx == len(available) - 1:
                    break
                continue

    combined = ' | '.join(errors)
    if all(_is_quota_error(e) for e in errors):
        if len(available) == 1:
            label = PROVIDER_LABELS.get(available[0], available[0])
            raise RuntimeError(
                f'Cuota agotada en {label}. Cambia de API con el selector o agrega creditos.'
            )
        raise RuntimeError(
            'Cuota agotada en Gemini y ChatGPT. Cambia de API manualmente o agrega creditos.'
        )
    if any(_is_auth_error(e) for e in errors):
        raise RuntimeError('API Key invalida en uno o mas proveedores. Revisa el archivo .env')
    raise RuntimeError(combined[:300])


@chatbot_bp.route('/chat/providers', methods=['GET'])
@token_required
def chat_providers():
    """Lista proveedores de IA disponibles segun las API keys configuradas."""
    _load_env()
    providers = []
    for key in ('gemini', 'openai'):
        if _provider_disponible(key):
            providers.append({
                'id': key,
                'label': PROVIDER_LABELS[key],
            })

    return success_response({
        'providers': providers,
        'auto_available': len(providers) > 0,
        'default': os.getenv('CHAT_PROVIDER', 'auto'),
    })


@chatbot_bp.route('/chat', methods=['POST'])
@token_required
def chat():
    """Endpoint principal del chatbot con soporte multi-proveedor."""
    data = request.get_json()
    if not data or not data.get('message', '').strip():
        return error_response('El mensaje no puede estar vacio')

    user_message = data['message'].strip()
    historial = data.get('history', [])
    provider = (data.get('provider') or 'auto').strip().lower()

    if provider not in ('auto', 'openai', 'gemini'):
        return error_response('Proveedor invalido. Usa: auto, openai o gemini')

    if provider != 'auto' and not _provider_disponible(provider):
        return error_response(
            f'El proveedor {PROVIDER_LABELS.get(provider, provider)} no esta configurado en .env',
            503
        )

    contexto = _recopilar_contexto_erp()
    system_instruction = SYSTEM_PROMPT.format(contexto=contexto)

    try:
        result = _generar_respuesta(provider, historial, user_message, system_instruction)
        user_id = get_jwt_identity()
        logger.info(
            f"Chat [{user_id}] ({result['provider']}): "
            f"{user_message[:60]} -> {result['response'][:60]}"
        )
        return success_response(result)

    except ValueError as e:
        return error_response(str(e), 503)
    except RuntimeError as e:
        error_msg = str(e)
        if 'Cuota agotada' in error_msg:
            return error_response(error_msg, 429)
        if 'API Key invalida' in error_msg:
            return error_response(error_msg, 403)
        return error_response(error_msg, 500)
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error en chatbot: {error_msg}")
        logger.error(traceback.format_exc())
        return error_response(f'Error del servicio de IA: {error_msg[:200]}', 500)
