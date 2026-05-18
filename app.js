// ============================================================
// Suivi Mission Consultant S&E — Initiative GreenTech Tunisie
// ============================================================

const DEFAULT_SETTINGS = {
  name: "Eya TBORSKI MANAI",
  client: "Caisse des Dépôts et Consignations",
  project: "Initiative GreenTech Tunisie — Greenov'i (Expertise France / UE)",
  signDate: "2026-03-04",
  startDate: "2026-03-04",
  duration: 19,
  total: 100700.000,
  monthly: 5300.000,
  net: 5300.000,
  delay: 15,
  workdays: 22,
  leaveQuota: 30,
  notes: ""
};

// Livrables types tirés du suivi (Excel) — modifiables ensuite
const DEFAULT_DELIVERABLES = [
  { title: "Manuel de procédures (MAJ)", desc: "Mise à jour du manuel de procédures du projet", recurrence: "ponctuel" },
  { title: "PV COPIL", desc: "Compte-rendu du comité de pilotage", recurrence: "trimestriel" },
  { title: "Rapport narratif périodique", desc: "Rapport narratif de période (P1, P2...)", recurrence: "trimestriel" },
  { title: "Planning mensuel", desc: "Planning des activités du mois", recurrence: "mensuel" },
  { title: "Cadre logique", desc: "Cadre logique du projet — version à jour", recurrence: "ponctuel" },
  { title: "Dashboard SERA", desc: "Tableau de suivi-évaluation et reporting (3 tableaux)", recurrence: "mensuel" },
  { title: "Compte-rendu info-session", desc: "Synthèse des sessions d'information aux bénéficiaires", recurrence: "ponctuel" },
  { title: "Règlement Intérieur (MAJ)", desc: "Mise à jour du règlement intérieur", recurrence: "ponctuel" },
  { title: "TDR Admin/Fin (MAJ)", desc: "Termes de référence Admin & Finance", recurrence: "ponctuel" },
  { title: "Charte du comité de sélection (MAJ)", desc: "Charte mise à jour", recurrence: "ponctuel" }
];

const STORE_KEY = "consultantTrackerData_v1";

let DATA = loadData();

