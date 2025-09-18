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
window.addEventListener('DOMContentLoaded', () => {
  pintarAvance(data.avance);
  pintarStats(data.stats);
  pintarReporte(data.reporte);
  pintarBarras(data.recursos);
});

