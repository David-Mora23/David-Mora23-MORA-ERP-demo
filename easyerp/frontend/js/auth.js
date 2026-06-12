/**
 * auth.js - Manejo de autenticación JWT en el frontend
 */

const Auth = {
    /** Verifica si hay sesión activa */
    isLoggedIn() {
        return !!localStorage.getItem('erp_token');
    },

    /** Obtiene datos del usuario en sesión */
    getUser() {
        const user = localStorage.getItem('erp_user');
        return user ? JSON.parse(user) : null;
    },

    /** Guarda token y datos de usuario */
    setSession(token, user) {
        localStorage.setItem('erp_token', token);
        localStorage.setItem('erp_user', JSON.stringify(user));
    },

    /** Cierra sesión */
    logout() {
        const token = localStorage.getItem('erp_token');
        if (token) {
            fetch(`${API_BASE}/auth/logout`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            }).catch(() => {});
        }
        localStorage.removeItem('erp_token');
        localStorage.removeItem('erp_user');
        window.location.href = '/login';
    },

    /** Protege páginas que requieren autenticación */
    requireAuth() {
        if (!this.isLoggedIn()) {
            window.location.href = '/login';
            return false;
        }
        return true;
    },

    /** Inicializa la UI con datos del usuario */
    initUserUI() {
        const user = this.getUser();
        if (!user) return;

        const emailEl = document.getElementById('user-email');
        const rolEl = document.getElementById('user-rol');
        if (emailEl) emailEl.textContent = user.email;
        if (rolEl) rolEl.textContent = user.rol;
    },

    /** Maneja el formulario de login */
    initLoginForm() {
        const form = document.getElementById('login-form');
        if (!form) return;

        // Si ya está logueado, redirigir
        if (this.isLoggedIn()) {
            window.location.href = '/';
            return;
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const errorEl = document.getElementById('login-error');
            const btn = form.querySelector('button[type="submit"]');

            btn.disabled = true;
            btn.textContent = 'Ingresando...';
            errorEl.style.display = 'none';

            try {
                const response = await API.login(email, password);
                if (response && response.data) {
                    this.setSession(response.data.access_token, response.data.user);
                    window.location.href = '/';
                }
            } catch (error) {
                errorEl.textContent = error.message || 'Error al iniciar sesión';
                errorEl.style.display = 'block';
            } finally {
                btn.disabled = false;
                btn.textContent = 'Iniciar Sesión';
            }
        });
    }
};
