// Vaani — front-end for the static drill. Fully localized: the whole UI flips
// to the chosen practice language, driven by the /i18n locale table. Sarvam
// (bulbul:v3) speaks every language, including English — no browser TTS.

const $ = (id) => document.getElementById(id);

window.addEventListener("error", (e) =>
  console.error("[Vaani] error:", e.message, e.error));
window.addEventListener("unhandledrejection", (e) =>
  console.error("[Vaani] rejection:", e.reason));

// If the passcode cookie ever expires, every API call 401s — bounce to login.
const _fetch = window.fetch.bind(window);
window.fetch = async (...args) => {
  const res = await _fetch(...args);
  if (res.status === 401) { window.location.href = "/login"; }
  return res;
};

// ── localization ─────────────────────────────────────────────────────
let I18N = {};            // full locale table from /i18n
let locale = "en";        // current UI locale (base lang: 'en','hi',…)

const FALLBACK = "en";
const LEVEL_ICON = { 1: "level-1", 2: "level-2", 3: "level-3" };
const BADGE_ICON = { correct: "check", incorrect: "undo", no_speech: "mute" };

// Reference into the <symbol> sprite at the top of index.html. Emoji used to
// stand in for icons here, which meant every OS drew the UI differently.
const icon = (name, cls = "ico") =>
  `<svg class="${cls}" aria-hidden="true"><use href="#i-${name}"></use></svg>`;

function toLocale(code) {
  const base = (code || "").split("-")[0].toLowerCase();
  return I18N[base] ? base : FALLBACK;
}
function t(key) {
  return (I18N[locale]?.ui?.[key]) ?? (I18N[FALLBACK]?.ui?.[key]) ?? key;
}
function meta(loc = locale) { return I18N[loc]?.meta || {}; }
function levelInfo(n) {
  return (I18N[locale]?.levels?.[n]) ?? (I18N[FALLBACK]?.levels?.[n]) ?? { name: `Level ${n}`, desc: "" };
}
function badgeText(label) {
  return (I18N[locale]?.badges?.[label]) ?? (I18N[FALLBACK]?.badges?.[label]) ?? label;
}

// Bilingual category strings ("People / ಜನರು") → the segment for this locale.
// The native half is matched across the whole Indic range (Devanagari through
// Malayalam, mirroring textutils._is_indic) rather than Devanagari alone, so
// every Indic locale gets its own script instead of falling back to English.
function localizeCategory(cat) {
  if (!cat || !cat.includes("/")) return cat || "";
  const parts = cat.split("/").map((s) => s.trim());
  const isIndic = (s) => /[ऀ-ൿ]/.test(s);
  const native = parts.find(isIndic);
  const latin = parts.find((p) => !isIndic(p));
  return locale === "en" ? (latin || native || cat) : (native || latin || cat);
}

function applyLocale(loc) {
  locale = I18N[loc] ? loc : FALLBACK;
  const m = meta();
  document.documentElement.lang = locale;
  document.documentElement.dir = m.dir || "ltr";
  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.textContent = t(el.dataset.i18n);
  }
}

// ── theme ────────────────────────────────────────────────────────────
// Light surfaces wash out badly under a projector, which is where this gets
// demoed. Defaults to the OS preference, then remembers the explicit choice.
function applyTheme(mode) {
  document.documentElement.dataset.theme = mode;
  $("theme-icon").setAttribute("href", mode === "dark" ? "#i-sun" : "#i-moon");
  document.querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", mode === "dark" ? "#0a0e18" : "#f4f6fb");
  localStorage.setItem("vaani_theme", mode);
}

function toggleTheme() {
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
}

// ── state ────────────────────────────────────────────────────────────
const state = {
  userId: null, userName: null,
  mode: "static",  // "static" | "dynamic" — from the SLP's assignment
  language: null, level: null, group: null,
  groupScores: [], words: [], index: 0,
  sessionId: null, recorder: null, recording: false,
};

// Dynamic mode only: auto-advance after a correct attempt, cleared on any
// manual navigation so it can never fire against the wrong word.
let autoAdvanceTimer = null;
const AUTO_ADVANCE_MS = 2000;

// ── audio helpers ───────────────────────────────────────────────────
function playBlob(blob) {
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.onended = () => URL.revokeObjectURL(url);
  audio.play().catch(() => {});
}
function playBase64Wav(b64) {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  playBlob(new Blob([bytes], { type: "audio/wav" }));
}

