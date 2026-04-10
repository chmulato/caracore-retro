/**
 * Sala de Operações — Canais de feedback (Privacy by Design)
 * - Camada de consentimento antes de exibir canais
 * - Contatos ofuscados em JS (nunca no HTML) para evitar scrapers
 * - Sem cookies; uso de sessionStorage apenas para estado de consentimento na sessão
 */
(function () {
  'use strict';

  var CONSENT_KEY = 'sala_feedback_consent';

  function getConsentFromStorage() {
    try {
      return sessionStorage.getItem(CONSENT_KEY) === '1';
    } catch (e) {
      return false;
    }
  }

  function setConsentInStorage(ok) {
    try {
      if (ok) sessionStorage.setItem(CONSENT_KEY, '1');
      else sessionStorage.removeItem(CONSENT_KEY);
    } catch (e) {}
  }

  /* Ofuscação: contatos nunca no HTML. Decodificação apenas no clique. */
  function decodeContact(encoded) {
    try {
      return decodeURIComponent(escape(atob(encoded)));
    } catch (e) {
      return '';
    }
  }

  /* Dados de contato em base64 (substitua pelos valores reais em produção).
   * Ex.: btoa('5511999999999') para WhatsApp, btoa('usuario') para Telegram, btoa('email@dominio.com') para e-mail. */
  var CONTACTS = {
    whatsapp: decodeContact('NTUxMTk5OTk5OTk5OQ=='),   /* placeholder: 5511999999999 */
    telegram: decodeContact('Y2FyYWNvcmU='),           /* placeholder: caracore */
    email: decodeContact('c3Vwb3J0ZUBjYXJhY29yZS5jb20uYnI=')  /* suporte@caracore.com.br */
  };

  function openWhatsApp() {
    var n = CONTACTS.whatsapp.replace(/\D/g, '');
    if (n) window.open('https://wa.me/' + n, '_blank', 'noopener,noreferrer');
  }

  function openTelegram() {
    var u = CONTACTS.telegram.replace(/^@/, '');
    if (u) window.open('https://t.me/' + u, '_blank', 'noopener,noreferrer');
  }

  function openEmail() {
    var e = CONTACTS.email;
    if (e) window.location.href = 'mailto:' + e;
  }

  function openChannel(channel) {
    if (channel === 'whatsapp') openWhatsApp();
    else if (channel === 'telegram') openTelegram();
    else if (channel === 'email') openEmail();
  }

  /* Consentimento: exibir canais só após checkbox */
  var consentCheckbox = document.getElementById('feedback-consent');
  var channelsSection = document.getElementById('feedback-channels');

  if (consentCheckbox && channelsSection) {
    if (getConsentFromStorage()) {
      consentCheckbox.checked = true;
      channelsSection.hidden = false;
    }

    consentCheckbox.addEventListener('change', function () {
      var checked = consentCheckbox.checked;
      setConsentInStorage(checked);
      channelsSection.hidden = !checked;
    });
  }

  /* Botões de canal: abrir link via JS (contato não está no HTML) */
  var channelBtns = document.querySelectorAll('.feedback-channel-card__btn[data-channel]');
  channelBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      openChannel(btn.getAttribute('data-channel'));
    });
  });

  /* Formulário de feedback (envio para /api/feedback) */
  var form = document.getElementById('form-feedback');
  var msg = document.getElementById('feedback-msg');

  if (!form) return;

  var today = new Date().toISOString().slice(0, 10);
  var dataEl = document.getElementById('data');
  if (dataEl) dataEl.value = today;

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var payload = {
      data: document.getElementById('data').value,
      resumo: document.getElementById('resumo').value.trim(),
      horas: document.getElementById('horas').value.trim(),
      observacoes: document.getElementById('observacoes').value.trim(),
    };

    if (!payload.resumo) {
      msg.textContent = 'Preencha o resumo do trabalho feito.';
      msg.className = 'sala-msg err';
      return;
    }

    msg.textContent = 'Enviando…';
    msg.className = 'sala-msg';

    fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      credentials: 'same-origin',
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (res.ok && data.ok) {
            msg.textContent = 'Feedback registrado. Obrigado.';
            msg.className = 'sala-msg ok';
            form.reset();
            if (dataEl) dataEl.value = today;
          } else {
            msg.textContent = data.error || 'Erro ao enviar. Faça login novamente.';
            msg.className = 'sala-msg err';
          }
        });
      })
      .catch(function () {
        msg.textContent = 'Erro de conexão. Tente de novo.';
        msg.className = 'sala-msg err';
      });
  });
})();
