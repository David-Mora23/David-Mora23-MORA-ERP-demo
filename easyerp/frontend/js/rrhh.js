/**
 * rrhh.js - Recursos Humanos Completo
 * Gestión de empleados, asistencia, horas extras, incidencias y nómina.
 */

const RRHH = {
    currentTab: 'empleados',
    empleados: [],

    async load() {
        this.switchTab(this.currentTab);
    },

    switchTab(tab) {
        this.currentTab = tab;
        // Update tab buttons
        document.querySelectorAll('.rrhh-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        // Show/hide panels
        document.querySelectorAll('.rrhh-tab-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === `rrhh-panel-${tab}`);
        });
        // Load data for the active tab
        const loaders = {
            empleados: () => this.loadEmpleados(),
            asistencia: () => this.loadAsistencia(),
            extras: () => this.loadHorasExtras(),
            incidencias: () => this.loadIncidencias(),
            nomina: () => this.loadNomina()
        };
        if (loaders[tab]) loaders[tab]();
        this.loadResumen();
    },

    // ═══════════════════════════════════════════
    //  RESUMEN / KPIs
    // ═══════════════════════════════════════════
    async loadResumen() {
        try {
            const res = await API.getResumenRRHH();
            if (res?.data) this.renderResumen(res.data);
        } catch (e) { /* silent */ }
    },

    renderResumen(data) {
        const el = document.getElementById('rrhh-resumen');
        if (!el) return;

        el.innerHTML = `
            <div class="kpi-grid kpi-grid-6">
                <div class="kpi-card primary">
                    <div class="kpi-label">Empleados activos</div>
                    <div class="kpi-value">${data.activos} / ${data.total_empleados}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-label">Nómina mensual</div>
                    <div class="kpi-value">${Utils.formatCurrency(data.nomina_mensual)}</div>
                </div>
                <div class="kpi-card success">
                    <div class="kpi-label">Asistencia hoy</div>
                    <div class="kpi-value">${data.asistencia_hoy}</div>
                </div>
                <div class="kpi-card warning">
                    <div class="kpi-label">Faltas del mes</div>
                    <div class="kpi-value">${data.faltas_mes}</div>
                </div>
                <div class="kpi-card" style="--kpi-accent:#7C3AED">
                    <div class="kpi-label">Horas extras (mes)</div>
                    <div class="kpi-value">${data.horas_extras_mes}h</div>
                </div>
                <div class="kpi-card danger">
                    <div class="kpi-label">Incidencias (mes)</div>
                    <div class="kpi-value">${data.incidencias_mes} <small style="font-size:0.65em;opacity:0.7">(${data.incidencias_medicas} médicas)</small></div>
                </div>
            </div>
        `;
    },

    // ═══════════════════════════════════════════
    //  EMPLEADOS
    // ═══════════════════════════════════════════
    async loadEmpleados() {
        Utils.showLoading('empleados-table');
        try {
            const res = await API.getEmpleados();
            this.empleados = res?.data || [];
            Utils.renderTable('empleados-table', [
                { key: 'nombre', label: 'Nombre' },
                { key: 'cedula', label: 'Cédula' },
                { key: 'departamento', label: 'Depto.' },
                { key: 'puesto', label: 'Puesto' },
                { key: 'salario', label: 'Salario', format: 'currency' },
                { key: 'fecha_ingreso', label: 'Ingreso', format: 'date' },
                { key: 'estado', label: 'Estado', format: 'badge' }
            ], this.empleados, (row) =>
                `<button class="btn btn-sm btn-ghost" onclick="RRHH.showEditarModal(${row.id})">Editar</button>`
            );
        } catch (e) {
            Utils.notify(e.message, 'danger');
        }
    },

    showCrearModal() {
        document.getElementById('empleado-form').reset();
        document.getElementById('empleado-form').dataset.editId = '';
        document.querySelector('#modal-empleado h3').textContent = 'Nuevo empleado';
        Utils.openModal('modal-empleado');
    },

    async showEditarModal(id) {
        try {
            const emp = this.empleados.find(e => e.id === id);
            if (!emp) {
                const res = await API.getEmpleados();
                this.empleados = res?.data || [];
                const found = this.empleados.find(e => e.id === id);
                if (!found) return Utils.notify('Empleado no encontrado', 'danger');
                return this._fillEditForm(found);
            }
            this._fillEditForm(emp);
        } catch (e) {
            Utils.notify(e.message, 'danger');
        }
    },

    _fillEditForm(emp) {
        const form = document.getElementById('empleado-form');
        form.dataset.editId = emp.id;
        form.nombre.value = emp.nombre;
        form.cedula.value = emp.cedula || '';
        form.email.value = emp.email || '';
        form.puesto.value = emp.puesto;
        form.departamento.value = emp.departamento || 'General';
        form.tipo_contrato.value = emp.tipo_contrato || 'fijo';
        form.horas_semanales.value = emp.horas_semanales || 44;
        form.salario.value = emp.salario;
        form.fecha_ingreso.value = emp.fecha_ingreso;
        if (form.estado) form.estado.value = emp.estado;

        document.querySelector('#modal-empleado h3').textContent = 'Editar empleado';
        Utils.openModal('modal-empleado');
    },

    async guardarEmpleado(e) {
        e.preventDefault();
        const form = e.target;
        const payload = {
            nombre: form.nombre.value,
            cedula: form.cedula.value,
            email: form.email.value,
            puesto: form.puesto.value,
            departamento: form.departamento.value,
            tipo_contrato: form.tipo_contrato.value,
            horas_semanales: parseInt(form.horas_semanales.value) || 44,
            salario: parseFloat(form.salario.value),
            fecha_ingreso: form.fecha_ingreso.value,
            estado: form.estado?.value || 'activo'
        };

        try {
            const editId = form.dataset.editId;
            if (editId) {
                await API.actualizarEmpleado(editId, payload);
                Utils.notify('Empleado actualizado');
            } else {
                await API.crearEmpleado(payload);
                Utils.notify('Empleado registrado');
            }
            Utils.closeModal('modal-empleado');
            this.loadEmpleados();
            this.loadResumen();
        } catch (err) {
            Utils.notify(err.message, 'danger');
        }
    },

    autoFillSalario(puesto) {
        const puestosData = {
            'Gerente General': { salario: 5500, depto: 'Administración' },
            'Gerente': { salario: 4500, depto: 'Administración' },
            'Vendedor Senior': { salario: 3200, depto: 'Ventas' },
            'Vendedor Junior': { salario: 1500, depto: 'Ventas' },
            'Vendedor': { salario: 1200, depto: 'Ventas' },
            'Contadora': { salario: 3800, depto: 'Finanzas' },
            'Contador': { salario: 3800, depto: 'Finanzas' },
            'Almacenero': { salario: 2500, depto: 'Almacén' },
            'Asistente RRHH': { salario: 2800, depto: 'RRHH' },
            'Operario': { salario: 500, depto: 'Operaciones' }
        };
        const normalizado = (puesto || '').trim();
        const match = Object.keys(puestosData).find(k => k.toLowerCase() === normalizado.toLowerCase());
        
        if (match) {
            const form = document.getElementById('empleado-form');
            if (form) {
                if (form.salario) form.salario.value = puestosData[match].salario;
                if (form.departamento) form.departamento.value = puestosData[match].depto;
            }
        }
    },

    // ═══════════════════════════════════════════
    //  ASISTENCIA
    // ═══════════════════════════════════════════
    async loadAsistencia() {
        Utils.showLoading('asistencia-table');
        try {
            const res = await API.getAsistencia();
            const data = (res?.data || []).slice(0, 50);
            const tipoLabels = {
                'normal': '<span class="badge badge-success">Normal</span>',
                'tardanza': '<span class="badge badge-warning">Tardanza</span>',
                'falta_justificada': '<span class="badge badge-info">Falta Just.</span>',
                'falta_injustificada': '<span class="badge badge-danger">Falta Injust.</span>'
            };
            // Map tipo for display
            const mapped = data.map(r => ({
                ...r,
                tipo_badge: tipoLabels[r.tipo] || r.tipo,
                horas_trabajadas: r.horas_trabajadas ? r.horas_trabajadas.toFixed(1) + 'h' : '-',
                horas_extra_display: r.horas_extra > 0 ? r.horas_extra.toFixed(1) + 'h' : '-'
            }));

            Utils.renderTable('asistencia-table', [
                { key: 'empleado_nombre', label: 'Empleado' },
                { key: 'fecha', label: 'Fecha', format: 'date' },
                { key: 'entrada', label: 'Entrada' },
                { key: 'salida', label: 'Salida' },
                { key: 'horas_trabajadas', label: 'Horas Trab.' },
                { key: 'horas_extra_display', label: 'H. Extra' },
                { key: 'tipo_badge', label: 'Tipo' },
                { key: 'observacion', label: 'Observación' }
            ], mapped);
        } catch (e) {
            Utils.notify(e.message, 'danger');
        }
    },

    // ═══════════════════════════════════════════
    //  HORAS EXTRAS
    // ═══════════════════════════════════════════
    async loadHorasExtras() {
        Utils.showLoading('horas-extras-table');
        try {
            const res = await API.getHorasExtras();
            const data = res?.data || [];
            const tipoLabels = { 'normal': '1.5x Normal', 'doble': '2x Doble', 'triple': '3x Triple' };
            const mapped = data.map(r => ({
                ...r,
                tipo_label: tipoLabels[r.tipo] || r.tipo,
                aprobado_badge: r.aprobado
                    ? '<span class="badge badge-success">Aprobado</span>'
                    : '<span class="badge badge-warning">Pendiente</span>'
            }));

            Utils.renderTable('horas-extras-table', [
                { key: 'empleado_nombre', label: 'Empleado' },
                { key: 'fecha', label: 'Fecha', format: 'date' },
                { key: 'horas', label: 'Horas' },
                { key: 'tipo_label', label: 'Tipo' },
                { key: 'monto', label: 'Monto', format: 'currency' },
                { key: 'aprobado_badge', label: 'Estado' },
                { key: 'observacion', label: 'Observación' }
            ], mapped, (row) => !row.aprobado
                ? `<button class="btn btn-sm btn-primary" onclick="RRHH.aprobarExtras(${row.id})">Aprobar</button>`
                : ''
            );
        } catch (e) {
            Utils.notify(e.message, 'danger');
        }
    },

    showRegistrarExtrasModal() {
        document.getElementById('horas-extras-form').reset();
        this._populateEmpleadoSelect('he-empleado-select');
        Utils.openModal('modal-horas-extras');
    },

    async guardarHorasExtras(e) {
        e.preventDefault();
        const form = e.target;
        try {
            await API.registrarHorasExtras({
                empleado_id: parseInt(form.empleado_id.value),
                fecha: form.fecha.value,
                horas: parseFloat(form.horas.value),
                tipo: form.tipo.value,
                observacion: form.observacion.value,
                aprobado: form.aprobado?.checked ? 1 : 0
            });
            Utils.notify('Horas extras registradas');
            Utils.closeModal('modal-horas-extras');
            this.loadHorasExtras();
            this.loadResumen();
        } catch (err) {
            Utils.notify(err.message, 'danger');
        }
    },

    async aprobarExtras(id) {
        try {
            await API.aprobarHorasExtras(id, 1);
            Utils.notify('Horas extras aprobadas');
            this.loadHorasExtras();
        } catch (err) {
            Utils.notify(err.message, 'danger');
        }
    },

    // ═══════════════════════════════════════════
    //  INCIDENCIAS
    // ═══════════════════════════════════════════
    async loadIncidencias() {
        Utils.showLoading('incidencias-table');
        try {
            const res = await API.getIncidencias();
            const data = res?.data || [];
            const tipoLabels = {
                'medica': '🏥 Médica', 'personal': '👤 Personal',
                'disciplinaria': '⚠️ Disciplinaria', 'accidente': '🚨 Accidente', 'otra': '📋 Otra'
            };
            const mapped = data.map(r => ({
                ...r,
                tipo_label: tipoLabels[r.tipo] || r.tipo,
                justificada_badge: r.justificada
                    ? '<span class="badge badge-success">Sí</span>'
                    : '<span class="badge badge-danger">No</span>'
            }));

            Utils.renderTable('incidencias-table', [
                { key: 'empleado_nombre', label: 'Empleado' },
                { key: 'fecha', label: 'Fecha', format: 'date' },
                { key: 'tipo_label', label: 'Tipo' },
                { key: 'descripcion', label: 'Descripción' },
                { key: 'dias_ausencia', label: 'Días Aus.' },
                { key: 'justificada_badge', label: 'Justificada' },
                { key: 'documento_soporte', label: 'Documento' }
            ], mapped);
        } catch (e) {
            Utils.notify(e.message, 'danger');
        }
    },

    showRegistrarIncidenciaModal() {
        document.getElementById('incidencia-form').reset();
        this._populateEmpleadoSelect('inc-empleado-select');
        Utils.openModal('modal-incidencia');
    },

    async guardarIncidencia(e) {
        e.preventDefault();
        const form = e.target;
        try {
            await API.registrarIncidencia({
                empleado_id: parseInt(form.empleado_id.value),
                fecha: form.fecha.value,
                tipo: form.tipo.value,
                descripcion: form.descripcion.value,
                dias_ausencia: parseInt(form.dias_ausencia.value) || 0,
                justificada: form.justificada?.checked ? 1 : 0,
                documento_soporte: form.documento_soporte?.value || ''
            });
            Utils.notify('Incidencia registrada');
            Utils.closeModal('modal-incidencia');
            this.loadIncidencias();
            this.loadResumen();
        } catch (err) {
            Utils.notify(err.message, 'danger');
        }
    },

    // ═══════════════════════════════════════════
    //  NÓMINA
    // ═══════════════════════════════════════════
    async loadNomina() {
        Utils.showLoading('nomina-table');
        try {
            const periodoInput = document.getElementById('nomina-periodo-filter');
            const periodo = periodoInput?.value || '';
            const params = periodo ? `?periodo=${periodo}` : '';
            const res = await API.getNomina(params);
            const data = res?.data || [];

            Utils.renderTable('nomina-table', [
                { key: 'empleado_nombre', label: 'Empleado' },
                { key: 'periodo', label: 'Periodo' },
                { key: 'salario_bruto', label: 'Sal. Bruto', format: 'currency' },
                { key: 'horas_extras_monto', label: 'H. Extras $', format: 'currency' },
                { key: 'total_ingresos', label: 'Total Ing.', format: 'currency' },
                { key: 'deduccion_iess', label: 'IESS (9.45%)', format: 'currency' },
                { key: 'deduccion_isr', label: 'ISR', format: 'currency' },
                { key: 'desc_faltas_injustificadas', label: 'Desc. Faltas', format: 'currency' },
                { key: 'total_deducciones', label: 'Total Ded.', format: 'currency' },
                { key: 'salario_neto', label: 'Sal. Neto', format: 'currency' },
                { key: 'estado', label: 'Estado', format: 'badge' }
            ], data, (row) => row.estado === 'pendiente'
                ? `<button class="btn btn-sm btn-primary" onclick="RRHH.pagarNomina(${row.id})">Pagar</button>`
                : `<span style="color:var(--text-muted);font-size:0.8em">${row.fecha_pago || ''}</span>`
            );

            // Render totals
            if (data.length > 0) {
                const totales = data.reduce((acc, n) => ({
                    bruto: acc.bruto + n.salario_bruto,
                    extras: acc.extras + n.horas_extras_monto,
                    ingresos: acc.ingresos + n.total_ingresos,
                    sfs: acc.sfs + n.deduccion_sfs,
                    afp: acc.afp + n.deduccion_afp,
                    isr: acc.isr + n.deduccion_isr,
                    deducciones: acc.deducciones + n.total_deducciones,
                    neto: acc.neto + n.salario_neto,
                }), { bruto: 0, extras: 0, ingresos: 0, sfs: 0, afp: 0, isr: 0, deducciones: 0, neto: 0 });

                const totalsEl = document.getElementById('nomina-totals');
                if (totalsEl) {
                    totalsEl.innerHTML = `
                        <div class="nomina-totals-grid">
                            <div class="nomina-total-item">
                                <span class="nomina-total-label">Total Ingresos</span>
                                <span class="nomina-total-value income">${Utils.formatCurrency(totales.ingresos)}</span>
                            </div>
                            <div class="nomina-total-item">
                                <span class="nomina-total-label">Total Deducciones</span>
                                <span class="nomina-total-value expense">${Utils.formatCurrency(totales.deducciones)}</span>
                            </div>
                            <div class="nomina-total-item highlight">
                                <span class="nomina-total-label">Total Neto a Pagar</span>
                                <span class="nomina-total-value">${Utils.formatCurrency(totales.neto)}</span>
                            </div>
                        </div>
                    `;
                }
            }
        } catch (e) {
            Utils.notify(e.message, 'danger');
        }
    },

    showGenerarNominaModal() {
        document.getElementById('generar-nomina-form').reset();
        // Default periodo = current month
        const now = new Date();
        const periodo = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
        document.getElementById('generar-nomina-periodo').value = periodo;
        Utils.openModal('modal-generar-nomina');
    },

    async generarNomina(e) {
        e.preventDefault();
        const form = e.target;
        try {
            const res = await API.generarNomina({
                periodo: form.periodo.value,
                bonificaciones: parseFloat(form.bonificaciones?.value) || 0,
                otras_deducciones: parseFloat(form.otras_deducciones?.value) || 0
            });
            const count = res?.data?.length || 0;
            Utils.notify(`Nómina generada para ${count} empleados`);
            Utils.closeModal('modal-generar-nomina');
            this.loadNomina();
            this.loadResumen();
        } catch (err) {
            Utils.notify(err.message, 'danger');
        }
    },

    async pagarNomina(id) {
        try {
            await API.pagarNomina(id);
            Utils.notify('Nómina pagada');
            this.loadNomina();
        } catch (err) {
            Utils.notify(err.message, 'danger');
        }
    },

    async pagarPeriodo() {
        const periodoInput = document.getElementById('nomina-periodo-filter');
        const periodo = periodoInput?.value;
        if (!periodo) return Utils.notify('Selecciona un periodo primero', 'warning');
        try {
            const res = await API.pagarPeriodo(periodo);
            Utils.notify(res?.message || 'Periodo pagado');
            this.loadNomina();
        } catch (err) {
            Utils.notify(err.message, 'danger');
        }
    },

    // ═══════════════════════════════════════════
    //  HELPERS
    // ═══════════════════════════════════════════
    async _populateEmpleadoSelect(selectId) {
        const select = document.getElementById(selectId);
        if (!select) return;

        if (this.empleados.length === 0) {
            try {
                const res = await API.getEmpleados();
                this.empleados = res?.data || [];
            } catch (e) { return; }
        }

        select.innerHTML = this.empleados
            .filter(e => e.estado === 'activo')
            .map(e => `<option value="${e.id}">${e.nombre} — ${e.puesto}</option>`)
            .join('');
    }
};
