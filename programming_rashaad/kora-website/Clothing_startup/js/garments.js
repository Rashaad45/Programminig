/*
 * Technical flat sketches — the kind a pattern-maker hands to a factory.
 * Each garment is drawn in a 200 x 240 box and filled with the chosen colour.
 * When you have real photography, set `image` on a product in products.js
 * and the photo is used instead.
 */
(function () {
  const stitch = 'fill="none" stroke="var(--g-line)" stroke-width="0.9" stroke-dasharray="2.5 2.5"';
  const line = 'fill="none" stroke="var(--g-line)" stroke-width="1.1" stroke-linejoin="round" stroke-linecap="round"';
  const body = 'fill="var(--g-fill)" stroke="var(--g-line)" stroke-width="1.3" stroke-linejoin="round"';
  const shade = 'fill="var(--g-shade)"';

  const shapes = {
    tee: `
      <path ${body} d="M62 32 L86 22 Q100 36 114 22 L138 32 L176 62 L158 88 L142 76 L143 214 Q100 220 57 214 L58 76 L42 88 L24 62 Z"/>
      <path ${shade} d="M58 76 L42 88 L24 62 L36 52 Z"/>
      <path ${shade} d="M142 76 L143 214 Q128 216 118 216 Q132 150 142 76 Z" opacity=".6"/>
      <path ${line} d="M86 22 Q100 44 114 22"/>
      <path ${stitch} d="M89 25 Q100 40 111 25"/>
      <path ${stitch} d="M60 205 Q100 211 140 205"/>
      <path ${stitch} d="M28 67 L45 82 M172 67 L155 82"/>
      <path ${line} d="M58 76 L62 40 M142 76 L138 40" opacity=".35"/>`,

    overshirt: `
      <path ${body} d="M64 34 L85 24 L100 38 L115 24 L136 34 L166 50 L182 152 L160 156 L150 84 L148 216 L52 216 L50 84 L40 156 L18 152 L34 50 Z"/>
      <path ${shade} d="M50 84 L40 156 L18 152 L34 50 L50 60 Z" opacity=".7"/>
      <path ${shade} d="M150 84 L148 216 L128 216 Q142 150 150 84 Z" opacity=".5"/>
      <path ${body} d="M85 24 L93 52 L100 38 Z M115 24 L107 52 L100 38 Z"/>
      <path ${line} d="M100 38 L100 216"/>
      <path ${stitch} d="M104 40 L104 216"/>
      <g fill="var(--g-line)"><circle cx="100" cy="62" r="2.2"/><circle cx="100" cy="94" r="2.2"/><circle cx="100" cy="126" r="2.2"/><circle cx="100" cy="158" r="2.2"/><circle cx="100" cy="190" r="2.2"/></g>
      <path ${line} d="M62 72 H88 V100 Q75 106 62 100 Z M112 72 H138 V100 Q125 106 112 100 Z"/>
      <path ${line} d="M60 66 H90 M110 66 H140"/>
      <path ${stitch} d="M54 208 H146 M20 146 L40 149 M180 146 L160 149"/>`,

    trouser: `
      <path ${body} d="M60 20 H140 L150 224 H108 L100 96 L92 224 H50 Z"/>
      <path ${shade} d="M100 96 L108 224 H120 Q110 150 100 96 Z" opacity=".7"/>
      <path ${shade} d="M60 20 L50 224 H64 Q60 120 64 20 Z" opacity=".5"/>
      <path ${line} d="M60 34 H140"/>
      <path ${stitch} d="M60 30 H140"/>
      <path ${line} d="M100 34 V80 Q100 90 92 92"/>
      <path ${line} d="M80 34 L78 224 M120 34 L122 224" opacity=".35"/>
      <path ${line} d="M64 40 Q74 52 72 64 M136 40 Q126 52 128 64"/>
      <path ${line} d="M72 20 V34 M128 20 V34 M100 20 V34" opacity=".6"/>
      <path ${stitch} d="M52 214 H92 M108 214 H148"/>`,

    dress: `
      <path ${body} d="M80 18 L86 18 L92 58 Q100 64 108 58 L114 18 L120 18 L126 72 Q130 92 124 104 L164 226 Q100 234 36 226 L76 104 Q70 92 74 72 Z"/>
      <path ${shade} d="M124 104 L164 226 Q150 228 138 229 Q136 160 124 104 Z" opacity=".6"/>
      <path ${shade} d="M76 104 L36 226 Q46 227 56 228 Q70 150 76 104 Z" opacity=".4"/>
      <path ${line} d="M74 104 Q100 112 126 104"/>
      <path ${stitch} d="M76 100 Q100 107 124 100"/>
      <path ${line} d="M92 108 Q86 170 72 228 M108 108 Q116 170 130 229 M100 110 V230" opacity=".3"/>
      <path ${line} d="M92 58 Q100 64 108 58"/>
      <path ${stitch} d="M40 218 Q100 226 160 218"/>`,

    kurta: `
      <path ${body} d="M66 34 L88 26 Q100 30 112 26 L134 34 L166 60 L182 130 L162 134 L146 86 L150 226 L50 226 L54 86 L38 134 L18 130 L34 60 Z"/>
      <path ${shade} d="M54 86 L38 134 L18 130 L34 60 L52 70 Z" opacity=".6"/>
      <path ${shade} d="M146 86 L150 226 L132 226 Q142 150 146 86 Z" opacity=".5"/>
      <path ${body} d="M88 26 L88 18 Q100 14 112 18 L112 26 Q100 30 88 26 Z"/>
      <path ${line} d="M100 28 V96"/>
      <path ${line} d="M96 28 V96 H104 V28" opacity=".5"/>
      <g fill="var(--g-line)"><circle cx="100" cy="44" r="1.8"/><circle cx="100" cy="62" r="1.8"/><circle cx="100" cy="80" r="1.8"/></g>
      <path ${line} d="M52 188 L50 226 M148 188 L150 226" stroke-width="2"/>
      <path ${stitch} d="M54 218 H146 M22 124 L40 128 M178 124 L160 128"/>
      <path ${line} d="M118 110 H136 V132 H118" opacity=".5"/>`,

    jacket: `
      <path ${body} d="M60 30 L86 22 L100 30 L114 22 L140 30 L170 50 L186 168 L162 172 L152 88 L152 206 L48 206 L48 88 L38 172 L14 168 L30 50 Z"/>
      <path ${shade} d="M48 88 L38 172 L14 168 L30 50 L48 58 Z" opacity=".6"/>
      <path ${shade} d="M152 88 L152 206 L134 206 Q146 150 152 88 Z" opacity=".5"/>
      <path ${body} d="M48 206 H152 V222 H48 Z"/>
      <path ${stitch} d="M48 211 H152 M48 217 H152"/>
      <path ${body} d="M86 22 L78 48 L94 44 L100 30 Z M114 22 L122 48 L106 44 L100 30 Z"/>
      <path ${line} d="M100 30 V222"/>
      <g fill="var(--g-line)"><circle cx="94" cy="70" r="2.3"/><circle cx="94" cy="104" r="2.3"/><circle cx="94" cy="138" r="2.3"/><circle cx="94" cy="172" r="2.3"/></g>
      <path ${line} d="M58 140 H90 V180 H58 Z M110 140 H142 V180 H110 Z"/>
      <path ${line} d="M114 80 H140 V100 H114 Z" opacity=".6"/>
      <path ${stitch} d="M61 143 H87 M113 143 H139 M18 160 L38 163 M182 160 L162 163"/>`
  };

  function shadeOf(hex, amt) {
    const n = parseInt(hex.replace('#', ''), 16);
    const r = Math.max(0, Math.min(255, (n >> 16) + amt));
    const g = Math.max(0, Math.min(255, ((n >> 8) & 255) + amt));
    const b = Math.max(0, Math.min(255, (n & 255) + amt));
    return `rgb(${r}, ${g}, ${b})`;
  }

  function isDark(hex) {
    const n = parseInt(hex.replace('#', ''), 16);
    const l = 0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255);
    return l < 110;
  }

  window.Garment = {
    svg(type, color) {
      const c = color || '#e9e1d4';
      const lineColor = isDark(c) ? 'rgba(255,255,255,.55)' : 'rgba(27,26,23,.72)';
      return `<svg class="garment" viewBox="0 0 200 240" role="img" aria-label="${type} sketch"
        style="--g-fill:${c};--g-shade:${shadeOf(c, -22)};--g-line:${lineColor}">
        ${shapes[type] || shapes.tee}
      </svg>`;
    },
    render(el, type, color) {
      el.innerHTML = this.svg(type, color);
    }
  };
})();