// ── live mic waveform ────────────────────────────────────────────────
// Reads the frames WavRecorder already posts to the main thread, so there is no
// second audio graph. One bar per frame, height = RMS: steadier to look at than
// raw samples, and it makes the long pauses of aphasic speech legible rather
// than looking like the app has frozen.
const WAVE_BARS = 54;
const wave = { bars: [], raf: null };

function waveStart() {
  const c = $("wave");
  if (!c) return;
  wave.bars = new Array(WAVE_BARS).fill(0);
  c.hidden = false;
  const draw = () => {
    waveDraw(c);
    wave.raf = requestAnimationFrame(draw);
  };
  draw();
}

function wavePush(frame) {
  let sum = 0;
  for (let i = 0; i < frame.length; i++) sum += frame[i] * frame[i];
  // ×3.4 lifts normal speaking level to roughly full height at typical mic gain.
  wave.bars.push(Math.min(1, Math.sqrt(sum / frame.length) * 3.4));
  if (wave.bars.length > WAVE_BARS) wave.bars.shift();
}

function waveDraw(c) {
  const dpr = window.devicePixelRatio || 1;
  const w = c.clientWidth, h = c.clientHeight;
  if (c.width !== Math.round(w * dpr)) {       // resize only when it changes
    c.width = Math.round(w * dpr);
    c.height = Math.round(h * dpr);
  }
  const g = c.getContext("2d");
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);

  const style = getComputedStyle(document.documentElement);
  const grad = g.createLinearGradient(0, 0, w, 0);
  grad.addColorStop(0, style.getPropertyValue("--primary").trim() || "#5b53f0");
  grad.addColorStop(1, style.getPropertyValue("--accent").trim() || "#0fae9e");
  g.fillStyle = grad;

  const gap = 3;
  const bw = Math.max(2, (w - gap * (WAVE_BARS - 1)) / WAVE_BARS);
  const mid = h / 2;
  const rounded = typeof g.roundRect === "function";  // Safari <16.4 lacks it
  for (let i = 0; i < wave.bars.length; i++) {
    const bh = Math.max(2, wave.bars[i] * (h - 6));
    const x = i * (bw + gap);
    if (rounded) {
      g.beginPath();
      g.roundRect(x, mid - bh / 2, bw, bh, bw / 2);
      g.fill();
    } else {
      g.fillRect(x, mid - bh / 2, bw, bh);
    }
  }
}

function waveStop() {
  if (wave.raf) cancelAnimationFrame(wave.raf);
  wave.raf = null;
  const c = $("wave");
  if (c) c.hidden = true;
}

// ── screen + menu management ─────────────────────────────────────────
function showScreen(name) {
  for (const s of ["user", "unassigned", "drill", "summary"])
    $(`screen-${s}`).hidden = s !== name;
  const onDrill = name === "drill";
  $("patient-chip").hidden   = !onDrill;
  $("level-chip-bar").hidden = !onDrill;
  $("menu-btn").hidden       = !onDrill;
  // menu items — no change-language/change-level: the SLP owns the
  // assignment, the patient never picks.
  $("restart-btn").hidden      = !onDrill;
  $("end-btn").hidden          = !onDrill;
  closeMenu();
}

function openMenu()  { $("menu").hidden = false; $("menu-btn").setAttribute("aria-expanded", "true"); }
function closeMenu() { $("menu").hidden = true;  $("menu-btn").setAttribute("aria-expanded", "false"); }
function toggleMenu() { $("menu").hidden ? openMenu() : closeMenu(); }

