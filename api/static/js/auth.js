document.addEventListener('DOMContentLoaded', () => {
    const loginTab = document.getElementById('login-tab');
    const registerTab = document.getElementById('register-tab');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const messageBox = document.getElementById('auth-message');

    // Switch Tabs
    loginTab.addEventListener('click', () => {
        loginTab.classList.add('active');
        registerTab.classList.remove('active');
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        messageBox.style.display = 'none';
    });

    registerTab.addEventListener('click', () => {
        registerTab.classList.add('active');
        loginTab.classList.remove('active');
        registerForm.style.display = 'block';
        loginForm.style.display = 'none';
        messageBox.style.display = 'none';
    });

    const showMessage = (msg, type) => {
        messageBox.textContent = msg;
        messageBox.className = `message ${type}`;
        messageBox.style.display = 'block';
    };

    // Handle Login
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('api_key', data.api_key);
                localStorage.setItem('username', data.username);
                showMessage('¡Ingreso exitoso! Redirigiendo...', 'success');
                setTimeout(() => window.location.href = '/', 1000);
            } else {
                showMessage(data.detail || 'Error en el ingreso', 'error');
            }
        } catch (err) {
            showMessage('Error de conexión', 'error');
        }
    });

    // Handle Register
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('reg-username').value;
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            });

            const data = await response.json();

            if (response.ok) {
                showMessage('Registro completado. Ya puedes ingresar.', 'success');
                setTimeout(() => loginTab.click(), 1500);
            } else {
                showMessage(data.detail || 'Error en el registro', 'error');
            }
        } catch (err) {
            showMessage('Error de conexión', 'error');
        }
    });
});
