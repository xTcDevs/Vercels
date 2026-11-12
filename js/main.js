// Zaga — contact form.
(function () {
  // ---- Contact form ----
  // Default: opens WhatsApp with the message pre-filled (number set in js/config.js).
  // On Netlify you can instead use Netlify Forms: add data-netlify="true" to the <form>
  // and set USE_NETLIFY_FORMS = true.
  const WHATSAPP_NUMBER = (window.ZAGA_CONFIG && window.ZAGA_CONFIG.whatsapp) || '';
  const USE_NETLIFY_FORMS = false;

  const form = document.getElementById('contact-form');
  const sent = document.getElementById('contact-sent');
  const reset = document.getElementById('contact-reset');
  if (!form || !sent) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = new FormData(form);

    if (USE_NETLIFY_FORMS) {
      try {
        const res = await fetch('/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams(data).toString(),
        });
        if (!res.ok) throw new Error('HTTP ' + res.status);
      } catch (err) {
        alert('Sorry, the message could not be sent. Please reach us on WhatsApp or Instagram.');
        return;
      }
    } else if (WHATSAPP_NUMBER) {
      const text =
        'Hi Zaga, I\'m ' + data.get('name') + ' (' + data.get('phone') + ').\n' +
        'I need: ' + data.get('need') + '\n' + (data.get('details') || '');
      window.open('https://wa.me/' + WHATSAPP_NUMBER + '?text=' + encodeURIComponent(text), '_blank', 'noopener');
    }

    form.hidden = true;
    sent.hidden = false;
  });

  if (reset) {
    reset.addEventListener('click', () => {
      form.reset();
      sent.hidden = true;
      form.hidden = false;
    });
  }
})();