function loadData() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  return {
    settings: { ...DEFAULT_SETTINGS },
    days: {},        // { "YYYY-MM-DD": { status, desc, deliverables } }
    deliverables: [],
    tasks: [],
    leaves: [],
    disbursements: []
  };
}
function saveData() { localStorage.setItem(STORE_KEY, JSON.stringify(DATA)); }
function uid() { return Math.random().toString(36).slice(2, 10); }
function fmtMoney(n) { return (Number(n) || 0).toLocaleString("fr-FR", { minimumFractionDigits: 3, maximumFractionDigits: 3 }) + " DT"; }
function pad(n) { return String(n).padStart(2, "0"); }
function ymd(d) { return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`; }
function parseYmd(s) { const [y,m,d] = s.split("-").map(Number); return new Date(y, m-1, d); }
function addMonths(date, n) { const d = new Date(date); d.setMonth(d.getMonth() + n); return d; }
function addDays(date, n) { const d = new Date(date); d.setDate(d.getDate() + n); return d; }

// ---------- TABS ----------
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
    renderAll();
  });
});

// ---------- DASHBOARD ----------
function renderDashboard() {
  const s = DATA.settings;
  document.getElementById("kpiName").textContent = s.name || "—";
  document.getElementById("kpiTotal").textContent = fmtMoney(s.total);
  document.getElementById("kpiMonthly").textContent = fmtMoney(s.monthly);
  document.getElementById("kpiDuration").textContent = `${s.duration} mois`;

  const paid = DATA.disbursements.filter(d => d.status === "paid");
  document.getElementById("kpiPaid").textContent = `${paid.length} / ${s.duration}`;
  const paidAmt = paid.reduce((a, b) => a + (Number(b.paidAmount) || 0), 0);
  document.getElementById("kpiRemaining").textContent = fmtMoney((s.total || 0) - paidAmt);

  // Days this month
  const now = new Date();
  const mPicker = document.getElementById("monthPicker");
  if (!mPicker.value) mPicker.value = `${now.getFullYear()}-${pad(now.getMonth()+1)}`;
  renderMonthSummary(mPicker.value);

  // Leaves left
  const usedLeaves = computeUsedLeaves();
  document.getElementById("kpiLeavesLeft").textContent = `${(s.leaveQuota - usedLeaves).toFixed(1)} / ${s.leaveQuota}`;

  // Upcoming payments
  const upcoming = DATA.disbursements
    .filter(d => d.status !== "paid")
    .sort((a,b) => (a.expectedDate || "").localeCompare(b.expectedDate || ""))
    .slice(0, 5);
  const ul = document.getElementById("upcomingPayments");
  ul.innerHTML = upcoming.length
    ? upcoming.map(d => `<li><b>Mois ${d.index}</b> — ${d.expectedDate || "?"} — ${fmtMoney(d.amount)} <span class="status-badge status-${d.status}">${d.status}</span></li>`).join("")
    : "<li>Aucune échéance enregistrée. Générez l'échéancier.</li>";

  // Deliverables stats
  const total = DATA.deliverables.length;
  const validated = DATA.deliverables.filter(d => d.validated).length;
  const delivered = DATA.deliverables.filter(d => d.deliveredDate).length;
  document.getElementById("deliverableStats").innerHTML =
    `<p><b>${total}</b> livrables enregistrés · <b>${delivered}</b> livrés · <b>${validated}</b> validés par le coordinateur.</p>`;

  renderAlerts();
}

function renderAlerts() {
  const today = ymd(new Date());
  const in7 = ymd(addDays(new Date(), 7));
  const alerts = [];

  DATA.deliverables.forEach(d => {
    if (d.dueDate && d.dueDate < today && !d.deliveredDate) {
      alerts.push({ level: "danger", msg: `Livrable en retard : <b>${esc(d.title)}</b>`, when: `prévu le ${d.dueDate}` });
    } else if (d.dueDate && d.dueDate <= in7 && !d.deliveredDate) {
      alerts.push({ level: "warn", msg: `Livrable à rendre bientôt : <b>${esc(d.title)}</b>`, when: `prévu le ${d.dueDate}` });
    }
    if (d.evaluationDeadline && d.evaluationDeadline < today && !d.validated) {
      alerts.push({ level: "danger", msg: `Évaluation en retard : <b>${esc(d.title)}</b> par ${esc(d.evaluator)}`, when: `échéance ${d.evaluationDeadline}` });
    } else if (d.evaluationDeadline && d.evaluationDeadline <= in7 && !d.validated) {
      alerts.push({ level: "warn", msg: `Évaluation proche : <b>${esc(d.title)}</b>`, when: `échéance ${d.evaluationDeadline}` });
    }
    if (d.deliveredDate && !d.justificatifLink && !d.justificatifFile) {
      alerts.push({ level: "info", msg: `Justificatif manquant : <b>${esc(d.title)}</b>`, when: "ajouter lien ou fichier" });
    }
  });

  DATA.tasks.forEach(t => {
    if (t.due && t.due < today && t.status !== "done") {
      alerts.push({ level: "warn", msg: `Tâche en retard : <b>${esc(t.title)}</b>`, when: `échéance ${t.due}` });
    }
  });

  DATA.disbursements.forEach(d => {
    if (d.expectedDate && d.expectedDate < today && d.status !== "paid") {
      alerts.push({ level: "danger", msg: `Paiement en retard : mois ${d.index} (${esc(d.month)})`, when: `attendu le ${d.expectedDate}` });
    }
    if (d.status === "paid" && !d.receiptFile && !d.receiptRef) {
      alerts.push({ level: "info", msg: `Reçu manquant : mois ${d.index} (${esc(d.month)})`, when: "uploader le reçu" });
    }
  });

  // Quota congés
  const usedLeaves = computeUsedLeaves();
  if (usedLeaves > DATA.settings.leaveQuota) {
    alerts.push({ level: "danger", msg: `Quota de congés dépassé : <b>${usedLeaves}</b> / ${DATA.settings.leaveQuota}`, when: "" });
  } else if (usedLeaves >= DATA.settings.leaveQuota * 0.8) {
    alerts.push({ level: "warn", msg: `Quota de congés bientôt atteint : <b>${usedLeaves}</b> / ${DATA.settings.leaveQuota}`, when: "" });
  }

  const list = document.getElementById("alertsList");
  if (!alerts.length) {
    list.innerHTML = `<p class="alert-empty">✅ Aucune alerte. Toutes les échéances sont respectées.</p>`;
    return;
  }
  list.innerHTML = alerts.map(a => `<div class="alert-item ${a.level}">${a.msg}${a.when?`<span class="when">(${a.when})</span>`:""}</div>`).join("");
}

function renderMonthSummary(monthStr) {
  if (!monthStr) return;
  const [y, m] = monthStr.split("-").map(Number);
  let pres=0, half=0, conge=0, auto=0, ferie=0;
  Object.entries(DATA.days).forEach(([dt, info]) => {
    const d = parseYmd(dt);
    if (d.getFullYear() === y && d.getMonth() === m-1) {
      if (info.status === "presence") pres++;
      else if (info.status === "half") half += 0.5;
      else if (info.status === "conge") conge++;
      else if (info.status === "autorisation") auto++;
      else if (info.status === "ferie") ferie++;
    }
  });
  const worked = pres + half;
  document.getElementById("kpiDaysMonth").textContent = worked.toFixed(1);
  document.getElementById("monthSummary").innerHTML = `
    <div><span>Jours travaillés :</span> <b>${worked.toFixed(1)}</b></div>
    <div><span>Demi-journées :</span> <b>${half * 2}</b></div>
    <div><span>Congés :</span> <b>${conge}</b></div>
    <div><span>Autorisations :</span> <b>${auto}</b></div>
    <div><span>Jours fériés :</span> <b>${ferie}</b></div>
    <div><span>Salaire calculé :</span> <b>${fmtMoney(computeMonthSalary(y, m))}</b></div>
  `;
}

function computeMonthSalary(y, m) {
  const s = DATA.settings;
  let worked = 0, workdaysInMonth = 0;
  const lastDay = new Date(y, m, 0).getDate();
  for (let d=1; d<=lastDay; d++) {
    const date = new Date(y, m-1, d);
    const dow = date.getDay();
    if (dow !== 0 && dow !== 6) workdaysInMonth++;
    const key = ymd(date);
    const info = DATA.days[key];
    if (info) {
      if (info.status === "presence") worked++;
      else if (info.status === "half") worked += 0.5;
      else if (info.status === "conge" || info.status === "ferie" || info.status === "autorisation") worked++;
    }
  }
  if (workdaysInMonth === 0) return 0;
  return (s.monthly || 0) * (worked / workdaysInMonth);
}

function computeUsedLeaves() {
  return Object.values(DATA.days).filter(d => d.status === "conge").length;
}

document.getElementById("monthPicker").addEventListener("change", e => renderMonthSummary(e.target.value));

// ---------- CALENDAR ----------
let calCurrent = new Date();

function renderCalendar() {
  const picker = document.getElementById("calMonth");
  if (!picker.value) picker.value = `${calCurrent.getFullYear()}-${pad(calCurrent.getMonth()+1)}`;
  const [y, m] = picker.value.split("-").map(Number);
  calCurrent = new Date(y, m-1, 1);
  const grid = document.getElementById("calendarGrid");
  grid.innerHTML = "";
  ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"].forEach(d => {
    const h = document.createElement("div"); h.className = "cal-head"; h.textContent = d; grid.appendChild(h);
  });
  const firstDow = (new Date(y, m-1, 1).getDay() + 6) % 7;
  for (let i=0; i<firstDow; i++) grid.appendChild(document.createElement("div"));
  const lastDay = new Date(y, m, 0).getDate();
  for (let d=1; d<=lastDay; d++) {
    const date = new Date(y, m-1, d);
    const key = ymd(date);
    const info = DATA.days[key] || {};
    const dow = date.getDay();
    const cell = document.createElement("div");
    cell.className = "cal-cell";
    if (info.status) cell.classList.add(info.status);
    else if (dow === 0 || dow === 6) cell.classList.add("weekend");
    cell.innerHTML = `<div class="d">${d}</div><div class="desc">${(info.desc||"").slice(0,40)}</div>`;
    cell.addEventListener("click", () => openDayEditor(key));
    grid.appendChild(cell);
  }
}

function openDayEditor(key) {
  document.getElementById("dayEditor").classList.remove("hidden");
  document.getElementById("editDate").textContent = key;
  const info = DATA.days[key] || {};
  document.getElementById("editStatus").value = info.status || "presence";
  document.getElementById("editDesc").value = info.desc || "";
  document.getElementById("editDeliv").value = info.deliverables || "";
  document.getElementById("dayEditor").dataset.key = key;
}

document.getElementById("saveDay").addEventListener("click", () => {
  const key = document.getElementById("dayEditor").dataset.key;
  DATA.days[key] = {
    status: document.getElementById("editStatus").value,
    desc: document.getElementById("editDesc").value,
    deliverables: document.getElementById("editDeliv").value
  };
  saveData(); renderCalendar();
});
document.getElementById("clearDay").addEventListener("click", () => {
  const key = document.getElementById("dayEditor").dataset.key;
  delete DATA.days[key]; saveData(); renderCalendar();
  document.getElementById("dayEditor").classList.add("hidden");
});
document.getElementById("closeDay").addEventListener("click", () => {
  document.getElementById("dayEditor").classList.add("hidden");
});
document.getElementById("calMonth").addEventListener("change", renderCalendar);
document.getElementById("prevMonth").addEventListener("click", () => {
  const p = document.getElementById("calMonth");
  const d = addMonths(calCurrent, -1);
  p.value = `${d.getFullYear()}-${pad(d.getMonth()+1)}`;
  renderCalendar();
});
document.getElementById("nextMonth").addEventListener("click", () => {
  const p = document.getElementById("calMonth");
  const d = addMonths(calCurrent, 1);
  p.value = `${d.getFullYear()}-${pad(d.getMonth()+1)}`;
  renderCalendar();
});

// ---------- DELIVERABLES ----------
function newDeliverable(extra = {}) {
  return {
    id: uid(),
    title: "Nouveau livrable", desc: "", recurrence: "ponctuel",
    dueDate: "", deliveredDate: "",
    status: "todo", validated: false,
    evaluator: "Coordinateur",
    evaluationMethod: "Revue documentaire",
    evaluationDeadline: "",
    notificationDate: "",
    justificatifLink: "",
    justificatifFile: "", justificatifFileName: "",
    notes: "",
    ...extra
  };
}

function renderDeliverables() {
  const list = document.getElementById("deliverablesList");
  if (!DATA.deliverables.length) {
    list.innerHTML = `<p class="alert-empty">Aucun livrable. Cliquez sur « Charger livrables types du contrat » pour pré-remplir.</p>`;
    return;
  }
  const today = ymd(new Date());
  list.innerHTML = DATA.deliverables.map(d => {
    const overdue = d.dueDate && d.dueDate < today && !d.deliveredDate;
    const cls = d.validated ? "validated" : (d.deliveredDate ? "delivered" : (overdue ? "overdue" : ""));
    const fileLink = d.justificatifFile
      ? `<a href="${d.justificatifFile}" download="${esc(d.justificatifFileName)}">📎 ${esc(d.justificatifFileName)}</a>
         <span class="clear-file" data-clear="${d.id}">✕</span>`
      : `<input type="file" data-f="justificatifFile" />`;
    return `
    <div class="deliv-card ${cls}" data-id="${d.id}">
      <div class="top">
        <input class="title" data-f="title" value="${esc(d.title)}" />
        <select data-f="status">
          <option value="todo" ${d.status==="todo"?"selected":""}>À faire</option>
          <option value="doing" ${d.status==="doing"?"selected":""}>En cours</option>
          <option value="delivered" ${d.status==="delivered"?"selected":""}>Livré</option>
        </select>
        <label style="flex-direction:row;align-items:center;gap:4px;">
          <input type="checkbox" data-f="validated" ${d.validated?"checked":""} /> Validé
        </label>
        ${overdue ? '<span class="status-badge status-overdue">EN RETARD</span>' : ''}
      </div>
      <div class="fields">
        <label>Description <textarea data-f="desc" rows="2">${esc(d.desc)}</textarea></label>
        <label>Récurrence
          <select data-f="recurrence">
            <option value="ponctuel" ${d.recurrence==="ponctuel"?"selected":""}>Ponctuel</option>
            <option value="mensuel" ${d.recurrence==="mensuel"?"selected":""}>Mensuel</option>
            <option value="trimestriel" ${d.recurrence==="trimestriel"?"selected":""}>Trimestriel</option>
            <option value="annuel" ${d.recurrence==="annuel"?"selected":""}>Annuel</option>
          </select>
        </label>
        <label>Date prévue <input type="date" data-f="dueDate" value="${d.dueDate||""}" /></label>
        <label>Date livrée <input type="date" data-f="deliveredDate" value="${d.deliveredDate||""}" /></label>
        <label>Évaluateur (qui ?) <input data-f="evaluator" value="${esc(d.evaluator)}" /></label>
        <label>Méthode d'évaluation (comment ?) <input data-f="evaluationMethod" value="${esc(d.evaluationMethod)}" /></label>
        <label>Échéance d'évaluation (quand ?) <input type="date" data-f="evaluationDeadline" value="${d.evaluationDeadline||""}" /></label>
        <label>Date notification <input type="date" data-f="notificationDate" value="${d.notificationDate||""}" /></label>
        <label>Justificatif — lien <input data-f="justificatifLink" value="${esc(d.justificatifLink)}" placeholder="URL Drive..." /></label>
        <label>Justificatif — fichier <div class="file-row">${fileLink}</div></label>
        <label style="grid-column: 1 / -1;">Notes <textarea data-f="notes" rows="2">${esc(d.notes)}</textarea></label>
      </div>
      <div class="actions">
        <button class="icon-btn" data-del="${d.id}">🗑️ Supprimer</button>
      </div>
    </div>`;
  }).join("");

  list.querySelectorAll(".deliv-card").forEach(card => {
    const id = card.dataset.id;
    card.querySelectorAll("input, select, textarea").forEach(el => {
      if (el.type === "file") {
        el.addEventListener("change", e => {
          const f = e.target.files[0];
          if (!f) return;
          if (f.size > 2 * 1024 * 1024) { alert("Fichier > 2 Mo : préférez un lien."); return; }
          const r = new FileReader();
          r.onload = ev => {
            const item = DATA.deliverables.find(x => x.id === id);
            item.justificatifFile = ev.target.result;
            item.justificatifFileName = f.name;
            saveData(); renderDeliverables();
          };
          r.readAsDataURL(f);
        });
      } else {
        el.addEventListener("change", e => {
          const item = DATA.deliverables.find(x => x.id === id);
          item[e.target.dataset.f] = e.target.type === "checkbox" ? e.target.checked : e.target.value;
          saveData(); renderDeliverables(); renderDashboard();
        });
      }
    });
    const clr = card.querySelector("[data-clear]");
    if (clr) clr.addEventListener("click", () => {
      const item = DATA.deliverables.find(x => x.id === id);
      item.justificatifFile = ""; item.justificatifFileName = "";
      saveData(); renderDeliverables();
    });
    card.querySelector("[data-del]").addEventListener("click", () => {
      if (confirm("Supprimer ce livrable ?")) {
        DATA.deliverables = DATA.deliverables.filter(x => x.id !== id);
        saveData(); renderDeliverables();
      }
    });
  });
}
document.getElementById("addDeliverable").addEventListener("click", () => {
  DATA.deliverables.push(newDeliverable());
  saveData(); renderDeliverables();
});
document.getElementById("seedDeliverables").addEventListener("click", () => {
  if (DATA.deliverables.length && !confirm("Ajouter les livrables types ? (les existants sont conservés)")) return;
  DEFAULT_DELIVERABLES.forEach(d => DATA.deliverables.push(newDeliverable(d)));
  saveData(); renderDeliverables();
});

// ---------- TASKS ----------
function renderTasks() {
  const filter = document.getElementById("taskFilter").value;
  const tb = document.getElementById("tasksBody");
  const list = filter === "all" ? DATA.tasks : DATA.tasks.filter(t => t.status === filter);
  tb.innerHTML = list.map(t => `
    <tr data-id="${t.id}">
      <td><input data-f="title" value="${esc(t.title)}" /></td>
      <td><textarea data-f="details" rows="1">${esc(t.details)}</textarea></td>
      <td><input type="date" data-f="due" value="${t.due||""}" /></td>
      <td>
        <select data-f="priority">
          <option value="low" ${t.priority==="low"?"selected":""}>Basse</option>
          <option value="med" ${t.priority==="med"?"selected":""}>Moyenne</option>
          <option value="high" ${t.priority==="high"?"selected":""}>Haute</option>
        </select>
      </td>
      <td>
        <select data-f="status">
          <option value="todo" ${t.status==="todo"?"selected":""}>À faire</option>
          <option value="doing" ${t.status==="doing"?"selected":""}>En cours</option>
          <option value="done" ${t.status==="done"?"selected":""}>Terminée</option>
        </select>
      </td>
      <td><button class="icon-btn" data-del="${t.id}">🗑️</button></td>
    </tr>
  `).join("");
  tb.querySelectorAll("input, select, textarea").forEach(el => {
    el.addEventListener("change", e => {
      const id = e.target.closest("tr").dataset.id;
      const item = DATA.tasks.find(x => x.id === id);
      item[e.target.dataset.f] = e.target.value;
      saveData();
    });
  });
  tb.querySelectorAll("[data-del]").forEach(b => b.addEventListener("click", () => {
    DATA.tasks = DATA.tasks.filter(x => x.id !== b.dataset.del);
    saveData(); renderTasks();
  }));
}
document.getElementById("addTask").addEventListener("click", () => {
  DATA.tasks.push({ id: uid(), title: "Nouvelle tâche", details: "", due: "", priority: "med", status: "todo" });
  saveData(); renderTasks();
});
document.getElementById("taskFilter").addEventListener("change", renderTasks);

// ---------- LEAVES ----------
function renderLeaves() {
  document.getElementById("leaveQuota").textContent = DATA.settings.leaveQuota;
  const tb = document.getElementById("leavesBody");
  tb.innerHTML = DATA.leaves.map(l => `
    <tr data-id="${l.id}">
      <td>
        <select data-f="type">
          <option value="conge" ${l.type==="conge"?"selected":""}>Congé</option>
          <option value="autorisation" ${l.type==="autorisation"?"selected":""}>Autorisation</option>
          <option value="maladie" ${l.type==="maladie"?"selected":""}>Maladie</option>
        </select>
      </td>
      <td><input type="date" data-f="from" value="${l.from||""}" /></td>
      <td><input type="date" data-f="to" value="${l.to||""}" /></td>
      <td><input type="checkbox" data-f="halfDay" ${l.halfDay?"checked":""} /></td>
      <td>${computeLeaveDays(l)}</td>
      <td><input data-f="reason" value="${esc(l.reason)}" /></td>
      <td>
        <select data-f="status">
          <option value="pending" ${l.status==="pending"?"selected":""}>En attente</option>
          <option value="approved" ${l.status==="approved"?"selected":""}>Approuvé</option>
          <option value="rejected" ${l.status==="rejected"?"selected":""}>Refusé</option>
        </select>
      </td>
      <td><button class="icon-btn" data-del="${l.id}">🗑️</button></td>
    </tr>
  `).join("");
  tb.querySelectorAll("input, select").forEach(el => {
    el.addEventListener("change", e => {
      const id = e.target.closest("tr").dataset.id;
      const item = DATA.leaves.find(x => x.id === id);
      const f = e.target.dataset.f;
      item[f] = e.target.type === "checkbox" ? e.target.checked : e.target.value;
      saveData(); renderLeaves();
    });
  });
  tb.querySelectorAll("[data-del]").forEach(b => b.addEventListener("click", () => {
    DATA.leaves = DATA.leaves.filter(x => x.id !== b.dataset.del);
    saveData(); renderLeaves();
  }));
}
function computeLeaveDays(l) {
  if (!l.from || !l.to) return 0;
  const days = Math.max(1, Math.round((parseYmd(l.to)-parseYmd(l.from))/86400000)+1);
  return l.halfDay ? 0.5 : days;
}
document.getElementById("addLeave").addEventListener("click", () => {
  DATA.leaves.push({ id: uid(), type: "conge", from: "", to: "", halfDay: false, reason: "", status: "pending" });
  saveData(); renderLeaves();
});

// ---------- DISBURSEMENTS ----------
function renderDisbursements() {
  const tb = document.getElementById("disbursementsBody");
  tb.innerHTML = DATA.disbursements.map(d => `
    <tr data-id="${d.id}">
      <td>${d.index}</td>
      <td>${d.month}</td>
      <td>${fmtMoney(d.amount)}</td>
      <td><input type="number" step="0.001" data-f="paidAmount" value="${d.paidAmount||""}" /></td>
      <td><input type="date" data-f="validationDate" value="${d.validationDate||""}" /></td>
      <td><input type="date" data-f="receivedDate" value="${d.receivedDate||""}" /></td>
      <td><input data-f="receiptRef" value="${esc(d.receiptRef)}" placeholder="N° reçu" /></td>
      <td class="receipt-cell">
        ${d.receiptFile
          ? `<span class="file-attach"><a href="${d.receiptFile}" download="${esc(d.receiptFileName)}">📎 ${esc(d.receiptFileName)}</a> <span class="clear-file" data-clear="${d.id}">✕</span></span>`
          : `<input type="file" data-f="receiptFile" accept="image/*,application/pdf" />`}
      </td>
      <td>
        <select data-f="status">
          <option value="pending" ${d.status==="pending"?"selected":""}>En attente</option>
          <option value="validated" ${d.status==="validated"?"selected":""}>Validé</option>
          <option value="paid" ${d.status==="paid"?"selected":""}>Payé</option>
          <option value="overdue" ${d.status==="overdue"?"selected":""}>Retard</option>
        </select>
      </td>
      <td><button class="icon-btn" data-del="${d.id}">🗑️</button></td>
    </tr>
  `).join("");
  tb.querySelectorAll("input, select").forEach(el => {
    if (el.type === "file") {
      el.addEventListener("change", e => {
        const id = e.target.closest("tr").dataset.id;
        const item = DATA.disbursements.find(x => x.id === id);
        const f = e.target.files[0];
        if (!f) return;
        if (f.size > 2 * 1024 * 1024) { alert("Fichier > 2 Mo : compressez ou utilisez un lien."); return; }
        const r = new FileReader();
        r.onload = ev => {
          item.receiptFile = ev.target.result;
          item.receiptFileName = f.name;
          saveData(); renderDisbursements();
        };
        r.readAsDataURL(f);
      });
    } else {
      el.addEventListener("change", e => {
        const id = e.target.closest("tr").dataset.id;
        const item = DATA.disbursements.find(x => x.id === id);
        item[e.target.dataset.f] = e.target.value;
        if (e.target.dataset.f === "validationDate" && e.target.value) {
          const expected = addDays(parseYmd(e.target.value), DATA.settings.delay || 15);
          item.expectedDate = ymd(expected);
        }
        saveData(); updateDisbTotals();
      });
    }
  });
  tb.querySelectorAll("[data-clear]").forEach(b => b.addEventListener("click", () => {
    const item = DATA.disbursements.find(x => x.id === b.dataset.clear);
    item.receiptFile = ""; item.receiptFileName = "";
    saveData(); renderDisbursements();
  }));
  tb.querySelectorAll("[data-del]").forEach(b => b.addEventListener("click", () => {
    DATA.disbursements = DATA.disbursements.filter(x => x.id !== b.dataset.del);
    saveData(); renderDisbursements();
  }));
  updateDisbTotals();
}
function updateDisbTotals() {
  const theoretical = DATA.disbursements.reduce((a,b)=>a+(Number(b.amount)||0),0);
  const received = DATA.disbursements.reduce((a,b)=>a+(Number(b.paidAmount)||0),0);
  document.getElementById("totalTheoretical").textContent = fmtMoney(theoretical);
  document.getElementById("totalReceived").textContent = fmtMoney(received);
  document.getElementById("totalRemaining").textContent = fmtMoney(theoretical - received);
}
document.getElementById("generateSchedule").addEventListener("click", () => {
  if (DATA.disbursements.length && !confirm("Remplacer l'échéancier existant ?")) return;
  const s = DATA.settings;
  const start = parseYmd(s.startDate);
  DATA.disbursements = [];
  for (let i=0; i<s.duration; i++) {
    const m = addMonths(start, i);
    const monthLabel = m.toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
    DATA.disbursements.push({
      id: uid(), index: i+1, month: monthLabel,
      amount: s.monthly, paidAmount: "",
      validationDate: "", expectedDate: "", receivedDate: "",
      receiptRef: "", status: "pending"
    });
  }
  saveData(); renderDisbursements();
});

// ---------- SETTINGS ----------
function loadSettingsForm() {
  const s = DATA.settings;
  document.getElementById("setName").value = s.name;
  document.getElementById("setClient").value = s.client;
  document.getElementById("setProject").value = s.project;
  document.getElementById("setSignDate").value = s.signDate;
  document.getElementById("setStartDate").value = s.startDate;
  document.getElementById("setDuration").value = s.duration;
  document.getElementById("setTotal").value = s.total;
  document.getElementById("setMonthly").value = s.monthly;
  document.getElementById("setNet").value = s.net;
  document.getElementById("setDelay").value = s.delay;
  document.getElementById("setWorkdays").value = s.workdays;
  document.getElementById("setLeaveQuota").value = s.leaveQuota;
  document.getElementById("setNotes").value = s.notes || "";
  document.getElementById("rMonthly").textContent = fmtMoney(s.monthly);
  document.getElementById("rDelay").textContent = s.delay;
  document.getElementById("rQuota").textContent = s.leaveQuota;
}
document.getElementById("setNotes").addEventListener("input", e => {
  DATA.settings.notes = e.target.value; saveData();
});
document.getElementById("saveSettings").addEventListener("click", () => {
  DATA.settings = {
    name: document.getElementById("setName").value,
    client: document.getElementById("setClient").value,
    project: document.getElementById("setProject").value,
    signDate: document.getElementById("setSignDate").value,
    startDate: document.getElementById("setStartDate").value,
    duration: +document.getElementById("setDuration").value,
    total: +document.getElementById("setTotal").value,
    monthly: +document.getElementById("setMonthly").value,
    net: +document.getElementById("setNet").value,
    delay: +document.getElementById("setDelay").value,
    workdays: +document.getElementById("setWorkdays").value,
    leaveQuota: +document.getElementById("setLeaveQuota").value,
    notes: document.getElementById("setNotes").value
  };
  saveData(); renderAll();
  alert("Paramètres enregistrés.");
});
document.getElementById("exportData").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(DATA, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `suivi-consultant-${new Date().toISOString().slice(0,10)}.json`;
  a.click();
});
document.getElementById("importDataBtn").addEventListener("click", () => document.getElementById("importData").click());
document.getElementById("importData").addEventListener("change", e => {
  const f = e.target.files[0];
  if (!f) return;
  const r = new FileReader();
  r.onload = ev => {
    try {
      DATA = JSON.parse(ev.target.result);
      saveData(); loadSettingsForm(); renderAll();
      alert("Données importées.");
    } catch (err) { alert("Fichier invalide."); }
  };
  r.readAsText(f);
});
document.getElementById("resetData").addEventListener("click", () => {
  if (confirm("Effacer toutes les données ? Cette action est irréversible.")) {
    localStorage.removeItem(STORE_KEY);
    DATA = loadData(); loadSettingsForm(); renderAll();
  }
});

// ---------- UTIL ----------
function esc(s) { return String(s||"").replace(/[&<>"']/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c])); }

function renderAll() {
  renderDashboard();
  renderCalendar();
  renderDeliverables();
  renderTasks();
  renderLeaves();
  renderDisbursements();
}

// ---------- INIT ----------
loadSettingsForm();
renderAll();
