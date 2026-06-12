/**
 * utils.js - Utilidades comunes del frontend EasyERP
 */

const Utils = {
    /** Formatea un número como moneda */
    formatCurrency(amount) {
        return new Intl.NumberFormat('es-ES', {
            style: 'currency',
            currency: 'USD'
        }).format(amount || 0);
    },

    /** Formatea una fecha */
    formatDate(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString('es-ES', {
            year: 'numeric', month: 'short', day: 'numeric'
        });
    },

    formatDateTime(dateStr) {
        if (!dateStr) return '-';
        const date = new Date(dateStr.includes('T') ? dateStr : dateStr.replace(' ', 'T'));
        return date.toLocaleString('es-ES', {
            year: 'numeric', month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
    },

    /** Obtiene la fecha actual en formato YYYY-MM-DD */
    today() {
        return new Date().toISOString().split('T')[0];
    },

    /** Muestra una notificación temporal */
    notify(message, type = 'success') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;
        alert.textContent = message;
        alert.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;min-width:250px;animation:fadeIn 0.3s';

        document.body.appendChild(alert);
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.3s';
            setTimeout(() => alert.remove(), 300);
        }, 3000);
    },

    /** Genera badge HTML según estado */
    statusBadge(estado) {
        const map = {
            'activo': 'success', 'pagada': 'success', 'recibida': 'success',
            'pendiente': 'warning', 'inactivo': 'danger', 'anulada': 'danger',
            'cancelada': 'danger', 'ingreso': 'success', 'egreso': 'danger',
            'entrada': 'success', 'salida': 'danger'
        };
        const cls = map[estado] || 'info';
        return `<span class="badge badge-${cls}">${estado}</span>`;
    },

    /** Abre/cierra modal */
    openModal(id) {
        document.getElementById(id)?.classList.add('active');
    },

    closeModal(id) {
        document.getElementById(id)?.classList.remove('active');
    },

    /** Muestra loading en un contenedor */
    showLoading(containerId) {
        const el = document.getElementById(containerId);
        if (el) el.innerHTML = '<div class="loading"><div class="spinner"></div><p>Cargando...</p></div>';
    },

    /** Renderiza tabla genérica */
    renderTable(containerId, headers, rows, actions = '') {
        const el = document.getElementById(containerId);
        if (!el) return;

        if (!rows || rows.length === 0) {
            el.innerHTML = '<div class="empty-state"><div class="icon">📭</div><p>No hay datos disponibles</p></div>';
            return;
        }

        let html = '<div class="table-container"><table><thead><tr>';
        headers.forEach(h => html += `<th>${h.label}</th>`);
        if (actions) html += '<th>Acciones</th>';
        html += '</tr></thead><tbody>';

        rows.forEach(row => {
            html += '<tr>';
            headers.forEach(h => {
                let val = row[h.key];
                if (h.format === 'currency') val = this.formatCurrency(val);
                else if (h.format === 'date') val = this.formatDate(val);
                else if (h.format === 'datetime') val = this.formatDateTime(val);
                else if (h.format === 'badge') val = this.statusBadge(val);
                html += `<td>${val ?? '-'}</td>`;
            });
            if (actions) html += `<td>${actions(row)}</td>`;
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        el.innerHTML = html;
    }
};
