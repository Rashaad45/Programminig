(function () {
  'use strict';

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const lerp = (a, b, t) => a + (b - a) * t;
  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const rupee = (n) => '₹' + n.toLocaleString('en-IN');
  const fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const FREE_SHIP = 2499;

  const PRODUCTS = window.PRODUCTS || [];
  const byId = Object.fromEntries(PRODUCTS.map((p) => [p.id, p]));

  /* ------------------------------------------------------------------ Loader */
  (function loader() {
    const count = $('.loader__count');
    const start = performance.now();
    const dur = reduced ? 200 : 1500;
    function tick(now) {
      const t = clamp((now - start) / dur, 0, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      count.textContent = String(Math.round(eased * 100)).padStart(3, '0');
      if (t < 1) requestAnimationFrame(tick);
      else setTimeout(done, 250);
    }
    function done() {
      document.body.classList.add('is-ready');
      document.body.classList.remove('is-loading');
      setTimeout(() => $('.loader').remove(), 1200);
    }
    requestAnimationFrame(tick);
  })();

  /* ---------------------------------------------------------- Small details */
  $$('[data-year]').forEach((el) => (el.textContent = new Date().getFullYear()));

  (function clock() {
    const el = $('[data-clock]');
    const fmt = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' });
    const set = () => (el.textContent = fmt.format(new Date()));
    set();
    setInterval(set, 15000);
  })();

  Garment.render($('.hero__garment'), 'overshirt', '#c9a98a');

  /* ------------------------------------------------------------------ Cursor */
  const pointer = { x: innerWidth / 2, y: innerHeight / 2 };
  window.addEventListener('pointermove', (e) => { pointer.x = e.clientX; pointer.y = e.clientY; }, { passive: true });

  if (fine) {
    const cursor = $('.cursor');
    const label = $('.cursor__label');
    const pos = { x: pointer.x, y: pointer.y };
    (function loop() {
      pos.x = lerp(pos.x, pointer.x, 0.22);
      pos.y = lerp(pos.y, pointer.y, 0.22);
      cursor.style.transform = `translate3d(${pos.x}px, ${pos.y}px, 0)`;
      requestAnimationFrame(loop);
    })();

    document.addEventListener('pointerover', (e) => {
      const t = e.target.closest('[data-cursor], [data-hover], a, button, input');
      cursor.classList.remove('is-hover', 'is-label');
      if (!t) return;
      const text = t.getAttribute('data-cursor');
      if (text) { label.textContent = text; cursor.classList.add('is-label'); }
      else if (t.tagName === 'INPUT') cursor.classList.add('is-hidden');
      else cursor.classList.add('is-hover');
    });
    document.addEventListener('pointerout', (e) => {
      if (e.target.tagName === 'INPUT') cursor.classList.remove('is-hidden');
    });
    document.addEventListener('mouseleave', () => cursor.classList.add('is-hidden'));
    document.addEventListener('mouseenter', () => cursor.classList.remove('is-hidden'));
  }

  /* ------------------------------------------- Gradient blob follows pointer */
  (function aura() {
    const blob = $('.aura__blob--4');
    if (!blob || reduced) return;
    const p = { x: 0, y: 0 };
    (function loop() {
      p.x = lerp(p.x, (pointer.x / innerWidth - 0.5) * 40, 0.04);
      p.y = lerp(p.y, (pointer.y / innerHeight - 0.5) * 40, 0.04);
      blob.style.transform = `translate(${p.x}vw, ${p.y}vh)`;
      requestAnimationFrame(loop);
    })();
  })();

  /* --------------------------------------------------------------------- Nav */
  (function nav() {
    const bar = $('.nav');
    let last = scrollY;
    window.addEventListener('scroll', () => {
      const y = scrollY;
      bar.classList.toggle('is-scrolled', y > 40);
      const menuOpen = $('.mobile-menu').classList.contains('is-open');
      bar.classList.toggle('is-hidden', !menuOpen && y > last && y > 400);
      last = y;
    }, { passive: true });

    const burger = $('.nav__burger');
    const menu = $('.mobile-menu');
    const toggle = (open) => {
      burger.setAttribute('aria-expanded', open);
      menu.classList.toggle('is-open', open);
      menu.setAttribute('aria-hidden', !open);
      document.body.classList.toggle('is-locked', open);
    };
    burger.addEventListener('click', () => toggle(!menu.classList.contains('is-open')));
    $$('a', menu).forEach((a) => a.addEventListener('click', () => toggle(false)));
  })();

  /* ---------------------------------------------------------- Magnetic btns */
  if (fine) {
    $$('[data-magnetic]').forEach((el) => {
      el.addEventListener('pointermove', (e) => {
        const r = el.getBoundingClientRect();
        const x = e.clientX - r.left - r.width / 2;
        const y = e.clientY - r.top - r.height / 2;
        el.style.transform = `translate(${x * 0.25}px, ${y * 0.35}px)`;
      });
      el.addEventListener('pointerleave', () => (el.style.transform = ''));
    });
  }

  /* -------------------------------------------------------------- Hero tilt */
  (function tilt() {
    const stage = $('[data-tilt]');
    if (!stage || !fine || reduced) return;
    const front = $('.hero__card--front', stage);
    const back = $('.hero__card--back', stage);
    const hero = $('.hero');
    hero.addEventListener('pointermove', (e) => {
      const r = stage.getBoundingClientRect();
      const x = clamp((e.clientX - (r.left + r.width / 2)) / r.width, -1, 1);
      const y = clamp((e.clientY - (r.top + r.height / 2)) / r.height, -1, 1);
      front.style.setProperty('--rx', `${x * 10}deg`);
      front.style.setProperty('--ry', `${-y * 10}deg`);
      back.style.transform = `translate(${-7 - x * 3}%, ${6 - y * 3}%) rotate(${-5 - x * 2}deg)`;
    });
    hero.addEventListener('pointerleave', () => {
      front.style.setProperty('--rx', '0deg');
      front.style.setProperty('--ry', '0deg');
      back.style.transform = '';
    });
  })();

  /* --------------------------------------------------------------- Products */
  const grid = $('[data-grid]');

  function mediaHTML(p, color) {
    if (p.image) return `<img class="card__photo" src="${p.image}" alt="${p.name}" loading="lazy" />`;
    return `<div class="card__garment">${Garment.svg(p.garment, color.hex)}</div>`;
  }

  function tint(hex) {
    // A soft background derived from the garment colour, so the card never clashes.
    const n = parseInt(hex.slice(1), 16);
    const mix = (c) => Math.round(c + (246 - c) * 0.78);
    return `rgb(${mix(n >> 16)}, ${mix((n >> 8) & 255)}, ${mix(n & 255)})`;
  }

  function renderGrid() {
    grid.innerHTML = PRODUCTS.map((p) => {
      const c = p.colors[0];
      return `
      <article class="card" data-id="${p.id}" data-cat="${p.category}" data-reveal>
        <div class="card__media" style="--card-bg:${tint(c.hex)}" data-cursor="View" data-open-qv>
          ${p.tag ? `<span class="card__tag">${p.tag}</span>` : ''}
          <span class="card__fig">${p.fig}</span>
          ${mediaHTML(p, c)}
          <div class="card__quick">
            <span class="card__quick-label">Quick add</span>
            ${p.sizes.map((s) => `<button data-quick="${s}" ${p.soldOut.includes(s) ? 'disabled aria-label="' + s + ' sold out"' : ''}>${s}</button>`).join('')}
          </div>
        </div>
        <div class="card__info">
          <div>
            <h3 class="card__name">${p.name}</h3>
            <p class="card__fabric">${p.fabric}</p>
            <div class="card__swatches">
              ${p.colors.map((col, i) => `<button class="${i === 0 ? 'is-active' : ''}" style="--c:${col.hex}" data-color="${i}" aria-label="${col.name}" title="${col.name}"></button>`).join('')}
            </div>
          </div>
          <span class="card__price">${rupee(p.price)}</span>
        </div>
      </article>`;
    }).join('');
  }
  renderGrid();

  grid.addEventListener('click', (e) => {
    const card = e.target.closest('.card');
    if (!card) return;
    const p = byId[card.dataset.id];
    const activeIdx = +($('.card__swatches .is-active', card)?.dataset.color || 0);

    const sw = e.target.closest('[data-color]');
    if (sw) {
      const i = +sw.dataset.color;
      $$('.card__swatches button', card).forEach((b) => b.classList.toggle('is-active', b === sw));
      const media = $('.card__media', card);
      media.style.setProperty('--card-bg', tint(p.colors[i].hex));
      const g = $('.card__garment', card);
      if (g) g.innerHTML = Garment.svg(p.garment, p.colors[i].hex);
      return;
    }
    const quick = e.target.closest('[data-quick]');
    if (quick) {
      e.stopPropagation();
      Bag.add(p.id, activeIdx, quick.dataset.quick);
      return;
    }
    if (e.target.closest('[data-open-qv]')) QuickView.open(p.id, activeIdx);
  });

  /* ---------------------------------------------------------------- Filters */
  $$('[data-filter]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const f = btn.dataset.filter;
      $$('[data-filter]').forEach((b) => b.classList.toggle('is-active', b === btn));
      const cards = $$('.card', grid);
      cards.forEach((c) => c.classList.add('is-out'));
      setTimeout(() => {
        grid.classList.toggle('is-filtered', f !== 'all');
        cards.forEach((c) => {
          const show = f === 'all' || c.dataset.cat === f;
          c.style.display = show ? '' : 'none';
        });
        requestAnimationFrame(() => requestAnimationFrame(() => {
          cards.forEach((c) => c.classList.remove('is-out'));
        }));
      }, 380);
    });
  });

  /* ------------------------------------------------------------- Quick view */
  const QuickView = (function () {
    const root = $('.qv');
    const state = { id: null, color: 0, size: null };
    let lastFocus = null;

    function paint() {
      const p = byId[state.id];
      const c = p.colors[state.color];
      $('.qv__media', root).style.setProperty('--card-bg', tint(c.hex));
      $('.qv__garment', root).innerHTML = p.image
        ? `<img src="${p.image}" alt="${p.name}" />`
        : Garment.svg(p.garment, c.hex);
      $('.qv__colorname', root).textContent = c.name;
      $$('.qv__colors button', root).forEach((b, i) => b.classList.toggle('is-active', i === state.color));
      $$('.qv__sizes button', root).forEach((b) => b.classList.toggle('is-active', b.dataset.size === state.size));
      const add = $('.qv__add', root);
      $('span', add).textContent = state.size ? `Add to bag — ${rupee(p.price)}` : 'Select a size';
      add.disabled = !state.size;
    }

    function open(id, color = 0) {
      const p = byId[id];
      Object.assign(state, { id, color, size: null });
      $('.qv__fig', root).textContent = `${p.fig} · ${p.category}`;
      $('.qv__title', root).textContent = p.name;
      $('.qv__price', root).textContent = rupee(p.price);
      $('.qv__desc', root).textContent = p.desc;
      $('.qv__colors', root).innerHTML = p.colors.map((c, i) => `<button style="--c:${c.hex}" data-c="${i}" aria-label="${c.name}" data-hover></button>`).join('');
      $('.qv__sizes', root).innerHTML = p.sizes.map((s) => `<button data-size="${s}" ${p.soldOut.includes(s) ? 'disabled' : ''} data-hover>${s}</button>`).join('');
      $('.qv__specs', root).innerHTML = [p.fabric, 'Pre-washed, will not shrink', 'Free alterations within 30 days', 'Stitched in Tiruppur'].map((s) => `<li>${s}</li>`).join('');
      paint();
      lastFocus = document.activeElement;
      root.classList.add('is-open');
      root.setAttribute('aria-hidden', 'false');
      document.body.classList.add('is-locked');
      setTimeout(() => $('.qv__close', root).focus(), 50);
    }

    function close() {
      root.classList.remove('is-open');
      root.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('is-locked');
      if (lastFocus) lastFocus.focus({ preventScroll: true });
    }

    root.addEventListener('click', (e) => {
      if (e.target.closest('[data-close-qv]')) return close();
      const c = e.target.closest('[data-c]');
      if (c) { state.color = +c.dataset.c; return paint(); }
      const s = e.target.closest('[data-size]');
      if (s) { state.size = s.dataset.size; return paint(); }
      if (e.target.closest('.qv__add') && state.size) {
        Bag.add(state.id, state.color, state.size);
        close();
      }
    });

    return { open, close, isOpen: () => root.classList.contains('is-open') };
  })();

  /* -------------------------------------------------------------------- Bag */
  const Bag = (function () {
    const root = $('.bag');
    let items = [];
    try { items = JSON.parse(localStorage.getItem('kora-bag') || '[]').filter((i) => byId[i.id]); } catch (_) { items = []; }

    const save = () => { try { localStorage.setItem('kora-bag', JSON.stringify(items)); } catch (_) {} };
    const count = () => items.reduce((n, i) => n + i.qty, 0);
    const total = () => items.reduce((n, i) => n + byId[i.id].price * i.qty, 0);

    function render() {
      const n = count();
      $$('.nav__count, .bag__count').forEach((el) => (el.textContent = n));
      root.classList.toggle('is-empty', n === 0);
      $('.bag__items', root).innerHTML = items.map((it, idx) => {
        const p = byId[it.id];
        const c = p.colors[it.color];
        return `<li class="bag__item">
          <div class="bag__thumb" style="background:${tint(c.hex)}"><div>${Garment.svg(p.garment, c.hex)}</div></div>
          <div>
            <h4>${p.name}</h4>
            <p>${c.name} · ${it.size}</p>
            <div class="bag__qty">
              <button data-dec="${idx}" aria-label="Decrease">−</button>
              <span>${it.qty}</span>
              <button data-inc="${idx}" aria-label="Increase">+</button>
            </div>
          </div>
          <div class="bag__price">${rupee(p.price * it.qty)}<button class="bag__remove" data-rm="${idx}">Remove</button></div>
        </li>`;
      }).join('');
      const t = total();
      $('.bag__total', root).textContent = rupee(t);
      const left = FREE_SHIP - t;
      $('.bag__ship-text', root).textContent = left > 0 ? `Add ${rupee(left)} more for free shipping` : 'You’ve unlocked free shipping ✺';
      $('.bag__ship-bar i', root).style.width = `${clamp((t / FREE_SHIP) * 100, 0, 100)}%`;
    }

    function add(id, color, size) {
      const found = items.find((i) => i.id === id && i.color === color && i.size === size);
      if (found) found.qty++;
      else items.push({ id, color, size, qty: 1 });
      save();
      render();
      const badge = $('.nav__count');
      badge.classList.add('is-bump');
      setTimeout(() => badge.classList.remove('is-bump'), 300);
      toast(`${byId[id].name} · ${size} — added`);
    }

    function open() {
      root.classList.add('is-open');
      root.setAttribute('aria-hidden', 'false');
      document.body.classList.add('is-locked');
    }
    function close() {
      root.classList.remove('is-open');
      root.setAttribute('aria-hidden', 'true');
      document.body.classList.remove('is-locked');
    }

    root.addEventListener('click', (e) => {
      const t = e.target;
      if (t.closest('[data-close-bag]')) return close();
      if (t.dataset.inc) items[+t.dataset.inc].qty++;
      else if (t.dataset.dec) {
        const it = items[+t.dataset.dec];
        it.qty--;
        if (it.qty <= 0) items.splice(+t.dataset.dec, 1);
      } else if (t.dataset.rm) items.splice(+t.dataset.rm, 1);
      else return;
      save();
      render();
    });
    $$('[data-open-bag]').forEach((b) => b.addEventListener('click', open));

    render();
    return { add, open, close, isOpen: () => root.classList.contains('is-open') };
  })();

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (QuickView.isOpen()) QuickView.close();
    if (Bag.isOpen()) Bag.close();
  });

  let toastTimer;
  function toast(msg) {
    const el = $('.toast');
    el.textContent = msg;
    el.classList.add('is-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('is-on'), 2200);
  }

  /* ----------------------------------------------------------- Lookbook rail */
  const railTrack = $('[data-rail]');
  railTrack.innerHTML = (window.LOOKS || []).map((l, i) => `
    <article class="look" data-cursor="Shop">
      <div class="look__frame" style="--bg:${l.bg}">
        <span class="look__day">${l.day}</span>
        <span class="look__num">${String(i + 1).padStart(2, '0')} / ${String(window.LOOKS.length).padStart(2, '0')}</span>
        <div class="look__garment" style="--r:${i % 2 ? 4 : -4}deg">${Garment.svg(l.garment, l.color)}</div>
      </div>
      <div class="look__cap"><h3>${l.title}</h3><p>${l.note}</p></div>
    </article>`).join('');
  $$('.look', railTrack).forEach((el) => el.addEventListener('click', () => $('#shop').scrollIntoView({ behavior: 'smooth' })));

  const rail = $('.rail');
  const railBar = $('.rail__progress i');
  const railIntro = $('.rail__intro');
  let railX = 0;

  /* ------------------------------------------------- Manifesto word scrub */
  const scrub = $('[data-scrub]');
  scrub.innerHTML = scrub.textContent.trim().split(/\s+/).map((w) => `<span class="w">${w}</span>`).join(' ');
  const words = $$('.w', scrub);

  /* ------------------------------------------------------- Marquee velocity */
  const marquee = $('[data-marquee]');
  let mqX = 0, mqSpeed = 1, lastY = scrollY;

  /* ---------------------------------------------------------- Frame loop */
  (function frame() {
    const vh = innerHeight;

    // Marquee: drifts on its own, speeds up and reverses with scroll direction.
    const dy = scrollY - lastY;
    lastY = scrollY;
    const target = reduced ? 0 : (dy >= 0 ? 1 : -1) * (1 + Math.min(Math.abs(dy), 60) * 0.25);
    mqSpeed = lerp(mqSpeed, target, 0.08);
    mqX -= mqSpeed;
    const half = marquee.scrollWidth / 2;
    if (half) { if (mqX <= -half) mqX += half; if (mqX > 0) mqX -= half; }
    marquee.style.transform = `translate3d(${mqX}px,0,0)`;

    // Manifesto: words light up as the paragraph passes the middle of the screen.
    const sr = scrub.getBoundingClientRect();
    const sp = clamp((vh * 0.78 - sr.top) / (sr.height + vh * 0.3), 0, 1);
    const on = Math.floor(sp * words.length);
    for (let i = 0; i < words.length; i++) words[i].classList.toggle('is-on', i < on);

    // Rail: vertical scroll drives horizontal travel.
    if (innerWidth > 760) {
      const rr = rail.getBoundingClientRect();
      const travel = railTrack.offsetLeft + railTrack.offsetWidth - innerWidth;
      const p = clamp(-rr.top / (rr.height - vh), 0, 1);
      railX = lerp(railX, p * Math.max(travel, 0), 0.12);
      const tf = `translate3d(${-railX}px,0,0)`;
      railIntro.style.transform = tf;
      railTrack.style.transform = tf;
      railBar.style.setProperty('--p', p);
    } else if (railX) {
      railX = 0;
      railIntro.style.transform = railTrack.style.transform = '';
    }

    requestAnimationFrame(frame);
  })();

  /* ------------------------------------------------------------ Count up */
  const counters = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (!en.isIntersecting) return;
      const el = en.target;
      const end = +el.dataset.count;
      const t0 = performance.now();
      const run = (now) => {
        const t = clamp((now - t0) / 1600, 0, 1);
        el.textContent = Math.round(end * (1 - Math.pow(1 - t, 4)));
        if (t < 1) requestAnimationFrame(run);
      };
      requestAnimationFrame(run);
      counters.unobserve(el);
    });
  }, { threshold: 0.6 });
  $$('[data-count]').forEach((el) => counters.observe(el));

  /* ------------------------------------------------------------ Reveal */
  $$('.display, .swatch, .people li, .manifesto__stats div, .journal__card').forEach((el) => el.setAttribute('data-reveal', ''));
  const reveal = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting) { en.target.classList.add('is-in'); reveal.unobserve(en.target); }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  $$('[data-reveal]').forEach((el, i) => {
    el.style.transitionDelay = `${(i % 3) * 80}ms`;
    reveal.observe(el);
  });

  /* ------------------------------------------------ Fabric: light follows */
  $$('.swatch').forEach((s) => {
    const weave = $('.swatch__weave', s);
    s.addEventListener('pointermove', (e) => {
      const r = weave.getBoundingClientRect();
      weave.style.setProperty('--mx', `${e.clientX - r.left}px`);
      weave.style.setProperty('--my', `${e.clientY - r.top}px`);
    });
  });

  /* ---------------------------------------------- People: floating preview */
  (function people() {
    const float = $('.people__float');
    const inner = $('div', float);
    if (!fine) return;
    const p = { x: 0, y: 0 };
    let active = false;
    $$('[data-people] li').forEach((li) => {
      li.addEventListener('pointerenter', () => {
        active = true;
        float.style.backgroundColor = tint(li.dataset.color);
        inner.innerHTML = Garment.svg(li.dataset.garment, li.dataset.color);
        float.classList.add('is-on');
      });
      li.addEventListener('pointerleave', () => { active = false; float.classList.remove('is-on'); });
    });
    (function loop() {
      p.x = lerp(p.x, pointer.x + 150, 0.12);
      p.y = lerp(p.y, pointer.y, 0.12);
      const rot = clamp((pointer.x + 150 - p.x) * 0.05, -8, 8);
      float.style.transform = `translate(${p.x}px, ${p.y}px) translate(-50%, -50%) rotate(${rot}deg) scale(${active ? 1 : 0.8})`;
      requestAnimationFrame(loop);
    })();
  })();

  /* -------------------------------------------------------------- Signup */
  $('.signup').addEventListener('submit', (e) => {
    e.preventDefault();
    const input = $('#email');
    const msg = $('.signup__msg');
    const ok = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(input.value.trim());
    if (!ok) { msg.textContent = 'That email doesn’t look quite right.'; input.focus(); return; }
    msg.textContent = 'You’re on the list. See you at the next drop.';
    input.value = '';
  });
})();
