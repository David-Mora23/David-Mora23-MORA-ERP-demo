/**
 * ventas.js - Módulo de ventas, clientes y facturas
 */

const Ventas = {
    clientes: [],
    facturas: [],

    async loadClientes() {
        Utils.showLoading('clientes-table');
        try {
            const res = await API.getClientes();
            this.clientes = res?.data || [];
            Utils.renderTable('clientes-table', [
                { key: 'nombre', label: 'Nombre' },
                { key: 'email', label: 'Email' },
                { key: 'telefono', label: 'Teléfono' },
                { key: 'ruc', label: 'RUC' }
            ], this.clientes);
        } catch (error) {
            Utils.notify('Error: ' + error.message, 'danger');
        }
    },

    async loadFacturas() {
        Utils.showLoading('facturas-table');
        try {
            const res = await API.getFacturas();
            this.facturas = res?.data || [];
            Utils.renderTable('facturas-table', [
                { key: 'id', label: '#' },
                { key: 'fecha', label: 'Fecha', format: 'date' },
                { key: 'cliente_nombre', label: 'Cliente' },
                { key: 'total', label: 'Total', format: 'currency' },
                { key: 'estado', label: 'Estado', format: 'badge' }
            ], this.facturas);
        } catch (error) {
            Utils.notify('Error: ' + error.message, 'danger');
        }
    },

    showCrearCliente() {
        document.getElementById('cliente-form').reset();
        Utils.openModal('modal-cliente');
    },

    async crearCliente(e) {
        e.preventDefault();
        const form = e.target;
        try {
            await API.crearCliente({
                nombre: form.nombre.value,
                email: form.email.value,
                telefono: form.telefono.value,
                direccion: form.direccion.value,
                ruc: form.ruc.value
            });
            Utils.notify('Cliente creado');
            Utils.closeModal('modal-cliente');
            this.loadClientes();
        } catch (error) {
            Utils.notify(error.message, 'danger');
        }
    },

    showCrearFactura() {
        document.getElementById('factura-form').reset();
        const select = document.getElementById('factura-cliente');
        select.innerHTML = this.clientes.map(c =>
            `<option value="${c.id}">${c.nombre}</option>`
        ).join('');
        Utils.openModal('modal-factura');
    },

    async crearFactura(e) {
        e.preventDefault();
        const form = e.target;
        const productoId = parseInt(form.producto_id.value);
        const cantidad = parseInt(form.cantidad.value);
        const precio = parseFloat(form.precio_unitario.value);

        try {
            await API.crearFactura({
                cliente_id: parseInt(form.cliente_id.value),
                fecha: form.fecha.value || Utils.today(),
                items: [{ producto_id: productoId, cantidad, precio_unitario: precio }]
            });
            Utils.notify('Factura creada');
            Utils.closeModal('modal-factura');
            this.loadFacturas();
        } catch (error) {
            Utils.notify(error.message, 'danger');
        }
    }
};
