
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
    const res = await fetch('http://127.0.0.1:8000/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: $username.value.trim(), password: $password.value })
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showMsg(err.detail || 'Credenciales inválidas', 'msg--error');
      return;
    }

    const data = await res.json();
    localStorage.setItem('token', data.access_token);
    showMsg('¡Ingreso exitoso! Redirigiendo...', 'msg--ok');
    setTimeout(() => { window.location.href = 'dashboard.html'; }, 700);
  } catch (err) {
    showMsg('No se pudo conectar con el servidor.', 'msg--error');
  } finally {
    $submit.disabled = false;
  }
});