// ── lifecycle ───────────────────────────────────────────────────────
async function init() {
  applyTheme(localStorage.getItem("vaani_theme")
    || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
  I18N = await (await fetch("/i18n")).json();
  applyLocale(toLocale(navigator.language));  // device locale for pre-selection
  wireButtons();
  await renderUsers();
}

window.addEventListener("beforeunload", () => {
  if (state.sessionId) navigator.sendBeacon(`/session/${state.sessionId}/end`);
});

// ── user screen ─────────────────────────────────────────────────────
// The SLP picks an already-enrolled patient from a dropdown — no typing, no
// self-signup. Patients are seeded server-side (vaani/db.py); "Add patient"
// is a fallback for enrolling someone new mid-session, not the primary flow.
async function renderUsers() {
  showScreen("user");
  let users = [];
  try {
    users = await (await fetch("/users")).json();
  } catch (e) {
    console.error("[Vaani] failed to load patients", e);
  }
  populateUserSelect(users);
}

function populateUserSelect(users) {
  $("user-loading").hidden = true;
  const select = $("user-select");
  select.innerHTML = users.map((u) =>
    `<option value="${u.id}">${u.name}</option>`
  ).join("");
  select.hidden = users.length === 0;
  $("user-continue-btn").hidden = users.length === 0;

  const storedId = parseInt(localStorage.getItem("vaani_user_id") || "0");
  if (users.some((u) => u.id === storedId)) select.value = storedId;
}

function continueWithSelectedUser() {
  const opt = $("user-select").selectedOptions[0];
  if (!opt) return;
  chooseUser(Number(opt.value), opt.textContent);
}

async function chooseUser(id, name) {
  state.userId = id;
  state.userName = name;
  localStorage.setItem("vaani_user_id", id);
  $("patient-chip").innerHTML = `${icon("user")}<span></span>`;
  $("patient-chip").querySelector("span").textContent = name;
  await loadAssignmentAndStart();
}

// ── assignment-driven start ────────────────────────────────────────
// No language/level picker for the patient — the SLP sets what they practice
// today (POST /assign from /slp.html). This just plays back whatever's there.
async function loadAssignmentAndStart() {
  let a = null;
  try {
    a = await (await fetch(`/assignment?user_id=${state.userId}`)).json();
  } catch (e) {
    console.error("[Vaani] failed to load assignment", e);
  }
  if (!a || !a.language) {
    showScreen("unassigned");
    return;
  }
  state.mode = a.mode || "static";
  state.language = a.language;
  state.level = a.level;
  applyLocale(toLocale(a.language));
  const info = levelInfo(a.level);
  $("level-chip-bar").innerHTML = `${icon(LEVEL_ICON[a.level] || "levels")}<span></span>`;
  $("level-chip-bar").querySelector("span").textContent =
    state.mode === "dynamic" ? "Dynamic" : info.name;

  if (state.mode === "dynamic") {
    await startDynamicSession(a);
  } else {
    await refreshGroupScores();
    await chooseGroup(a.group_num);
  }
}

// Dynamic mode has no fixed word list — the server picks a first word at
// session start, and each /evaluate response picks the next one (judged by
// the LLM against the verbatim transcript; see vaani/judge.py). The patient
// app just appends whatever it's given and walks forward.
async function startDynamicSession(a) {
  await endActiveSession();
  const form = new FormData();
  form.append("language", state.language);
  form.append("level", state.level);
  form.append("user_id", state.userId);
  form.append("group_num", a.group_num);
  const r = await (await fetch("/session/start", { method: "POST", body: form })).json();
  state.sessionId = r.session_id;

  if (!r.first_word) {
    // Corpus exhausted for this language/patient — rare (English has 100
    // words, Hindi 900), but don't leave the patient stuck on a spinner.
    showScreen("unassigned");
    return;
  }
  state.words = [r.first_word];
  state.index = 0;
  showScreen("drill");
  const sidebar = document.querySelector(".group-sidebar");
  if (sidebar) sidebar.hidden = true;
  renderWord();
}

async function addUser() {
  const name = prompt(t("patient_name_prompt"));
  if (!name || !name.trim()) return;
  const form = new FormData();
  form.append("name", name.trim());
  const res = await (await fetch("/users", { method: "POST", body: form })).json();
  await chooseUser(res.user_id, res.name);
}

// ── group sidebar ───────────────────────────────────────────────────
async function refreshGroupScores() {
  state.groupScores = await (await fetch(
    `/groups?language=${encodeURIComponent(state.language)}&level=${state.level}&user_id=${state.userId}`
  )).json();
  renderGroupSidebar();
}

function renderGroupSidebar() {
  const container = $("group-list");
  if (!container) return;
  // A single group makes the sidebar a heading over one full-width chip that
  // conveys nothing. On a phone it stacks above the card and pushes the target
  // word toward the fold, so drop it until there is a choice to make.
  const sidebar = document.querySelector(".group-sidebar");
  if (sidebar) sidebar.hidden = state.groupScores.length < 2;
  container.innerHTML = state.groupScores.map((g) => {
    const isActive = g.group_num === state.group;
    const pct = g.word_count ? Math.round((g.words_correct / g.word_count) * 100) : 0;
    const scoreClass = pct === 100 ? "score-done" : pct > 0 ? "score-partial" : "score-zero";
    return `<button class="group-item${isActive ? " active" : ""}" data-group="${g.group_num}">
      <div class="group-item-row">
        <span class="group-name">${t("group")} ${g.group_num}</span>
        <span class="group-score ${scoreClass}">${g.words_correct}/${g.word_count}</span>
      </div>
      <div class="group-bar"><div class="group-bar-fill" style="width:${pct}%"></div></div>
    </button>`;
  }).join("");
  for (const el of document.querySelectorAll(".group-item"))
    el.onclick = () => chooseGroup(Number(el.dataset.group));
}

async function chooseGroup(groupNum) {
  await endActiveSession();
  state.mode = "static";
  state.group = groupNum;
  state.index = 0;

  const raw = await (await fetch(
    `/words?language=${encodeURIComponent(state.language)}&level=${state.level}&group=${groupNum}`
  )).json();
  for (let i = raw.length - 1; i > 0; i--) {           // Fisher-Yates shuffle
    const j = Math.floor(Math.random() * (i + 1));
    [raw[i], raw[j]] = [raw[j], raw[i]];
  }
  state.words = raw;

  showScreen("drill");
  renderGroupSidebar();
  renderWord();
}

function currentWord() { return state.words[state.index]; }

function renderWord() {
  clearTimeout(autoAdvanceTimer);
  const w = currentWord();
  if (state.mode === "dynamic") {
    // No fixed total to count against — the judge extends the list one word
    // at a time, so "N / total" would just show a number trailing itself.
    $("progress").textContent = `${t("word")} ${state.index + 1}`;
    $("level-chip").textContent = `${t("level")} ${w.level}`;
    $("progress-fill").style.width = "0%";
  } else {
    $("progress").textContent = `${t("word")} ${state.index + 1} / ${state.words.length}`;
    $("level-chip").textContent = `${t("level")} ${w.level} · ${t("group")} ${state.group}`;
    $("progress-fill").style.width = `${(state.index / state.words.length) * 100}%`;
  }
  const wd = $("word-display");
  wd.textContent = w.text;
  wd.lang = (w.language || "").split("-")[0];
  wd.style.animation = "none";   // replay the entrance on every advance;
  void wd.offsetWidth;           // reading offsetWidth forces the reflow
  wd.style.animation = "";
  $("word-gloss").textContent = w.display || "";
  $("word-category").textContent = localizeCategory(w.category);
  $("result").hidden = true;
  $("status").textContent = "";
  $("listen-btn").disabled = false;
  $("record-btn").disabled = false;
}

// ── session ─────────────────────────────────────────────────────────
async function ensureSession() {
  if (state.sessionId) return state.sessionId;
  const form = new FormData();
  form.append("language", state.language);
  if (state.level  != null) form.append("level",     state.level);
  if (state.userId != null) form.append("user_id",   state.userId);
  if (state.group  != null) form.append("group_num", state.group);
  const r = await (await fetch("/session/start", { method: "POST", body: form })).json();
  state.sessionId = r.session_id;
  return state.sessionId;
}

// ── drill actions ───────────────────────────────────────────────────
async function playPrompt() {
  const w = currentWord();
  $("status").textContent = t("playing");
  const form = new FormData();
  form.append("word", w.text);
  form.append("lang", w.language);
  try {
    const res = await fetch("/prompt", { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    playBlob(await res.blob());
    $("status").textContent = "";
  } catch (e) {
    console.error(e);
    $("status").textContent = t("audio_error");
  }
}

async function toggleRecord() {
  if (!state.recording) {
    try {
      state.recorder = new WavRecorder(16000, wavePush);
      await state.recorder.start();
    } catch (e) {
      console.error("[Vaani] mic error", e);
      $("status").textContent = t("allow_mic");
      return;
    }
    state.recording = true;
    $("record-btn").classList.add("rec");
    $("record-icon").setAttribute("href", "#i-stop");
    $("record-btn").querySelector(".record-label").textContent = t("stop");
    $("status").textContent = t("recording_hint");
    waveStart();
  } else {
    let blob;
    try { blob = await state.recorder.stop(); }
    catch (e) { console.error(e); state.recording = false; waveStop(); return; }
    state.recording = false;
    waveStop();
    $("record-btn").classList.remove("rec");
    $("record-icon").setAttribute("href", "#i-mic");
    $("record-btn").querySelector(".record-label").textContent = t("speak");
    if (!blob.capturedSeconds || blob.capturedSeconds < 0.3) {
      $("status").textContent = t("no_audio");
      return;
    }
    $("record-btn").disabled = true;
    $("listen-btn").disabled = true;
    $("status").innerHTML = `<span class="spinner"></span> ${t("checking")}`;
    await submitAttempt(blob);
  }
}

async function submitAttempt(blob) {
  const w = currentWord();
  try {
    await ensureSession();
    const form = new FormData();
    form.append("word",       w.text);
    form.append("session_id", state.sessionId);
    form.append("language",   w.language);
    form.append("word_id",    w.id);
    form.append("attempt",    blob, "attempt.wav");
    const res = await fetch("/evaluate", { method: "POST", body: form });
    if (!res.ok) throw new Error(await res.text());
    renderResult(await res.json());
  } catch (e) {
    console.error(e);
    $("status").textContent = t("error_retry");
    $("record-btn").disabled = false;
    $("listen-btn").disabled = false;
  }
}

function renderResult(d) {
  $("status").textContent = "";
  const label = d.result_label in BADGE_ICON ? d.result_label : "incorrect";
  $("result-badge").className = `badge ${label}`;
  $("result-badge").innerHTML = `${icon(BADGE_ICON[label])}<span></span>`;
  $("result-badge").querySelector("span").textContent = badgeText(label);

  // Show whichever transcript actually scored the attempt — static mode
  // scores on transcribe, dynamic mode scores on verbatim (see drill.py).
  // Showing the other one is worse than showing nothing: a static/dynamic
  // ASR disagreement (real and observed — e.g. transcribe hearing "Nice" for
  // verbatim's correct "Knife") makes a correct verdict look like nonsense.
  const heard = $("heard-val");
  const heardText = state.mode === "dynamic" ? d.transcript_verbatim : d.transcript;
  if (heardText && heardText.trim()) {
    heard.textContent = heardText;
    heard.className = "val";
  } else {
    heard.textContent = t("nothing");
    heard.className = "val empty";
  }

  $("result").hidden = false;   // unhide before animating, or the bar has no
                                // layout to transition from and snaps instead
  animateScore(Math.round((d.similarity || 0) * 100), d.correct);

  $("dur-chip").textContent = `${t("duration")}: ${(d.audio_duration_sec || 0).toFixed(1)}s`;
  const prob = d.language_probability != null
    ? ` ${Math.round(d.language_probability * 100)}%` : "";
  $("detect-chip").innerHTML = `${icon("globe")}<span></span>`;
  $("detect-chip").querySelector("span").textContent =
    d.language_detected ? `${d.language_detected}${prob}` : "";
  $("detect-chip").hidden = !d.language_detected;

  $("feedback-text").textContent = d.decision.feedback_text;

  // Dynamic mode's retry cue — the cueing hierarchy from JUDGE.md, generated
  // fresh per attempt (phonemic cue for a semantic error, a slow syllable
  // model for a phonemic error, etc). Empty when the judge says correct.
  const cueEl = $("cue-text");
  cueEl.hidden = !(state.mode === "dynamic" && d.cue_hint);
  if (!cueEl.hidden) cueEl.textContent = d.cue_hint;

  if (state.mode === "dynamic") {
    // The judge already picked what's next regardless of correctness — that
    // IS the adaptive behavior, so don't gate "Next" on getting it right.
    if (d.next_word) state.words.push(d.next_word);
    $("next-btn").hidden = !d.next_word;  // no candidates left → let skip/end handle it
    // Correct → the judge's adaptation continues on its own; a deliberate
    // pause (not a countdown, nothing visibly ticking) rather than requiring
    // a tap, so the adaptive loop reads as continuous. Incorrect still waits
    // for the patient — they need the cue and a real retry, never rushed.
    clearTimeout(autoAdvanceTimer);
    if (d.correct && d.next_word) {
      autoAdvanceTimer = setTimeout(() => {
        if (!$("screen-drill").hidden) nextWord();
      }, AUTO_ADVANCE_MS);
    }
  } else {
    $("next-btn").hidden = !d.correct;
    if (d.correct) refreshGroupScores();
  }

  if (d.feedback_audio_wav_b64) playBase64Wav(d.feedback_audio_wav_b64);
}

// The judge's verdict is the point of the product, so let it land as motion
// rather than appearing pre-filled: bar and number run together over ~700ms.
//
// The score is written synchronously FIRST and only rewound inside a rAF
// callback. requestAnimationFrame does not fire in a page the browser isn't
// painting (backgrounded tab, throttled renderer), and a meter frozen at 0%
// misreports the judge — so the honest value has to be the state we fall back
// to, never the starting point. A timer backstops a run that dies mid-flight.
const SCORE_MS = 700;

function animateScore(pct, correct) {
  const fill = $("sim-fill"), label = $("sim-pct");
  fill.className = "fill " + (correct ? "good" : "bad");
  const settle = () => { fill.style.transition = ""; fill.style.width = `${pct}%`; label.textContent = `${pct}%`; };
  settle();

  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  clearTimeout(animateScore._guard);
  requestAnimationFrame(() => {
    fill.style.transition = "none";     // rewind without animating backwards
    fill.style.width = "0%";
    label.textContent = "0%";
    animateScore._guard = setTimeout(settle, SCORE_MS + 150);
    requestAnimationFrame(() => {
      fill.style.transition = "";
      fill.style.width = `${pct}%`;
      const t0 = performance.now();
      const step = (now) => {
        const k = Math.min(1, (now - t0) / SCORE_MS);
        label.textContent = `${Math.round(pct * (1 - Math.pow(1 - k, 3)))}%`;
        if (k < 1) requestAnimationFrame(step);
        else settle();
      };
      requestAnimationFrame(step);
    });
  });
}

// ── navigation ──────────────────────────────────────────────────────
function repeatWord() { renderWord(); }

function nextWord() {
  if (state.index < state.words.length - 1) { state.index += 1; renderWord(); }
  else endSession();
}

async function endActiveSession() {
  if (state.sessionId) await fetch(`/session/${state.sessionId}/end`, { method: "POST" });
  state.sessionId = null;
}

async function restart() {
  await endActiveSession();
  state.index = 0;
  showScreen("drill");
  renderGroupSidebar();
  renderWord();
}

async function endSession() {
  clearTimeout(autoAdvanceTimer);
  let s = { attempts: 0, correct: 0, avg_similarity: null, avg_duration: null };
  if (state.sessionId) {
    const r = await (await fetch(`/session/${state.sessionId}/end`, { method: "POST" })).json();
    s = r.summary;
    state.sessionId = null;
  }
  const acc = s.attempts ? Math.round((s.correct / s.attempts) * 100) : 0;
  const avgMatch = s.avg_similarity != null ? Math.round(s.avg_similarity * 100) + "%" : "—";
  const stat = (num, lbl) =>
    `<div class="stat"><div class="num">${num}</div><div class="lbl">${lbl}</div></div>`;
  $("summary-grid").innerHTML =
    stat(s.attempts || 0, t("attempts")) +
    stat(s.correct  || 0, t("correct")) +
    stat(`${acc}%`,       t("accuracy")) +
    stat(avgMatch,        t("avg_match"));
  showScreen("summary");
}

// ── wiring ──────────────────────────────────────────────────────────
function wireButtons() {
  $("listen-btn").onclick  = playPrompt;
  $("record-btn").onclick  = toggleRecord;
  $("repeat-btn").onclick  = repeatWord;
  $("skip-btn").onclick    = nextWord;
  $("next-btn").onclick     = nextWord;
  $("restart-btn").onclick  = () => { closeMenu(); restart(); };
  $("end-btn").onclick      = () => { closeMenu(); endSession(); };
  $("add-user-btn").onclick     = addUser;
  $("user-continue-btn").onclick = continueWithSelectedUser;
  $("check-assignment-btn").onclick = loadAssignmentAndStart;
  // Re-checks the assignment rather than just replaying the same group — the
  // SLP may have assigned something new between sessions.
  $("again-btn").onclick         = async () => { await endActiveSession(); await loadAssignmentAndStart(); };

  $("theme-btn").onclick = toggleTheme;
  $("menu-btn").onclick = (e) => { e.stopPropagation(); toggleMenu(); };
  document.addEventListener("click", (e) => {
    if (!$("menu").hidden && !e.target.closest(".menu-wrap")) closeMenu();
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMenu(); });
}

init();
