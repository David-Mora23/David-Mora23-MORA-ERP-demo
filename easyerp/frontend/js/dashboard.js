/**
 * dashboard.js - Dashboard principal con KPIs, gráficos y mapa de módulos
 */

const Dashboard = {
    ERP_MODULES: [
        { id: 'inventario', name: 'Inventario', desc: 'Productos, stock y alertas', status: 'ok', section: 'inventario' },
        { id: 'ventas', name: 'Ventas & CRM', desc: 'Clientes, facturas y reportes', status: 'ok', section: 'ventas' },
        { id: 'compras', name: 'Compras', desc: 'Proveedores y órdenes', status: 'ok', section: 'compras' },
        { id: 'finanzas', name: 'Finanzas', desc: 'Flujo, cuentas y transacciones', status: 'ok', section: 'finanzas' },
        { id: 'rrhh', name: 'Recursos Humanos', desc: 'Nómina, empleados y asistencia', status: 'ok', section: 'rrhh' },
        { id: 'reportes', name: 'Reportes', desc: 'Exportación PDF y Excel', status: 'ok', section: 'reportes' },
        { id: 'usuarios', name: 'Usuarios & Roles', desc: 'Admin, Gerente, Vendedor, Contador', status: 'ok', section: 'usuarios' },
        { id: 'auditoria', name: 'Auditoría', desc: 'Logs, logins y cambios del sistema', status: 'ok', section: 'auditoria' },
        { id: 'ia', name: 'Asistente IA', desc: 'ChatGPT + Gemini con respaldo', status: 'ok', section: null },
        { id: 'contabilidad', name: 'Contabilidad formal', desc: 'Asientos, balance, P&G', status: 'missing', section: null },
        { id: 'produccion', name: 'Producción / MRP', desc: 'Órdenes de fabricación', status: 'missing', section: null },
        { id: 'presupuestos', name: 'Presupuestos', desc: 'Planificación financiera', status: 'missing', section: null },
    ],

    async load() {
        try {
            const [kpisRes, graficosRes] = await Promise.all([
                API.getKPIs(),
                API.getGraficos()
            ]);

            this.renderModulos();
            if (kpisRes?.data) this.renderKPIs(kpisRes.data);
            if (graficosRes?.data) this.renderGraficos(graficosRes.data);
        } catch (error) {
            Utils.notify('Error al cargar dashboard: ' + error.message, 'danger');
        }
    },

    renderModulos() {
        const container = document.getElementById('erp-modules-map');
        if (!container) return;

        const user = Auth.getUser();
        const rol = user?.rol || 'Vendedor';
        const config = typeof ROL_CONFIG !== 'undefined' ? ROL_CONFIG[rol] : null;
        const modulosPermitidos = config?.modulos || [];

        const statusLabel = {
            ok: 'Implementado',
            partial: 'Básico',
            missing: 'Pendiente'
        };

        container.innerHTML = this.ERP_MODULES.map(mod => {
            const canNavigate = mod.section && modulosPermitidos.includes(mod.section);
            const clickable = canNavigate ? `onclick="Dashboard.irModulo('${mod.section}')"` : '';
            const cls = canNavigate ? 'module-card clickable' : 'module-card';

            return `
                <div class="${cls}" ${clickable}>
                    <div class="module-card-top">
                        <span class="module-dot status-${mod.status}"></span>
                        <span class="module-status">${statusLabel[mod.status]}</span>
                    </div>
                    <strong>${mod.name}</strong>
                    <p>${mod.desc}</p>
                </div>
            `;
        }).join('');
    },

    irModulo(section) {
        const link = document.querySelector(`.nav-link[data-section="${section}"]`);
        if (link && !link.classList.contains('hidden')) {
            link.click();
        }
    },

    renderKPIs(data) {
        const container = document.getElementById('kpi-grid');
        if (!container) return;

        const kpis = [
            { label: 'Total Ventas', value: Utils.formatCurrency(data.total_ventas), cls: 'success' },
            { label: 'Facturas', value: data.num_facturas, cls: '' },
            { label: 'Productos', value: data.total_productos, cls: '' },
            { label: 'Stock Bajo', value: data.stock_bajo, cls: data.stock_bajo > 0 ? 'warning' : 'success' },
            { label: 'Clientes', value: data.total_clientes, cls: '' },
            { label: 'Empleados', value: data.total_empleados, cls: '' },
            { label: 'Balance Financiero', value: Utils.formatCurrency(data.balance_financiero), cls: data.balance_financiero >= 0 ? 'success' : 'danger' },
            { label: 'Valor Inventario', value: Utils.formatCurrency(data.valor_inventario), cls: '' },
        ];

        container.innerHTML = kpis.map(k => `
            <div class="kpi-card ${k.cls}">
                <div class="kpi-label">${k.label}</div>
                <div class="kpi-value">${k.value}</div>
            </div>
        `).join('');
    },

    renderGraficos(data) {
        const ventasContainer = document.getElementById('chart-ventas');
        if (ventasContainer && data.ventas_por_mes?.length) {
            const max = Math.max(...data.ventas_por_mes.map(v => v.total));
            ventasContainer.innerHTML = data.ventas_por_mes.reverse().map(v => {
                const height = max > 0 ? (v.total / max * 150) : 10;
                return `<div class="chart-bar" style="height:${height}px">
                    <span class="chart-bar-value">${Utils.formatCurrency(v.total)}</span>
                    <span class="chart-bar-label">${v.mes}</span>
                </div>`;
            }).join('');
        }

        const topContainer = document.getElementById('top-productos');
        if (topContainer && data.top_productos?.length) {
            Utils.renderTable('top-productos', [
                { key: 'nombre', label: 'Producto' },
                { key: 'vendidos', label: 'Vendidos' },
                { key: 'ingresos', label: 'Ingresos', format: 'currency' }
            ], data.top_productos);
        }

        const catContainer = document.getElementById('chart-categorias');
        if (catContainer && data.productos_por_categoria?.length) {
            const max = Math.max(...data.productos_por_categoria.map(c => c.cantidad));
            catContainer.innerHTML = data.productos_por_categoria.map(c => {
                const height = max > 0 ? (c.cantidad / max * 150) : 10;
                return `<div class="chart-bar" style="height:${height}px;background:linear-gradient(180deg,#2563EB,#7C3AED)">
                    <span class="chart-bar-value">${c.cantidad}</span>
                    <span class="chart-bar-label">${c.categoria}</span>
                </div>`;
            }).join('');
        }
    }
};
