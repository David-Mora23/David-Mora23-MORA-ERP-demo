"""
app.py - Aplicación principal Flask para EasyERP.
Punto de entrada del sistema ERP.
"""

import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

# Cargar .env siempre desde la carpeta backend (aunque el servidor se inicie desde otra ruta)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Importar módulos de la aplicación
from database import init_db, seed_db
from auth import auth_bp
from finanzas import finanzas_bp
from inventario import inventario_bp
from compras import compras_bp
from ventas import ventas_bp
from rrhh import rrhh_bp
from reportes import reportes_bp
from chatbot import chatbot_bp
from auditoria import auditoria_bp

# Rutas al frontend
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')


def create_app():
    """Factory para crear y configurar la aplicación Flask."""
    # Asegurar que la base de datos esté creada e inicializada en cualquier servidor de producción (Gunicorn, etc.)
    init_db()
    seed_db()

    app = Flask(__name__, static_folder=None)

    # --- Configuración ---
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'clave_secreta_por_defecto_cambiar')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 86400  # 24 horas
    app.config['JWT_TOKEN_LOCATION'] = ['headers', 'query_string']
    app.config['JWT_QUERY_STRING_NAME'] = 'token'

    # --- Extensiones ---
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)

    # --- Registrar Blueprints (módulos) ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(finanzas_bp)
    app.register_blueprint(inventario_bp)
    app.register_blueprint(compras_bp)
    app.register_blueprint(ventas_bp)
    app.register_blueprint(rrhh_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(auditoria_bp)

    # --- Servir Frontend Estático ---
    @app.route('/')
    def index():
        return send_from_directory(FRONTEND_DIR, 'index.html')

    @app.route('/login')
    def login_page():
        return send_from_directory(FRONTEND_DIR, 'login.html')

    @app.route('/<path:filename>')
    def serve_static(filename):
        """Sirve archivos estáticos del frontend (CSS, JS, HTML)."""
        # Evitar servir rutas de API
        if filename.startswith('api/'):
            return jsonify({'error': 'Ruta no encontrada'}), 404
        return send_from_directory(FRONTEND_DIR, filename)

    # --- Manejo global de errores ---
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Recurso no encontrado'}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Error interno del servidor'}), 500

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({'error': 'Método no permitido'}), 405

    return app


# Crear instancia de la aplicación
app = create_app()


if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("  EasyERP - Sistema de Planificación de Recursos")
    print("=" * 50)
    print("  URL: http://localhost:5000")
    print("  Login: http://localhost:5000/login")
    print("  API:  http://localhost:5000/api/")
    print("=" * 50)
    print("  Usuarios de prueba:")
    print("    admin@erp.com    / password123 (Admin)")
    print("    vendedor@erp.com / password123 (Vendedor)")
    print("    contador@erp.com / password123 (Contador)")
    print("=" * 50 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=True)
