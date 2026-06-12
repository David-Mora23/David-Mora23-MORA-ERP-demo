/**
 * usuarios.js - Gestión de usuarios del sistema (solo Admin)
 */

const Usuarios = {
    editingId: null,

    ROLES_NUEVO: ['Gerente', 'Vendedor', 'Contador'],

    _renderRolSelect(rolActual = 'Gerente', esAdmin = false) {
        const select = document.getElementById('usuario-rol-select');
        if (!select) return;

        if (esAdmin) {
            select.innerHTML = '<option value="Admin">Admin</option>';
            select.value = 'Admin';
            select.disabled = true;
            return;
        }

        select.disabled = false;
        select.innerHTML = this.ROLES_NUEVO.map(r =>
            `<option value="${r}">${r}</option>`
        ).join('');
        select.value = this.ROLES_NUEVO.includes(rolActual) ? rolActual : 'Gerente';
    },

    _puedeEliminar(row, currentUser) {
        return row.rol !== 'Admin' && currentUser?.id !== row.id;
    },

    async load() {
        Utils.showLoading('usuarios-table');
        try {
            const res = await API.getUsuarios();
            const currentUser = Auth.getUser();
            Utils.renderTable('usuarios-table', [
                { key: 'email', label: 'Email' },
                { key: 'rol', label: 'Rol', format: 'badge' },
                { key: 'created_at', label: 'Registrado', format: 'date' }
            ], res?.data || [], (row) => {
                let actions = `<button class="btn btn-sm btn-ghost" onclick="Usuarios.showEditarModal(${row.id})">Editar</button>`;
                if (this._puedeEliminar(row, currentUser)) {
                    actions += ` <button class="btn btn-sm btn-danger" onclick="Usuarios.eliminar(${row.id}, '${row.email.replace(/'/g, "\\'")}')">Eliminar</button>`;
                }
                if (currentUser?.id === row.id) {
                    actions += ` <span class="badge badge-info">Tú</span>`;
                } else if (row.rol === 'Admin') {
                    actions += ` <span class="badge badge-default">Protegido</span>`;
                }
                return actions;
            });
        } catch (e) {
            Utils.notify(e.message, 'danger');
        }
    },

    showCrearModal() {
        this.editingId = null;
        document.getElementById('usuario-modal-title').textContent = 'Nuevo usuario';
        document.getElementById('usuario-form').reset();
        document.getElementById('usuario-password-group').style.display = '';
        document.getElementById('usuario-password').required = true;
        document.getElementById('usuario-password-hint').textContent = 'Mínimo 6 caracteres';
        this._renderRolSelect('Gerente', false);
        Utils.openModal('modal-usuario');
    },

    async showEditarModal(id) {
        try {
            const res = await API.getUsuarios();
            const usuario = (res?.data || []).find(u => u.id === id);
            if (!usuario) {
                Utils.notify('Usuario no encontrado', 'danger');
                return;
            }

            this.editingId = id;
            const form = document.getElementById('usuario-form');
            form.email.value = usuario.email;
            form.password.value = '';
            this._renderRolSelect(usuario.rol, usuario.rol === 'Admin');

            document.getElementById('usuario-modal-title').textContent = 'Editar usuario';
            document.getElementById('usuario-password-group').style.display = '';
            document.getElementById('usuario-password').required = false;
            document.getElementById('usuario-password-hint').textContent =
                'Deja en blanco para mantener la contraseña actual';

            Utils.openModal('modal-usuario');
        } catch (e) {
            Utils.notify(e.message, 'danger');
        }
    },

    async guardar(e) {
        e.preventDefault();
        const form = e.target;
        const payload = {
            email: form.email.value.trim(),
            rol: form.rol.value
        };

        try {
            if (this.editingId) {
                const password = form.password.value.trim();
                if (password) payload.password = password;
                await API.actualizarUsuario(this.editingId, payload);
                Utils.notify('Usuario actualizado');
            } else {
                payload.password = form.password.value;
                await API.crearUsuario(payload);
                Utils.notify('Usuario creado');
            }

            Utils.closeModal('modal-usuario');
            this.load();
        } catch (err) {
            Utils.notify(err.message, 'danger');
        }
    },

    async eliminar(id, email) {
        if (!confirm(`¿Eliminar al usuario ${email}?\n\nEsta acción no se puede deshacer.`)) return;

        try {
            await API.eliminarUsuario(id);
            Utils.notify('Usuario eliminado');
            this.load();
        } catch (err) {
            Utils.notify(err.message, 'danger');
        }
    }
};
