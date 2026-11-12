// Zaga shop: category tabs, colour swatches on every card, quick view with size + WhatsApp order.
// Product data lives in js/products.js (window.ZAGA_PRODUCTS).
(function () {
  const products = window.ZAGA_PRODUCTS || [];
  const tabsEl = document.getElementById('shop-tabs');
  const gridEl = document.getElementById('shop-grid');
  const countEl = document.getElementById('shop-count');
  if (!tabsEl || !gridEl || !products.length) return;

  const CATEGORY_ORDER = ['T-Shirts', 'Sleeveless', 'Long Sleeves', 'Polos', 'Hoodies', 'Trousers', 'Shorts', 'Socks', 'Headwear', 'Bags'];
  const ONE_SIZE = ['Socks', 'Headwear', 'Bags'];
  const SIZES = ['S', 'M', 'L', 'XL', 'XXL'];
  const categories = ['All'].concat(CATEGORY_ORDER.filter((c) => products.some((p) => p.category === c)));
  const chosen = {}; // product id -> colour key
  products.forEach((p) => { chosen[p.id] = p.defaultColour; });
  let activeCat = 'All';

  const colourOf = (p, key) => p.colours.find((c) => c.key === key) || p.colours[0];
  const el = (tag, attrs, children) => {
    const n = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (k === 'text') n.textContent = v;
      else if (k === 'style') n.style.cssText = v;
      else if (k.startsWith('on')) n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v);
    });
    (children || []).forEach((c) => c && n.appendChild(c));
    return n;
  };

  // ---- Swatches (shared by cards and quick view) ----
  function swatchRow(p, onPick, large) {
    const row = el('div', { class: 'swatches' + (large ? ' swatches-lg' : ''), role: 'radiogroup', 'aria-label': p.name + ' colour' });
    p.colours.forEach((c) => {
      const on = c.key === chosen[p.id];
      row.appendChild(el('button', {
        type: 'button', class: 'swatch', role: 'radio', 'aria-checked': String(on),
        'aria-label': c.label + (c.photo ? '' : ' (preview)'), title: c.label,
        style: '--sw:' + c.hex, 'data-key': c.key,
        onclick: () => onPick(c.key),
        onmouseenter: () => { const img = new Image(); img.src = c.img; },
      }));
    });
    return row;
  }
  function syncSwatches(row, key) {
    row.querySelectorAll('.swatch').forEach((b) => b.setAttribute('aria-checked', String(b.dataset.key === key)));
  }

  // ---- Tabs ----
  categories.forEach((cat) => {
    tabsEl.appendChild(el('button', {
      type: 'button', class: 'filter-btn', 'aria-pressed': String(cat === activeCat), 'data-cat': cat, text: cat,
      onclick: () => {
        activeCat = cat;
        tabsEl.querySelectorAll('.filter-btn').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.cat === cat)));
        renderGrid();
      },
    }));
  });

  // ---- Grid ----
  function card(p) {
    const c = colourOf(p, chosen[p.id]);
    const img = el('img', { src: c.img, alt: p.name + ' in ' + c.label, loading: 'lazy', width: '800', height: '800' });
    const badge = el('span', { class: 'card-badge', text: 'Preview' });
    badge.hidden = c.photo;
    const label = el('span', { class: 'card-colour', text: c.label });
    let row;
    const pick = (key) => {
      chosen[p.id] = key;
      const nc = colourOf(p, key);
      img.src = nc.img; img.alt = p.name + ' in ' + nc.label;
      label.textContent = nc.label; badge.hidden = nc.photo;
      syncSwatches(row, key);
    };
    row = swatchRow(p, pick);
    return el('article', { class: 'card' }, [
      el('button', { type: 'button', class: 'card-media', 'aria-label': 'View ' + p.name, onclick: () => openQuickView(p) }, [img, badge]),
      el('p', { class: 'card-cat', text: p.category }),
      el('div', { class: 'card-head' }, [
        el('h3', { class: 'card-name', text: p.name }),
        el('span', { class: 'card-price', text: '[PRICE]' }),
      ]),
      el('p', { class: 'card-detail', text: p.detail }),
      el('div', { class: 'card-colours' }, [row, label]),
      el('button', { type: 'button', class: 'card-cta', text: 'Choose size & order', onclick: () => openQuickView(p) }),
    ]);
  }
  function renderGrid() {
    gridEl.replaceChildren();
    const list = products.filter((p) => activeCat === 'All' || p.category === activeCat);
    list
      .slice()
      .sort((a, b) => CATEGORY_ORDER.indexOf(a.category) - CATEGORY_ORDER.indexOf(b.category))
      .forEach((p) => gridEl.appendChild(card(p)));
    countEl.textContent = list.length + (list.length === 1 ? ' piece' : ' pieces') + ' · 10 colours each';
  }

  // ---- Quick view ----
  const dlg = document.getElementById('quick-view');
  const q = (id) => document.getElementById(id);
  let current = null;
  let size = null;

  function updateQuickView() {
    const p = current;
    const c = colourOf(p, chosen[p.id]);
    q('qv-img').src = c.img;
    q('qv-img').alt = p.name + ' in ' + c.label;
    q('qv-badge').hidden = c.photo;
    q('qv-colour').textContent = c.label + (c.photo ? '' : ' (preview)');
    syncSwatches(q('qv-swatches'), c.key);
    q('qv-sizes').querySelectorAll('.size').forEach((b) => b.setAttribute('aria-checked', String(b.dataset.size === size)));
    const number = (window.ZAGA_CONFIG && window.ZAGA_CONFIG.whatsapp) || '';
    const msg = 'Hi Zaga, I\'d like to order the ' + p.name + ' in ' + c.label + ', size ' + (size || '?') + '.';
    const order = q('qv-order');
    order.href = number ? 'https://wa.me/' + number + '?text=' + encodeURIComponent(msg) : '#contact';
    order.target = number ? '_blank' : '';
    order.rel = number ? 'noopener' : '';
    order.dataset.msg = msg;
    order.classList.toggle('is-disabled', !size);
    order.setAttribute('aria-disabled', String(!size));
  }

  function openQuickView(p) {
    current = p;
    const oneSize = ONE_SIZE.includes(p.category);
    size = oneSize ? 'One size' : null;
    q('qv-cat').textContent = p.category;
    q('qv-name').textContent = p.name;
    q('qv-detail').textContent = p.detail;
    const sw = swatchRow(p, (key) => {
      chosen[p.id] = key;
      updateQuickView();
      renderGrid(); // keep the card in step with the quick view
    }, true);
    sw.id = 'qv-swatches';
    q('qv-swatches').replaceWith(sw);
    const sizesEl = q('qv-sizes');
    sizesEl.replaceChildren();
    (oneSize ? ['One size'] : SIZES).forEach((s) => {
      sizesEl.appendChild(el('button', {
        type: 'button', class: 'size', role: 'radio', 'aria-checked': String(s === size), 'data-size': s, text: s,
        onclick: () => { size = s; updateQuickView(); },
      }));
    });
    updateQuickView();
    if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.setAttribute('open', '');
  }

  function closeQuickView() {
    if (typeof dlg.close === 'function') dlg.close(); else dlg.removeAttribute('open');
  }

  q('qv-close').addEventListener('click', closeQuickView);
  dlg.addEventListener('click', (e) => { if (e.target === dlg) closeQuickView(); });

  q('qv-order').addEventListener('click', (e) => {
    const order = e.currentTarget;
    if (!size) {
      e.preventDefault();
      q('qv-sizes').classList.add('needs-size');
      setTimeout(() => q('qv-sizes').classList.remove('needs-size'), 900);
      return;
    }
    if (order.getAttribute('href') === '#contact') {
      // No WhatsApp number set yet: hand the order to the contact form instead.
      e.preventDefault();
      closeQuickView();
      const details = document.querySelector('#contact-form textarea[name="details"]');
      const need = document.querySelector('#contact-form select[name="need"]');
      if (details) details.value = order.dataset.msg;
      if (need) need.selectedIndex = 0;
      document.getElementById('contact').scrollIntoView({ behavior: 'smooth' });
    }
  });
  q('qv-custom').addEventListener('click', closeQuickView);

  renderGrid();
})();
