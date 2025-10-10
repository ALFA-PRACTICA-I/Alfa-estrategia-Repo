// js/plan_form.js
export function initPlanForm() {
  const API = "http://127.0.0.1:8000";
  const SCHOOL = "Liceo La Asuncion de Talcahuano";

  const authHeaders = () => {
    const t = localStorage.getItem("token");
    return t ? { Authorization: "Bearer " + t } : {};
  };

  const $form = document.getElementById("planForm");
  const $msg  = document.getElementById("plansMsg");
// fuerza colegio único
  const schoolEl = document.getElementById("p_school");
  if (schoolEl) {
    if (schoolEl.tagName === "SELECT") {
      schoolEl.innerHTML = `<option value="${SCHOOL}">${SCHOOL}</option>`;
      schoolEl.disabled = false;        // si quieres mostrarlo activo
    } else {
      schoolEl.value = SCHOOL;
      schoolEl.readOnly = true;         // si es <input>
    }
  }
  if (!$form) return;

  // -------------------------------
  // 1) Cargar select de dimensiones
  // -------------------------------
  (async () => {
    const sel = document.getElementById("p_dimension");
    if (!sel) return;
    sel.innerHTML = '<option value="">Cargando…</option>';
    try {
      const r = await fetch(`${API}/plans/dimensions`, { headers: { ...authHeaders() } });
      const arr = await r.json();
      sel.innerHTML = '<option value="">Seleccione…</option>' +
        arr.map(d => `<option value="${d}">${d.replaceAll("_"," ")}</option>`).join("");
    } catch {
      sel.innerHTML = '<option value="">Error al cargar</option>';
    }
  })();

  // -----------------------------------------
  // 2) Helpers para la sección de RECURSOS
  //    (IDs esperados en el HTML: ver comentario)
  // -----------------------------------------
  // Espera los campos:
  // r_need, r_ate, r_tic, r_planes, r_medios,
  // r_subv_gen, r_sep, r_pie, r_eib, r_mant, r_proret, r_internado, r_reforz,
  // r_faep, r_aporte_mun, r_total
  const $rTotal = document.getElementById('r_total');

  const num = (id) => {
    const el = document.getElementById(id);
    if (!el) return 0;
    const n = parseInt((el.value || '0').replace(/\D+/g, ''), 10);
    return Number.isFinite(n) ? n : 0;
  };
  const txt = (id) => (document.getElementById(id)?.value || '').trim();

  function setUpAutoTotal() {
    const ids = [
      'r_subv_gen','r_sep','r_pie','r_eib','r_mant','r_proret',
      'r_internado','r_reforz','r_faep','r_aporte_mun'
    ];
    if (!$rTotal) return;
    const calc = () => {
      const t = ids.reduce((s, id) => s + num(id), 0);
      $rTotal.value = t;
    };
    ids.forEach(id => document.getElementById(id)?.addEventListener('input', calc));
    calc();
  }
  // Inicializa auto-total solo si existe la sección
  if ($rTotal) setUpAutoTotal();

  function collectResourcePayload() {
    // Si no hay bloque de recursos en el HTML, no enviamos nada
    if (!$rTotal) return null;

    const payload = {
      recursos_necesarios: txt('r_need'),
      ate: txt('r_ate'),
      tic: txt('r_tic'),
      planes: txt('r_planes'),
      medios_verificacion: txt('r_medios'),
      monto_subvencion_general: num('r_subv_gen'),
      monto_sep: num('r_sep'),
      monto_pie: num('r_pie'),
      monto_eib: num('r_eib'),
      monto_mantenimiento: num('r_mant'),
      monto_pro_retencion: num('r_proret'),
      monto_internado: num('r_internado'),
      monto_reforzamiento: num('r_reforz'),
      monto_faep: num('r_faep'),
      monto_aporte_municipal: num('r_aporte_mun'),
      monto_total: num('r_total'),
    };

    // ¿Hay algo realmente informado?
    const anyText =
      payload.recursos_necesarios || payload.ate || payload.tic ||
      payload.planes || payload.medios_verificacion;
    const anyMonto =
      payload.monto_subvencion_general || payload.monto_sep || payload.monto_pie ||
      payload.monto_eib || payload.monto_mantenimiento || payload.monto_pro_retencion ||
      payload.monto_internado || payload.monto_reforzamiento || payload.monto_faep ||
      payload.monto_aporte_municipal;

    return (anyText || anyMonto) ? payload : null;
  }

  // -----------------------------------------
  // 3) Submit: crea PLAN y luego (opcional) RECURSOS
  // -----------------------------------------
  $form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if ($msg) { $msg.textContent = ""; $msg.className = "msg"; }

    // --- IMPORTANTE: nombres en ESPAÑOL como en el backend ---
    const payload = {
      dimension:            document.getElementById("p_dimension")?.value || "",
      colegio:              SCHOOL,
      objetivo_estrategico: document.getElementById("p_obj")?.value.trim() || "",
      estrategia:           document.getElementById("p_strategy")?.value.trim() || "",
      subdimension:         document.getElementById("p_sub")?.value.trim() || "",
      accion:               document.getElementById("p_action")?.value.trim() || "",
      descripcion:          document.getElementById("p_desc")?.value.trim() || "",
      fecha_inicio:         document.getElementById("p_start")?.value || "",
      fecha_termino:        document.getElementById("p_end")?.value || "",
      programa_asociado:    document.getElementById("p_program")?.value.trim() || "",
      responsable:          document.getElementById("p_resp")?.value.trim() || "",
    };

    // Valida obligatorios
    const faltan = [];
    if (!payload.dimension)            faltan.push("Dimensión");
    if (!payload.colegio)              faltan.push("Colegio");
    if (!payload.objetivo_estrategico) faltan.push("Objetivo Estratégico");
    if (!payload.fecha_inicio)         faltan.push("Fecha Inicio");
    if (!payload.fecha_termino)        faltan.push("Fecha Término");

    if (faltan.length) {
      if ($msg) {
        $msg.textContent = "Faltan: " + faltan.join(", ");
        $msg.className = "msg msg--error";
      }
      return;
    }

    try {
      // 1) Crear el plan
      const res = await fetch(`${API}/plans`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(payload)
      });
      if (res.status === 403) {
        $msg.textContent = "No tienes permisos para guardar.";
        $msg.className = "msg msg--error";
        return;
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if ($msg) {
          $msg.textContent = err.detail || "Error al guardar el plan";
          $msg.className = "msg msg--error";
        }
        return;
      }

      const created = await res.json();          
      const planId  = created.id;

      // 2) Si hay recursos, crearlos ligados al plan
      const resPayload = collectResourcePayload();
      if (resPayload) {
        await fetch(`${API}/plans/${planId}/resources`, {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify(resPayload)
        }).catch(() => {
          // No interrumpimos si falla recursos; solo avisamos por consola
          console.warn("No se pudieron guardar los recursos");
        });
      }

      if ($msg) {
        $msg.textContent = "Guardado correctamente";
        $msg.className = "msg msg--ok";
      }
      $form.reset();
      // Recalcula total 
      if ($rTotal) setUpAutoTotal();

    } catch (err) {
      if ($msg) {
        $msg.textContent = "Error de red";
        $msg.className = "msg msg--error";
      }
      console.error(err);
    }
  });
}

window.initPlanForm = initPlanForm;