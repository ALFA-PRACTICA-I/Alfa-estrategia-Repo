
const form = document.querySelector('form');
const $username = document.getElementById('username');
const $password = document.getElementById('password');
const $submit   = document.getElementById('submit');
const $msg      = document.getElementById('loginMsg');

function showMsg(text, cls = 'msg--info') {
  $msg.className = `msg ${cls}`;
  $msg.textContent = text;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!$username.value.trim() || !$password.value) {
    showMsg('Ingresa usuario y contraseña.', 'msg--error');
    return;
  }

  $submit.disabled = true;
  showMsg('Validando credenciales...', 'msg--info');

  try {
    const formData = new URLSearchParams();
    formData.append('username', $username.value.trim());
    formData.append('password', $password.value);

    const res = await fetch('http://127.0.0.1:8000/auth/login', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: formData.toString()
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      let errorMessage = 'Credenciales inválidas. Verifica tu usuario y contraseña.';
      
      if (err.detail) {
        if (Array.isArray(err.detail) && err.detail.length > 0) {
          errorMessage = err.detail[0].msg;
        } else if (typeof err.detail === 'string') {
          errorMessage = err.detail;
        }
      }

      showMsg(errorMessage, 'msg--error');
      return;
    }

    const data = await res.json();
    localStorage.setItem('token', data.access_token);
    showMsg('¡Ingreso exitoso! Redirigiendo...', 'msg--ok');
    setTimeout(() => { window.location.href = 'dashboard.html'; }, 700);
  } catch (err) {
    showMsg('Error de conexión con el servidor.', 'msg--error');
  } finally {
    $submit.disabled = false;
  }
});
