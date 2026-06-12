/**
 * inventario.js - Módulo de inventario y productos
 */

const Inventario = {
    productos: [],

    async load() {
        Utils.showLoading('productos-table');
        try {
            const res = await API.getProductos();
            this.productos = res?.data || [];
            this.render();
        } catch (error) {
            Utils.notify('Error: ' + error.message, 'danger');
        }
    },

    render() {
        Utils.renderTable('productos-table', [
            { key: 'codigo', label: 'Código' },
            { key: 'nombre', label: 'Nombre' },
            { key: 'categoria', label: 'Categoría' },
            { key: 'stock', label: 'Stock' },
            { key: 'precio_costo', label: 'Costo', format: 'currency' },
            { key: 'precio_venta', label: 'Venta', format: 'currency' }
        ], this.productos, (row) => `
            <button class="btn btn-sm btn-outline" onclick="Inventario.editarStock(${row.id})">Editar Stock</button>
        `);
    },

    async loadAlertas() {
        try {
            const res = await API.getAlertasStock();
            const alertas = res?.data || [];
            const container = document.getElementById('alertas-stock');
            if (!container) return;

            if (alertas.length === 0) {
                container.innerHTML = '<div class="alert alert-success">No hay productos con stock bajo</div>';
                return;
            }

            container.innerHTML = alertas.map(p =>
                `<div class="alert alert-danger">⚠️ <strong>${p.nombre}</strong> (${p.codigo}) - Stock: ${p.stock}</div>`
            ).join('');
        } catch (error) {
            Utils.notify('Error al cargar alertas', 'danger');
        }
    },

    showCrearModal() {
        document.getElementById('producto-form').reset();
        Utils.openModal('modal-producto');
    },

    async crearProducto(e) {
        e.preventDefault();
        const form = e.target;
        const data = {
            codigo: form.codigo.value,
            nombre: form.nombre.value,
            descripcion: form.descripcion.value,
            precio_costo: parseFloat(form.precio_costo.value),
            precio_venta: parseFloat(form.precio_venta.value),
            stock: parseInt(form.stock.value) || 0,
            categoria: form.categoria.value
        };

        try {
            await API.crearProducto(data);
            Utils.notify('Producto creado exitosamente');
            Utils.closeModal('modal-producto');
            this.load();
        } catch (error) {
            Utils.notify(error.message, 'danger');
        }
    },

    editarStock(id) {
        const producto = this.productos.find(p => p.id === id);
        if (!producto) return;

        const nuevoStock = prompt(`Stock actual de "${producto.nombre}": ${producto.stock}\nIngrese nuevo stock:`);
        if (nuevoStock === null) return;

        API.actualizarProducto(id, { stock: parseInt(nuevoStock) })
            .then(() => { Utils.notify('Stock actualizado'); this.load(); })
            .catch(err => Utils.notify(err.message, 'danger'));
    }
};
