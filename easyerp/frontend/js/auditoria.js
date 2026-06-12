/**
 * auditoria.js - Registro de actividad (solo Admin)
 */

const Auditoria = {
    async load() {
        Utils.showLoading('auditoria-table');
        await this.buscar();
    },

    async buscar() {
        const accion = document.getElementById('audit-filtro-accion')?.value?.trim() || '';
        const desde = document.getElementById('audit-filtro-desde')?.value || '';
        const hasta = document.getElementById('audit-filtro-hasta')?.value || '';

        const params = new URLSearchParams();
        if (accion) params.set('accion', accion);
        if (desde) params.set('desde', desde);
        if (hasta) params.set('hasta', hasta);
        params.set('limite', '150');

        try {
            const res = await API.getAuditoria(params.toString());
            const data = res?.data || {};

            this.renderStats(data.stats || {});
            this.renderAcciones(data.acciones_top || []);

            Utils.renderTable('auditoria-table', [
                { key: 'created_at', label: 'Fecha y hora', format: 'datetime' },
                { key: 'usuario_email', label: 'Usuario' },
                { key: 'usuario_rol', label: 'Rol', format: 'badge' },
                { key: 'accion', label: 'Acción', format: 'badge' },
                { key: 'detalle', label: 'Detalle' }
            ], data.logs || []);
        } catch (e) {
            Utils.notify(e.message, 'danger');
        }
    },

    renderStats(stats) {
        const el = document.getElementById('auditoria-stats');
        if (!el) return;

        el.innerHTML = `
            <div class="kpi-grid">
                <div class="kpi-card primary">
                    <div class="kpi-label">Eventos totales</div>
                    <div class="kpi-value">${stats.total || 0}</div>
                </div>
                <div class="kpi-card success">
                    <div class="kpi-label">Inicios de sesión</div>
                    <div class="kpi-value">${stats.logins || 0}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Actividad hoy</div>
                    <div class="kpi-value">${stats.hoy || 0}</div>
                </div>
            </div>
        `;
    },

    renderAcciones(acciones) {
        const el = document.getElementById('auditoria-acciones');
        if (!el || !acciones.length) return;

        el.innerHTML = acciones.map(a => `
            <button type="button" class="audit-chip" onclick="document.getElementById('audit-filtro-accion').value='${a.accion}'; Auditoria.buscar()">
                ${a.accion} <span>${a.total}</span>
            </button>
        `).join('');
    },

    limpiarFiltros() {
        document.getElementById('audit-filtro-accion').value = '';
        document.getElementById('audit-filtro-desde').value = '';
        document.getElementById('audit-filtro-hasta').value = '';
        this.buscar();
    }
};
