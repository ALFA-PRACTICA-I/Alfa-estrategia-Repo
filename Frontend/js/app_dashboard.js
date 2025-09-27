const data = {
  avance: 75,
  stats: {
    indicadores: 20,
    metas: 35,
    actividades: 50,
    recursos: 50000,
  },
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
  document.getElementById('statIndicadores').textContent = s.indicadores;
  document.getElementById('statMetas').textContent = s.metas;
  document.getElementById('statActividades').textContent = s.actividades;
  document.getElementById('statRecursos').textContent = formatoMoneda(s.recursos);
}

function pintarReporte(items) {
  const ul = document.getElementById('reportList');
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

// -----------------------------------------------------------
// NUEVA LÓGICA PARA CAMBIO DE CONTENIDO Y PLACEHOLDERS
// -----------------------------------------------------------

const placeholderContent = {
  dashboard: {
    title: 'Panel de Gestión',
    isDashboard: true,
    html: '', 
  },
  liderazgo: {
    title: 'Plan Estratégico: Liderazgo',
    html: `
      <header class="header"><h1>Plan Estratégico: Liderazgo</h1></header>
      <div class="card" style="padding: 20px; font-size: 1.5rem; text-align: center; height: 400px; display: grid; place-items: center;">
        Placeholder 1: Contenido de Liderazgo
      </div>
    `,
  },
  'gestion-pedagogica': {
    title: 'Plan Estratégico: Gestión Pedagógica',
    html: `
      <header class="header"><h1>Plan Estratégico: Gestión Pedagógica</h1></header>
      <div class="card" style="padding: 20px; font-size: 1.5rem; text-align: center; height: 400px; display: grid; place-items: center;">
        Placeholder 2: Contenido de Gestión Pedagógica
      </div>
    `,
  },
  'convivencia-escolar': {
    title: 'Plan Estratégico: Convivencia Escolar',
    html: `
      <header class="header"><h1>Plan Estratégico: Convivencia Escolar</h1></header>
      <div class="card" style="padding: 20px; font-size: 1.5rem; text-align: center; height: 400px; display: grid; place-items: center;">
        Placeholder 3: Contenido de Convivencia Escolar
      </div>
    `,
  },
  'gestion-recursos': {
    title: 'Plan Estratégico: Gestión de Recursos',
    html: `
      <header class="header"><h1>Plan Estratégico: Gestión de Recursos</h1></header>
      <div class="card" style="padding: 20px; font-size: 1.5rem; text-align: center; height: 400px; display: grid; place-items: center;">
        Placeholder 4: Contenido de Gestión de Recursos
      </div>
    `,
  },
};

function showContent(sectionKey) {
  const content = placeholderContent[sectionKey];
  
  // Referencias a las áreas de contenido
  const originalContent = document.getElementById('dashboard-original-content');
  const dynamicContent = document.getElementById('dynamic-content-area');

  // Lógica de activación de menú ('is-active')
  document.querySelectorAll('.nav__item').forEach(item => item.classList.remove('is-active'));
  
  const activeItem = document.querySelector(`[data-section="${sectionKey}"]`) || document.getElementById(`menu-${sectionKey}`);
  if (activeItem) {
    activeItem.classList.add('is-active');
    // Si es un submenú, activa también el Plan Estratégico
    if (sectionKey !== 'dashboard') {
        const planItem = document.querySelector('.plan--item');
        if(planItem) planItem.classList.add('is-active');
    }
  } else if (sectionKey === 'dashboard') {
     document.getElementById('menu-dashboard').classList.add('is-active');
  }

  // Lógica para mostrar/ocultar el contenido
  if (content.isDashboard) {
    // Mostrar el dashboard original
    originalContent.style.display = 'block';
    dynamicContent.style.display = 'none';
  } else {
    // Mostrar el contenido dinámico (Placeholder)
    originalContent.style.display = 'none';
    dynamicContent.innerHTML = content.html;
    dynamicContent.style.display = 'block';
  }
}

window.addEventListener('DOMContentLoaded', () => {
  // Inicializa los datos del dashboard original
  pintarAvance(data.avance);
  pintarStats(data.stats);
  pintarReporte(data.reporte);
  pintarBarras(data.recursos);
  
  // 1. Ocultamos el contenido dinámico al inicio
  document.getElementById('dynamic-content-area').style.display = 'none';
  
  // 2. Listener para los submenús (Liderazgo, Gestión Pedagógica, etc.)
  const subMenuItems = document.querySelectorAll('.sub-menu-item');
  subMenuItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const section = e.target.closest('a').dataset.section;
      showContent(section);
    });
  });

  // 3. Listener para el item de Dashboard
  document.getElementById('menu-dashboard').addEventListener('click', (e) => {
      e.preventDefault();
      showContent('dashboard');
  });

  // 4. Aseguramos que el menú del Plan Estratégico esté siempre desplegado y listo.
  const planDetails = document.querySelector('.nav__details');
  if (planDetails) {
      planDetails.setAttribute('open', '');
  }

  // 5. Mostrar el Dashboard por defecto al cargar
  showContent('dashboard'); 
});