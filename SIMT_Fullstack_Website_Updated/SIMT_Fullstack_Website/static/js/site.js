(() => {
  const menuButton = document.querySelector('.menu-toggle');
  const menuPanel = document.getElementById('site-menu');
  if (menuButton && menuPanel) {
    const toggle = (open) => {
      menuPanel.hidden = !open;
      menuButton.setAttribute('aria-expanded', String(open));
      menuButton.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
      document.body.classList.toggle('menu-open', open);
      if (open) menuPanel.querySelector('a')?.focus();
    };
    menuButton.addEventListener('click', () => toggle(menuPanel.hidden));
    menuPanel.querySelectorAll('a').forEach(a => a.addEventListener('click', () => toggle(false)));
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && !menuPanel.hidden) { toggle(false); menuButton.focus(); }
    });
  }

  if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    document.documentElement.classList.add('js-motion');
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      }
    }, { threshold: 0.06, rootMargin: '0px 0px 60px 0px' });
    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
  }

  const form = document.querySelector('#inquiry-form');
  if (!form) return;

  const params = new URLSearchParams(window.location.search);
  const tabs = [...document.querySelectorAll('.form-tabs .tab')];
  const kindField = document.getElementById('kind');
  const service = document.getElementById('contact-service');
  const audience = document.getElementById('contact-audience');
  const dateField = document.getElementById('preferred-date');
  const status = document.getElementById('form-status');
  const submitButton = document.getElementById('submit-inquiry');
  let sending = false;

  const setKind = kind => {
    const safeKind = kind === 'consultation' ? 'consultation' : 'inquiry';
    kindField.value = safeKind;
    tabs.forEach(tab => {
      const active = tab.dataset.kind === safeKind;
      tab.classList.toggle('active', active);
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    const shown = safeKind === 'consultation';
    document.querySelectorAll('.only-consultation').forEach(x => { x.hidden = !shown; });
    const panel = document.getElementById('panel-inquiry');
    panel?.setAttribute('aria-labelledby', shown ? 'tab-consultation' : 'tab-inquiry');
    submitButton.innerHTML = shown ? 'REQUEST A CONSULTATION <span>↗</span>' : 'SEND INQUIRY <span>↗</span>';
    if (status) { status.textContent = ''; status.classList.remove('error'); }
  };
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => setKind(tab.dataset.kind));
    tab.addEventListener('keydown', event => {
      if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
      event.preventDefault();
      const next = tabs[(index + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
      setKind(next.dataset.kind);
      next.focus();
    });
  });
  setKind(params.get('tab'));

  if (params.has('service')) {
    const candidate = params.get('service');
    if ([...service.options].some(o => o.value === candidate)) service.value = candidate;
  }
  if (params.has('audience')) {
    const candidate = params.get('audience');
    if ([...audience.options].some(o => o.value === candidate)) audience.value = candidate;
  }
  if (dateField) {
    const local = new Date();
    const yyyy = local.getFullYear();
    const mm = String(local.getMonth() + 1).padStart(2, '0');
    const dd = String(local.getDate()).padStart(2, '0');
    dateField.min = `${yyyy}-${mm}-${dd}`;
  }
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (sending) return;
    status.textContent = '';
    status.classList.remove('error');
    if (!form.reportValidity()) return;
    sending = true;
    submitButton.disabled = true;
    const former = submitButton.innerHTML;
    submitButton.textContent = 'SENDING…';
    const data = Object.fromEntries(new FormData(form).entries());
    try {
      const response = await fetch('/api/inquiries', {
        method: 'POST',
        headers: { 'Content-Type':'application/json', 'Accept':'application/json' },
        body: JSON.stringify(data)
      });
      const result = await response.json();
      if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Unable to submit this request. Please try again.');
      status.textContent = `Thank you. Your ${kindField.value === 'consultation' ? 'consultation request' : 'inquiry'} is recorded. Reference: ${result.reference}. This is not an appointment confirmation; SIMT will contact you by email.`;
      form.reset();
    } catch (error) {
      status.classList.add('error');
      status.textContent = `${error.message} If needed, email simt.consultancy007@gmail.com directly.`;
    } finally {
      sending = false;
      submitButton.disabled = false;
      submitButton.innerHTML = former;
      status.focus();
    }
  });
})();