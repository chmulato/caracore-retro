/**
 * Sala de Notícias — Login (caracore-mkt)
 * Envia usuário e senha para /api/login; em sucesso, redireciona para a sala.
 */
(function () {
  var form = document.getElementById('form-login');
  var msg = document.getElementById('login-msg');
  var btn = document.getElementById('btn-login');

  if (!form) return;

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var user = document.getElementById('user').value.trim();
    var password = document.getElementById('password').value;

    if (!user || !password) {
      msg.textContent = 'Preencha usuário e senha.';
      msg.className = 'sala-msg err';
      return;
    }

    msg.textContent = '';
    msg.className = 'sala-msg';
    btn.disabled = true;

    fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user: user, password: password }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (res.ok && data.ok) {
            msg.textContent = 'Entrando…';
            msg.className = 'sala-msg ok';
            window.location.href = '/index.htm';
          } else {
            msg.textContent = data.error || 'Usuário ou senha incorretos.';
            msg.className = 'sala-msg err';
            btn.disabled = false;
          }
        });
      })
      .catch(function () {
        msg.textContent = 'Erro de conexão. Tente de novo.';
        msg.className = 'sala-msg err';
        btn.disabled = false;
      });
  });
})();
