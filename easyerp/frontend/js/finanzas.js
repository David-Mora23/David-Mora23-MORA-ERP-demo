/**
 * finanzas.js - Módulo de finanzas y contabilidad
 */

const Finanzas = {
    async load() {
        Utils.showLoading('transacciones-table');
        try {
            const [transRes, resumenRes] = await Promise.all([
                API.getTransacciones(),
                API.getResumenFinanciero()
            ]);

            if (transRes?.data) {
                Utils.renderTable('transacciones-table', [
                    { key: 'id', label: '#' },
                    { key: 'fecha', label: 'Fecha', format: 'date' },
                    { key: 'tipo', label: 'Tipo', format: 'badge' },
                    { key: 'descripcion', label: 'Descripción' },
                    { key: 'monto', label: 'Monto', format: 'currency' },
                    { key: 'usuario_email', label: 'Usuario' }
                ], transRes.data);
            }

            if (resumenRes?.data) this.renderResumen(resumenRes.data);
        } catch (error) {
            Utils.notify('Error: ' + error.message, 'danger');
        }
    },

    renderResumen(data) {
        const container = document.getElementById('resumen-financiero');
        if (!container) return;

        const mes = data.mes_actual || {};
        const balanceCls = data.balance >= 0 ? 'success' : 'danger';
        const mesCls = (mes.balance || 0) >= 0 ? 'success' : 'warning';

        container.innerHTML = `
            <div class="kpi-grid">
                <div class="kpi-card success">
                    <div class="kpi-label">Ingresos acumulados</div>
                    <div class="kpi-value">${Utils.formatCurrency(data.total_ingresos)}</div>
                </div>
                <div class="kpi-card danger">
                    <div class="kpi-label">Egresos acumulados</div>
                    <div class="kpi-value">${Utils.formatCurrency(data.total_egresos)}</div>
                </div>
                <div class="kpi-card ${balanceCls}">
                    <div class="kpi-label">Resultado acumulado</div>
                    <div class="kpi-value">${Utils.formatCurrency(data.balance)}</div>
                </div>
                <div class="kpi-card primary">
                    <div class="kpi-label">Liquidez en cuentas</div>
                    <div class="kpi-value">${Utils.formatCurrency(data.saldo_cuentas)}</div>
                </div>
                <div class="kpi-card ${mesCls}">
                    <div class="kpi-label">Resultado del mes</div>
                    <div class="kpi-value">${Utils.formatCurrency(mes.balance || 0)}</div>
                </div>
            </div>
            <div class="info-banner">${data.nota_balance || ''}</div>
        `;

        this._renderFlujo(data.flujo_mensual || []);
        this._renderCuentas(data.cuentas || []);
    },

    _renderFlujo(flujo) {
        const el = document.getElementById('finanzas-flujo');
        if (!el || !flujo.length) return;

        el.innerHTML = `
            <div class="card-header"><h3>Flujo mensual</h3></div>
            <div class="flujo-grid">
                ${flujo.map(f => `
                    <div class="flujo-item">
                        <span class="flujo-mes">${f.mes}</span>
                        <span class="flujo-ing">+${Utils.formatCurrency(f.ingresos)}</span>
                        <span class="flujo-egr">−${Utils.formatCurrency(f.egresos)}</span>
                        <strong class="flujo-bal ${f.balance >= 0 ? 'pos' : 'neg'}">${Utils.formatCurrency(f.balance)}</strong>
                    </div>
                `).join('')}
            </div>
        `;
    },

    _renderCuentas(cuentas) {
        const el = document.getElementById('finanzas-cuentas');
        if (!el) return;

        Utils.renderTable('finanzas-cuentas', [
            { key: 'nombre', label: 'Cuenta' },
            { key: 'tipo', label: 'Tipo', format: 'badge' },
            { key: 'saldo', label: 'Saldo', format: 'currency' }
        ], cuentas);
    },

    showCrearModal() {
        document.getElementById('transaccion-form').reset();
        document.getElementById('trans-fecha').value = Utils.today();
        Utils.openModal('modal-transaccion');
    },

    async crearTransaccion(e) {
        e.preventDefault();
        const form = e.target;
        try {
            await API.crearTransaccion({
                tipo: form.tipo.value,
                descripcion: form.descripcion.value,
                monto: parseFloat(form.monto.value),
                fecha: form.fecha.value
            });
            Utils.notify('Transacción registrada');
            Utils.closeModal('modal-transaccion');
            this.load();
        } catch (error) {
            Utils.notify(error.message, 'danger');
        }
    }
};
