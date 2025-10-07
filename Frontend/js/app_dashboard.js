const data = {
  avance: 75,
  stats: { indicadores: 20, metas: 35, actividades: 50, recursos: 50000 },
  reporte: [
    { nombre: 'Actividad 1', estado: 'Completada' },
    { nombre: 'Actividad 2', estado: 'En proceso' },
    { nombre: 'Actividad 3', estado: 'Retrasada' },
    { nombre: 'Actividad 4', estado: 'Pendiente' },
  ],
  recursos: [
    { etiqueta: 'Personal', valor: 68 },
    { etiqueta: 'Infraestructura', valor: 45 },
    { etiqueta: 'Equipamiento', valor: 30 },
    { etiqueta: 'Otros', valor: 20 },
  ],
};

// ====== Pinta tarjetas del dashboard ======
function formatoMoneda(n) {
  return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(n);
}
function claseChip(estado) {
  const e = estado.toLowerCase();
  if (e.includes('complet')) return 'chip chip--ok';
  if (e.includes('proceso')) return 'chip chip--info';
  if (e.includes('retras')) return 'chip chip--warn';
  return 'chip chip--danger';
}
function pintarAvance(valor) {
  const ring = document.querySelector('.ring');
  const txt = document.getElementById('progressValue');
  if (!ring || !txt) return;
  ring.style.setProperty('--value', 0);
  const target = Math.max(0, Math.min(100, valor));
  let cur = 0;
  const step = () => {
    cur += Math.max(1, Math.round((target - cur) / 8));
    ring.style.setProperty('--value', cur);
    txt.textContent = `${cur}%`;
    if (cur < target) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
function pintarStats(s) {
  const ids = ['statIndicadores','statMetas','statActividades','statRecursos'];
  if (!ids.every(id => document.getElementById(id))) return;
  document.getElementById('statIndicadores').textContent = s.indicadores;
  document.getElementById('statMetas').textContent = s.metas;
  document.getElementById('statActividades').textContent = s.actividades;
  document.getElementById('statRecursos').textContent = formatoMoneda(s.recursos);
}
function pintarReporte(items) {
  const ul = document.getElementById('reportList');
  if (!ul) return;
  ul.innerHTML = '';
  items.forEach((it) => {
    const li = document.createElement('li');
    const name = document.createElement('span');
    const chip = document.createElement('span');
    name.textContent = it.nombre;
    chip.textContent = it.estado;
    chip.className = claseChip(it.estado);
    li.appendChild(name);
    li.appendChild(chip);
    ul.appendChild(li);
  });
}
function pintarBarras(items) {
  const cont = document.getElementById('resourcesBars');
  if (!cont) return;
  cont.innerHTML = '';
  items.forEach((it) => {
    const row = document.createElement('div');
    row.className = 'bar';
    const label = document.createElement('div');
    label.className = 'bar__label';
    label.textContent = it.etiqueta;
    const track = document.createElement('div');
    track.className = 'bar__track';
    const fill = document.createElement('div');
    fill.className = 'bar__fill';
    fill.style.setProperty('--w', 0);
    requestAnimationFrame(() => {
      fill.style.setProperty('--w', Math.max(0, Math.min(100, it.valor)) / 100);
    });
    track.appendChild(fill);
    const val = document.createElement('div');
    val.className = 'bar__value';
    val.textContent = `${it.valor}%`;
    row.appendChild(label);
    row.appendChild(track);
    row.appendChild(val);
    cont.appendChild(row);
  });
}

// ====== Helpers SPA y API ======
const API    = "http://127.0.0.1:8000";
const $view  = document.getElementById('view');
const $title = document.getElementById('pageTitle');

function authHeaders() {
  const t = localStorage.getItem("token");
  return t ? { Authorization: "Bearer " + t } : {};
}
async function loadHTML(url) {
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error('No se pudo cargar ' + url);
  return res.text();
}
function loadScriptOnce(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[data-dyn="${src}"]`)) return resolve();
    const s = document.createElement('script');
    s.src = src;
    s.type = 'module'; // si tu plan_form.js NO usa import/export, puedes quitar esta línea
    s.dataset.dyn = src;
    s.onload = resolve;
    s.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
    document.body.appendChild(s);
  });
}
function setActiveByHash(hash) {
  document.querySelectorAll('.nav__item').forEach(a => a.classList.remove('is-active'));
  const active = document.querySelector(`a[href="${hash}"]`);
  if (active) active.classList.add('is-active');
}
const esc = (s='') => String(s).replace(/[&<>"']/g, m=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[m]));
function fechaCL(iso='') {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return esc(iso);
  return d.toLocaleDateString('es-CL', { timeZone: 'UTC' });
}
function tituloDimension(dim) {
  switch(dim){
    case 'LIDERAZGO':           return 'Liderazgo';
    case 'GESTION_PEDAGOGICA':  return 'Gestión Pedagógica';
    case 'CONVIVENCIA_ESCOLAR': return 'Convivencia Escolar';
    case 'GESTION_RECURSOS':    return 'Gestión de Recursos';
    default: return dim;
  }
}

// ====== Cache y obtención de planes por dimensión ======
const plansCache = new Map(); // dimension -> { list:Array, groups:Map(objetivo->Array) }
window.invalidatePlansCache = (dim) => dim ? plansCache.delete(dim) : plansCache.clear();

async function getPlansByDimension(dimensionValue) {
  if (plansCache.has(dimensionValue)) return plansCache.get(dimensionValue);

  const res = await fetch(`${API}/plans?dimension=${encodeURIComponent(dimensionValue)}`, {
    headers: { ...authHeaders() }
  });
  if (res.status === 401) { window.location.href = 'login.html'; return { list: [], groups: new Map() }; }

  const list = await res.json();
  // Agrupa por objetivo 
  const groups = new Map();
  for (const p of list) {
    const key = (p.objetivo_estrategico || '').trim() || '(Sin objetivo)';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(p);
  }
  const value = { list, groups };
  plansCache.set(dimensionValue, value);
  return value;
}

// ====== Vistas ======
async function showDashboard() {
  $title.textContent = 'Panel de Gestión';
  $view.innerHTML = `
    <section class="grid">
      <article class="card">
        <header class="card__header"><h2>Avance del Plan Estratégico</h2></header>
        <div class="card__body plan">
          <div class="progress">
            <div class="ring" style="--value: 75" aria-label="Avance 75%">
              <div class="ring__inside"><div class="ring__value" id="progressValue">75%</div></div>
            </div>
          </div>
          <ul class="stats">
            <li><span>Indicadores</span><strong id="statIndicadores">20</strong></li>
            <li><span>Metas</span><strong id="statMetas">35</strong></li>
            <li><span>Actividades</span><strong id="statActividades">50</strong></li>
            <li><span>Recursos</span><strong id="statRecursos">$50.000</strong></li>
          </ul>
        </div>
      </article>
      <article class="card">
        <header class="card__header"><h2>Reporte de Gestión</h2></header>
        <div class="card__body"><ul class="report" id="reportList"></ul></div>
      </article>
      <article class="card card--wide">
        <header class="card__header"><h2>Seguimiento de Recursos</h2></header>
        <div class="card__body"><div class="bars" id="resourcesBars"></div></div>
      </article>
    </section>
  `;
  pintarAvance(data.avance);
  pintarStats(data.stats);
  pintarReporte(data.reporte);
  pintarBarras(data.recursos);
}

async function showPlanForm() {
  $title.textContent = 'Formulario de Planes Estratégicos';
  const html = await loadHTML('plan_form.html');
  $view.innerHTML = html;
  await loadScriptOnce('js/plan_form.js');
  if (window.initPlanForm) window.initPlanForm();
}

// ====== Vista 1: listado de objetivos (primer paso) ======
async function showPlanList(dimensionValue) {
  $title.textContent = `Plan Estratégico — ${tituloDimension(dimensionValue)}`;
  $view.innerHTML = `
    <section class="card card--full">
      <header class="card__header" style="display:flex;justify-content:space-between;align-items:center;">
        <h2 style="margin:0;">${tituloDimension(dimensionValue)}</h2>
        <button id="btnRefrescar" class="btn">Refrescar</button>
      </header>
      <div class="card__body" id="plansList">Cargando…</div>
    </section>
  `;

  const $list = document.getElementById('plansList');
  const { groups } = await getPlansByDimension(dimensionValue);

  if (!groups || groups.size === 0) {
    $list.innerHTML = `<p>Sin planes para esta dimensión.</p>`;
    return;
  }

  let i = 1;
  let html = `<ol class="obj-list">`;
  const orden = [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0], 'es'));
  for (const [objetivo, items] of orden) {
    const oEnc = encodeURIComponent(objetivo); 
    html += `
      <li class="obj-item">
        <div class="obj-item__title">
          <span class="obj-item__num">${i++}.</span> ${esc(objetivo)}
        </div>
        <div class="obj-item__actions">
          <button class="btn btn--sm" data-act="ver" data-obj="${oEnc}">Ir al objetivo</button>
          <button class="btn btn--sm" data-act="rec" data-obj="${oEnc}">Recursos del objetivo</button>
          <button class="btn btn--sm" data-act="ver" data-obj="${oEnc}">Evidencias</button>
          <span class="obj-item__meta">${items.length} acción(es)</span>
        </div>
      </li>
    `;
  }
  html += `</ol>`;
  $list.innerHTML = html;

  $list.addEventListener('click', (ev) => {
    const btn = ev.target.closest('button[data-act]');
    if (!btn) return;
    const objetivo = decodeURIComponent(btn.dataset.obj || '');
    if (btn.dataset.act === 'ver')  showObjectiveDetail(dimensionValue, objetivo);
    if (btn.dataset.act === 'rec')  showObjectiveResources(dimensionValue, objetivo);
  });

  document.getElementById('btnRefrescar')?.addEventListener('click', () => {
    plansCache.delete(dimensionValue);
    showPlanList(dimensionValue);
  });
}

// ====== Vista 2: detalle del objetivo (tabla de acciones) ======
async function showObjectiveDetail(dimensionValue, objetivo) {
  const { groups } = await getPlansByDimension(dimensionValue);
  const items = (groups.get(objetivo) || []).slice()
    .sort((a, b) => (a.fecha_inicio || '').localeCompare(b.fecha_inicio || ''));

  $title.textContent = `${tituloDimension(dimensionValue)} — Objetivo`;
  $view.innerHTML = `
    <section class="card card--full">
      <header class="card__header" style="display:flex;gap:.5rem;align-items:center;">
        <button class="btn btn--ghost" id="btnVolver">← Volver</button>
        <h2 style="margin:0;">${esc(objetivo)}</h2>
      </header>
      <div class="card__body">
        <div class="table-wrap">
          <table class="plan-table">
            <thead>
              <tr>
                <th>Colegio</th>
                <th>Estrategia</th>
                <th>Subdimensiones</th>
                <th>Acción</th>
                <th>Descripción</th>
                <th>Inicio</th>
                <th>Término</th>
                <th>Programa</th>
                <th>Responsable</th>
              </tr>
            </thead>
            <tbody>
              ${items.map(r => `
                <tr>
                  <td>${esc(r.colegio)}</td>
                  <td>${esc(r.estrategia)}</td>
                  <td>${esc(r.subdimension)}</td>
                  <td>${esc(r.accion)}</td>
                  <td>${esc(r.descripcion)}</td>
                  <td>${fechaCL(r.fecha_inicio)}</td>
                  <td>${fechaCL(r.fecha_termino)}</td>
                  <td>${esc(r.programa_asociado)}</td>
                  <td>${esc(r.responsable)}</td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  `;
  document.getElementById('btnVolver')?.addEventListener('click', () => showPlanList(dimensionValue));
}

// recursos asociados a un objetivo
async function showObjectiveResources(dimensionValue, objetivo) {
  const { groups } = await getPlansByDimension(dimensionValue);
  const plans = (groups.get(objetivo) || []).slice()
    .sort((a, b) => (a.fecha_inicio || '').localeCompare(b.fecha_inicio || ''));

  // Traer recursos por cada plan
  const lists = await Promise.all(
    plans.map(p =>
      fetch(`${API}/plans/${p.id}/resources`, { headers: { ...authHeaders() } })
        .then(r => r.ok ? r.json() : [])
        .catch(() => [])
    )
  );

  // Aplanar: una fila por recurso (si un plan no tiene recursos, ponemos una fila vacía)
  const rows = [];
  lists.forEach((resources, idx) => {
    const plan = plans[idx];
    if (Array.isArray(resources) && resources.length) {
      resources.forEach(res => rows.push({ plan, res }));
    } else {
      rows.push({ plan, res: null });
    }
  });

  const money = (v) => {
    if (v === null || v === undefined || v === '') return '–';
    const n = Number(v);
    return Number.isFinite(n) ? formatoMoneda(n) : String(v);
  };
  const txt = (v) => (v && String(v).trim()) ? String(v) : '–';

  $title.textContent = `${tituloDimension(dimensionValue)} — Recursos`;
  $view.innerHTML = `
    <section class="card card--full">
      <header class="card__header" style="display:flex;gap:.5rem;align-items:center;">
        <button class="btn btn--ghost" id="btnVolver">← Volver</button>
        <h2 style="margin:0;">Recursos — ${esc(objetivo)}</h2>
      </header>

      <div class="card__body table-wrap">
        <div class="scroll-btns">
          <button class="btn-swipe" data-dir="-1">◀</button>
          <button class="btn-swipe" data-dir="1">▶</button>
        </div>

        <div class="hscroll" id="recWrap">
          <table class="plan-table">
            <colgroup>
              <col class="w-lg">  <!-- Recursos Necesarios -->
              <col class="w-xs">  <!-- Ate -->
              <col class="w-xs">  <!-- TIC -->
              <col class="w-md">  <!-- Plan(es) -->
              <col class="w-md">  <!-- Medios de verificación -->
              <col class="w-sm"><col class="w-sm"><col class="w-sm"><col class="w-sm">
              <col class="w-sm"><col class="w-sm"><col class="w-sm"><col class="w-sm">
              <col class="w-sm"><col class="w-sm"><col class="w-sm">
            </colgroup>
            <thead>
              <tr>
                <th>Recursos Necesarios<br/>Ejecución</th>
                <th>Ate</th>
                <th>TIC</th>
                <th>Plan(es)</th>
                <th>Medios de Verificación</th>
                <th>Monto Subv. General</th>
                <th>Monto SEP</th>
                <th>Monto PIE</th>
                <th>Monto EIB</th>
                <th>Monto Mantención</th>
                <th>Monto Pro retención</th>
                <th>Monto Internado</th>
                <th>Monto Reforzamiento</th>
                <th>Monto FAEP</th>
                <th>Monto Aporte Municipal</th>
                <th>Monto Total</th>
              </tr>
            </thead>
            <tbody id="tbRecursos"></tbody>
          </table>
        </div>
      </div>
    </section>
  `;

  const $tb = document.getElementById('tbRecursos');
  if (!rows.length) {
    $tb.innerHTML = `<tr><td colspan="16">Sin datos de recursos para este objetivo.</td></tr>`;
  } else {
    $tb.innerHTML = rows.map(({ plan, res }) => `
      <tr>
        <td>${esc(txt(res?.recursos_necesarios))}</td>
        <td>${esc(txt(res?.ate))}</td>
        <td>${esc(txt(res?.tic))}</td>
        <td>${esc(txt(res?.planes))}</td>
        <td>${esc(txt(res?.medios_verificacion))}</td>

        <td class="money">${money(res?.monto_subvencion_general)}</td>
        <td class="money">${money(res?.monto_sep)}</td>
        <td class="money">${money(res?.monto_pie)}</td>
        <td class="money">${money(res?.monto_eib)}</td>
        <td class="money">${money(res?.monto_mantenimiento)}</td>   <!-- OJO: mantenimiento -->
        <td class="money">${money(res?.monto_pro_retencion)}</td>
        <td class="money">${money(res?.monto_internado)}</td>
        <td class="money">${money(res?.monto_reforzamiento)}</td>
        <td class="money">${money(res?.monto_faep)}</td>
        <td class="money">${money(res?.monto_aporte_municipal)}</td>
        <td class="money"><strong>${money(res?.monto_total)}</strong></td>
      </tr>
    `).join('');
  }

  // Botones de desplazamiento horizontal
  const wrap = document.getElementById('recWrap');
  document.querySelectorAll('.btn-swipe').forEach(b => {
    b.addEventListener('click', () => {
      const step = 420;
      const dir  = Number(b.dataset.dir);
      wrap.scrollBy({ left: step * dir, behavior: 'smooth' });
    });
  });

  document.getElementById('btnVolver')?.addEventListener('click', () => showPlanList(dimensionValue));
}


// ==== REPORTES =====

function showReportes() {
    $title.textContent = 'Reportes'; 
    
    $view.innerHTML = `
      <section class="card card--full">
        <header class="card__header">
          <h2 style="margin:0;">Reportes</h2>
        </header>
        <div class="card__body" style="padding: 50px; text-align: center;">
          <h1 style="color: var(--primary); font-size: 2.5rem;">En proceso...</h1>
          <p style="margin-top: 15px; font-size: 1.2rem;">
              Pronto podrás acceder a los informes de gestión.
          </p>
        </div>
      </section>
    `;
    
}

// ======== Funcion para la transicion de acordeon =========
function setupAccordionTransition() {
  document.querySelectorAll('.nav__details').forEach(details => {
    const content = details.querySelector('.nav__submenu-content');
    const summary = details.querySelector('summary'); 
    if (!content || !summary) return;
    
    if (details.open) {
      content.style.maxHeight = content.scrollHeight + 'px';
      content.style.transition = 'max-height 0.4s ease-in-out';
    } else {
      content.style.maxHeight = '0';
    }

    summary.addEventListener('click', (e) => { 
      e.preventDefault(); 

      const isOpening = !details.open; 
      if (isOpening) {
        details.open = true; 
        content.style.transition = 'none';
        const scrollHeight = content.scrollHeight;
        
        requestAnimationFrame(() => {
          content.style.maxHeight = scrollHeight + 'px';
          content.style.transition = 'max-height 0.4s ease-in-out';
        });

      } else {
        content.style.transition = 'none';
        content.style.maxHeight = content.scrollHeight + 'px';
        
        requestAnimationFrame(() => {
          content.style.transition = 'max-height 0.4s ease-in-out';
          content.style.maxHeight = '0';
          
          const transitionEndHandler = () => {
            details.open = false;
            content.removeEventListener('transitionend', transitionEndHandler);
          };
          content.addEventListener('transitionend', transitionEndHandler);
        });
      }
    });
  });
}


// ====== Router por hash ======
async function router() {
  const hash = location.hash || '#/dashboard';
  setActiveByHash(hash);

  if (hash === '#/dashboard')          return showDashboard();
  if (hash === '#/reportes')           return showReportes();
  if (hash === '#/planes/form')        return showPlanForm();
  if (hash === '#/planes/liderazgo')   return showPlanList('LIDERAZGO');
  if (hash === '#/planes/gestion')     return showPlanList('GESTION_PEDAGOGICA');
  if (hash === '#/planes/convivencia') return showPlanList('CONVIVENCIA_ESCOLAR');
  if (hash === '#/planes/recursos')    return showPlanList('GESTION_RECURSOS');


  // fallback
  return showDashboard();
}
window.addEventListener('hashchange', router);
window.addEventListener('DOMContentLoaded', router);
window.addEventListener('DOMContentLoaded', setupAccordionTransition);

// (opcional) listeners directos si tienes botones con IDs:
document.getElementById('nav-dashboard')?.addEventListener('click', e => { e.preventDefault(); location.hash = '#/dashboard'; });
document.getElementById('nav-plan-form')?.addEventListener('click', e => { e.preventDefault(); location.hash = '#/planes/form'; });