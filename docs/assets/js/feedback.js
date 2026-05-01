(function(){
  var consent = document.getElementById('feedback-consent');
  var channels = document.getElementById('feedback-channels');
  var form = document.getElementById('form-feedback');
  var msg = document.getElementById('feedback-msg');

  function syncConsent(){
    if(!consent || !channels) return;
    channels.hidden = !consent.checked;
  }

  if(consent){
    consent.addEventListener('change', syncConsent);
    syncConsent();
  }

  document.querySelectorAll('[data-channel]').forEach(function(btn){
    btn.addEventListener('click', function(){
      var ch = btn.getAttribute('data-channel');
      if(ch === 'whatsapp') window.open('https://wa.me/5511999999999', '_blank');
      else if(ch === 'telegram') window.open('https://t.me/caracore', '_blank');
      else if(ch === 'email') window.location.href = 'mailto:contato@caracore.com.br?subject=Feedback%20Sala';
    });
  });

  if(form){
    form.addEventListener('submit', function(ev){
      ev.preventDefault();
      if(msg){ msg.textContent = 'Feedback registrado localmente. Use também um canal acima para envio oficial.'; }
      form.reset();
      syncConsent();
    });
  }
})();