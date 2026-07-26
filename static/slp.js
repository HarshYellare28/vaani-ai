// Vaani — clinician view. Pick a patient, assign today's practice set, review
// every attempt with both transcripts (what scored it vs what they actually
// said). No auth wired yet — this page is reachable directly at /slp.html.

const $ = (id) => document.getElementById(id);

function escapeHtml(s) {
  return (s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

function applyTheme(mode) {
  document.documentElement.dataset.theme = mode;
  $("theme-icon").setAttribute("href", mode === "dark" ? "#i-sun" : "#i-moon");
  localStorage.setItem("vaani_theme", mode);
}
function toggleTheme() {
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
}

const state = { selectedPatientId: null };

async function init() {
  applyTheme(localStorage.getItem("vaani_theme")
    || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  $("theme-btn").onclick = toggleTheme;
  $("assign-btn").onclick = onAssign;
  for (const el of document.querySelectorAll('input[name="assign-mode"]'))
    el.onchange = applyModeVisibility;
  applyModeVisibility();
  await loadPatients();
}

function selectedMode() {
  return document.querySelector('input[name="assign-mode"]:checked').value;
}

// Dynamic mode has no fixed group — level is just a starting point the judge
// adapts away from. Group picker is meaningless there, so hide it.
function applyModeVisibility() {
  const dynamic = selectedMode() === "dynamic";
  $("assign-group-wrap").hidden = dynamic;
  $("assign-level-label").textContent = dynamic ? " (starting point)" : "";
}

// ── patient list ────────────────────────────────────────────────────
async function loadPatients() {
  let patients = [];
  try {
    patients = await (await fetch("/users")).json();
  } catch (e) {
    console.error("[Vaani/SLP] failed to load patients", e);
  }
  $("patient-list").innerHTML = patients.map((p) =>
    `<button class="patient-item" data-id="${p.id}">
       <svg class="ico" aria-hidden="true"><use href="#i-user"></use></svg>
       <span>${escapeHtml(p.name)}</span>
     </button>`
  ).join("") || `<p class="subhead">No patients enrolled.</p>`;
  for (const el of document.querySelectorAll(".patient-item"))
    el.onclick = () => selectPatient(Number(el.dataset.id), el.querySelector("span").textContent);
}

async function selectPatient(id, name) {
  state.selectedPatientId = id;
  for (const el of document.querySelectorAll(".patient-item"))
    el.classList.toggle("active", Number(el.dataset.id) === id);

  $("slp-empty").hidden = true;
  $("slp-patient-view").hidden = false;
  $("slp-patient-name").textContent = name;

  await loadLanguageOptions();
  await loadCurrentAssignment();
  await loadAttempts();
}

// ── assignment form (cascading language → level → group) ──────────────
async function loadLanguageOptions() {
  const langs = await (await fetch("/languages")).json();
  $("assign-language").innerHTML = langs.map((l) =>
    `<option value="${l.language}">${l.language} — ${l.word_count} words</option>`
  ).join("");
  $("assign-language").onchange = loadLevelOptions;
  await loadLevelOptions();
}

async function loadLevelOptions() {
  const language = $("assign-language").value;
  const levels = await (await fetch(`/levels?language=${encodeURIComponent(language)}`)).json();
  $("assign-level").innerHTML = levels.map((l) =>
    `<option value="${l.level}">Level ${l.level} — ${l.word_count} words</option>`
  ).join("");
  $("assign-level").onchange = loadGroupOptions;
  await loadGroupOptions();
}

async function loadGroupOptions() {
  const language = $("assign-language").value;
  const level = $("assign-level").value;
  const groups = await (await fetch(
    `/groups?language=${encodeURIComponent(language)}&level=${level}&user_id=${state.selectedPatientId}`
  )).json();
  $("assign-group").innerHTML = groups.map((g) =>
    `<option value="${g.group_num}">Group ${g.group_num} — ${g.words_correct}/${g.word_count} done</option>`
  ).join("");
}

async function onAssign() {
  if (!state.selectedPatientId) return;
  const form = new FormData();
  form.append("user_id", state.selectedPatientId);
  form.append("language", $("assign-language").value);
  form.append("level", $("assign-level").value);
  form.append("group_num", $("assign-group").value || "1");  // ignored in dynamic mode, still required
  form.append("mode", selectedMode());
  await fetch("/assign", { method: "POST", body: form });
  await loadCurrentAssignment();
}

async function loadCurrentAssignment() {
  const a = await (await fetch(`/assignment?user_id=${state.selectedPatientId}`)).json();
  if (!a || !a.language) {
    $("assign-current").textContent = "No assignment yet — patient sees a wait screen until you assign one.";
    return;
  }
  const when = `(set ${new Date(a.assigned_at).toLocaleString()})`;
  $("assign-current").textContent = a.mode === "dynamic"
    ? `Currently assigned: ${a.language}, dynamic mode, starting near level ${a.level} ${when}`
    : `Currently assigned: ${a.language}, level ${a.level}, group ${a.group_num} ${when}`;
}

// ── attempts (both transcripts) ─────────────────────────────────────
async function loadAttempts() {
  $("attempts-table-wrap").innerHTML = `<div class="center"><span class="spinner"></span></div>`;
  const attempts = await (await fetch(`/patients/${state.selectedPatientId}/attempts`)).json();
  if (!attempts.length) {
    $("attempts-table-wrap").innerHTML = `<p class="subhead">No attempts yet.</p>`;
    return;
  }
  const badgeClass = (label) =>
    label === "correct" ? "correct" : label === "no_speech" ? "no_speech" : "incorrect";
  const cell = (v) => v ? escapeHtml(v) : `<span class="muted">—</span>`;

  $("attempts-table-wrap").innerHTML = `
    <table class="attempts-table">
      <thead>
        <tr><th>Time</th><th>Mode</th><th>Target</th><th>Heard</th><th>Verbatim</th><th>Result</th><th>Match</th><th>Judge note</th></tr>
      </thead>
      <tbody>
        ${attempts.map((a) => `
          <tr>
            <td class="muted">${new Date(a.created_at).toLocaleString()}</td>
            <td class="muted">${a.mode || "static"}</td>
            <td>${escapeHtml(a.target_word)}</td>
            <td>${cell(a.transcript)}</td>
            <td class="${a.transcript_verbatim !== a.transcript ? "verbatim-diff" : ""}">${cell(a.transcript_verbatim)}</td>
            <td><span class="badge ${badgeClass(a.result_label)}">${a.result_label}</span></td>
            <td>${Math.round((a.similarity || 0) * 100)}%</td>
            <td class="muted">${a.judge_error_type ? `<strong>${escapeHtml(a.judge_error_type)}</strong> — ${cell(a.judge_note)}` : "—"}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

init();
