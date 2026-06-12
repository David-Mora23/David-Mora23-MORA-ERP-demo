/**
 * api.js - Cliente API para comunicación con el backend EasyERP
 */

// Enlace relativo que funciona automáticamente tanto en desarrollo local como en producción
const API_BASE = '/api';


const API = {
    /** Realiza una petición HTTP autenticada */
    async request(endpoint, options = {}) {
        const token = localStorage.getItem('erp_token');
        const headers = {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...options.headers
        };

        try {
            const response = await fetch(`${API_BASE}${endpoint}`, {
                ...options,
                headers
            });

            // Token expirado - redirigir a login
            if (response.status === 401) {
                localStorage.removeItem('erp_token');
                localStorage.removeItem('erp_user');
                window.location.href = '/login';
                return null;
            }

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `Error ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    },

    get(endpoint) {
        return this.request(endpoint);
    },

    post(endpoint, body) {
        return this.request(endpoint, { method: 'POST', body: JSON.stringify(body) });
    },

    put(endpoint, body) {
        return this.request(endpoint, { method: 'PUT', body: JSON.stringify(body) });
    },

    delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    },

    // --- Auth ---
    login(email, password) {
        return this.post('/auth/login', { email, password });
    },

    register(email, password, rol) {
        return this.post('/auth/registro', { email, password, rol });
    },

    getMe() {
        return this.get('/auth/me');
    },

    getUsuarios() {
        return this.get('/auth/usuarios');
    },

    crearUsuario(data) {
        return this.post('/auth/usuarios', data);
    },

    actualizarUsuario(id, data) {
        return this.put(`/auth/usuarios/${id}`, data);
    },

    eliminarUsuario(id) {
        return this.delete(`/auth/usuarios/${id}`);
    },

    logout() {
        return this.post('/auth/logout', {});
    },

    getAuditoria(query = '') {
        return this.get(`/auditoria/logs${query ? '?' + query : ''}`);
    },

    getResumenRRHH() {
        return this.get('/rrhh/resumen');
    },

    actualizarEmpleado(id, data) {
        return this.put(`/rrhh/empleados/${id}`, data);
    },

    // --- Dashboard ---
    getKPIs() {
        return this.get('/dashboard/kpis');
    },

    getGraficos() {
        return this.get('/dashboard/graficos');
    },

    // --- Finanzas ---
    getTransacciones() {
        return this.get('/finanzas/transacciones');
    },

    crearTransaccion(data) {
        return this.post('/finanzas/transacciones', data);
    },

    getResumenFinanciero() {
        return this.get('/finanzas/resumen');
    },

    // --- Inventario ---
    getProductos() {
        return this.get('/inventario/productos');
    },

    crearProducto(data) {
        return this.post('/inventario/productos', data);
    },

    actualizarProducto(id, data) {
        return this.put(`/inventario/productos/${id}`, data);
    },

    getAlertasStock() {
        return this.get('/inventario/alertas');
    },

    registrarMovimiento(data) {
        return this.post('/inventario/movimientos', data);
    },

    // --- Compras ---
    getProveedores() {
        return this.get('/compras/proveedores');
    },

    getOrdenesCompra() {
        return this.get('/compras/ordenes');
    },

    crearOrdenCompra(data) {
        return this.post('/compras/ordenes', data);
    },

    actualizarOrden(id, data) {
        return this.put(`/compras/ordenes/${id}`, data);
    },

    // --- Ventas ---
    getClientes() {
        return this.get('/ventas/clientes');
    },

    crearCliente(data) {
        return this.post('/ventas/clientes', data);
    },

    getFacturas() {
        return this.get('/ventas/facturas');
    },

    crearFactura(data) {
        return this.post('/ventas/facturas', data);
    },

    getReportesVentas() {
        return this.get('/ventas/reportes');
    },

    // --- RRHH ---
    getEmpleados() {
        return this.get('/rrhh/empleados');
    },

    crearEmpleado(data) {
        return this.post('/rrhh/empleados', data);
    },

    getAsistencia(params = '') {
        return this.get(`/rrhh/asistencia${params}`);
    },

    registrarAsistencia(data) {
        return this.post('/rrhh/asistencia', data);
    },

    // --- RRHH: Horas Extras ---
    getHorasExtras(params = '') {
        return this.get(`/rrhh/horas-extras${params}`);
    },

    registrarHorasExtras(data) {
        return this.post('/rrhh/horas-extras', data);
    },

    aprobarHorasExtras(id, aprobado) {
        return this.put(`/rrhh/horas-extras/${id}/aprobar`, { aprobado });
    },

    // --- RRHH: Incidencias ---
    getIncidencias(params = '') {
        return this.get(`/rrhh/incidencias${params}`);
    },

    registrarIncidencia(data) {
        return this.post('/rrhh/incidencias', data);
    },

    // --- RRHH: Nómina ---
    getNomina(params = '') {
        return this.get(`/rrhh/nomina${params}`);
    },

    getDetalleNomina(id) {
        return this.get(`/rrhh/nomina/${id}`);
    },

    generarNomina(data) {
        return this.post('/rrhh/nomina/generar', data);
    },

    pagarNomina(id) {
        return this.put(`/rrhh/nomina/${id}/pagar`, {});
    },

    pagarPeriodo(periodo) {
        return this.put('/rrhh/nomina/pagar-periodo', { periodo });
    },

    getPeriodosNomina() {
        return this.get('/rrhh/periodos-nomina');
    },

    // --- Reportes ---
    exportarPDF(tipo) {
        const token = localStorage.getItem('erp_token');
        window.open(`${API_BASE}/reportes/pdf?tipo=${tipo}&token=${token}`, '_blank');
    },

    exportarExcel(tipo) {
        const token = localStorage.getItem('erp_token');
        window.open(`${API_BASE}/reportes/excel?tipo=${tipo}&token=${token}`, '_blank');
    }
};
