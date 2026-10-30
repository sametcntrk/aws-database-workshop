/* Mission of the Guided e-commerce app (tutorials/guided.yaml): coach marks. Turkish, 101 level.
 *
 * The page goes dark. Only the control of the current step stays lit and accepts input. A small coach card next to it says
 * what to do. A step with a `panel` has its "Perde arkası" in its own browser tab (perde.js): the click on the lit control
 * opens /guided-e-commerce-app/perde-arkasi/<n> in the one tab named "perde-arkasi" (the click is the user gesture a tab needs), and when the page makes
 * the expected Engine call this tab writes the call to localStorage "lm_perde_<n>" for that tab. A "look" step has no click:
 * its card offers a button. A step with no `panel` shows its `result` text in the small card.
 * Step fields: page, path, engines, use_case, title, why, do, target (CSS selector of the control),
 *   action: click | look | type | change,  wait: {method, path, query, body, count, any} | {click} | {change} | {value},
 *   focus (selector to light after the action), result (short text, steps with no panel), panel (perde.js).
 * State: localStorage lm_mission_v2 = {"i": step index, "done": {index: true}}. ?adim=N opens step N.
 */
(function () {
  "use strict";
  if (!window.LM || !LM.mission || !document.getElementById("mission")) return;
  const { esc, $ } = lm;
  const steps = LM.mission.steps || [];
  const BASE = LM.mode.base;
  const KEY = "lm_mission_v2";
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || { i: 0, done: {} }; } catch (e) { return { i: 0, done: {} }; } };
  const save = (st) => localStorage.setItem(KEY, JSON.stringify(st));
  let st = load();
  const asked = Number(new URLSearchParams(location.search).get("adim"));
  if (asked >= 1 && asked <= steps.length) { st.i = asked - 1; save(st); }
  st.i = Math.max(0, Math.min(st.i || 0, steps.length - 1));
  let step = steps[st.i];
  const go = (s) => { window.location.href = BASE + s.path; };
  if (step.page !== LM.page.id) { go(step); return; }          // a step on another page: go there

  const ENGINE_LABEL = { docdb: "DocumentDB", opensearch: "OpenSearch", neptune: "Neptune", dynamodb: "DynamoDB", aurora: "Aurora PostgreSQL",
    elasticache: "ElastiCache (Valkey)", keyspaces: "Keyspaces", s3: "S3", redshift: "Redshift", influxdb: "Timestream for InfluxDB" };
  let last, actionDone, phase, calls, w, seen, from = 0, tabOpen = false;

  /* ---------- Top bar: progress only */
  const bar = () => { $("#mission").innerHTML = `<div class="mission-head"><span class="tutor-badge">Görev</span><span class="mission-step">Adım ${st.i + 1} / ${steps.length}</span>
    <ol class="mission-dots" aria-hidden="true">${steps.map((_, k) => `<li class="${k < st.i ? "done" : k === st.i ? "now" : ""}"></li>`).join("")}</ol>
    <span class="mission-hint">Aydınlık kontrolü ve yanındaki kartı takip et.</span></div>`; };

  /* ---------- Dark layer with a hole, and the small coach card */
  const layer = document.createElement("div");
  layer.className = "coach-layer";
  layer.innerHTML = `<div class="coach-block" data-b="t"></div><div class="coach-block" data-b="l"></div><div class="coach-block" data-b="r"></div>
    <div class="coach-block" data-b="b"></div><div class="coach-ring"></div><div class="coach-cover" hidden></div>`;
  const card = document.createElement("section");
  card.className = "coach-card";
  card.setAttribute("role", "dialog");
  card.setAttribute("aria-live", "polite");
  document.body.append(layer, card);
  const ring = $(".coach-ring", layer), cover = $(".coach-cover", layer);
  const blocks = Object.fromEntries([...layer.querySelectorAll(".coach-block")].map((b) => [b.dataset.b, b]));

  const lit = () => document.querySelector(phase === "look-result" && step.focus ? step.focus : step.target) || document.querySelector(step.target);
  const PAD = 8;
  function place() {
    const el = lit();
    if (!el) { Object.values(blocks).forEach((b) => Object.assign(b.style, { top: 0, left: 0, width: "100vw", height: "100vh" })); return; }
    const r = el.getBoundingClientRect();
    const t = Math.max(0, r.top - PAD), l = Math.max(0, r.left - PAD), w = r.width + 2 * PAD, h = r.height + 2 * PAD;
    Object.assign(blocks.t.style, { top: 0, left: 0, width: "100vw", height: `${t}px` });
    Object.assign(blocks.b.style, { top: `${t + h}px`, left: 0, width: "100vw", height: `calc(100vh - ${t + h}px)` });
    Object.assign(blocks.l.style, { top: `${t}px`, left: 0, width: `${l}px`, height: `${h}px` });
    Object.assign(blocks.r.style, { top: `${t}px`, left: `${l + w}px`, width: `calc(100vw - ${l + w}px)`, height: `${h}px` });
    Object.assign(ring.style, { top: `${t}px`, left: `${l}px`, width: `${w}px`, height: `${h}px` });
    Object.assign(cover.style, { top: `${t}px`, left: `${l}px`, width: `${w}px`, height: `${h}px` });
    if (card.hidden) return;
    // The card goes below the lit control, or above it, or at the side: wherever it fits in the window.
    const cw = Math.min(440, window.innerWidth - 24), ch = card.offsetHeight;
    let top = t + h + 12, left = Math.min(Math.max(12, l), window.innerWidth - cw - 12);
    if (top + ch > window.innerHeight - 12) top = t - ch - 12;
    if (top < 12) { top = Math.max(12, Math.min(window.innerHeight - ch - 12, t)); left = l + w + 12 + cw < window.innerWidth ? l + w + 12 : Math.max(12, l - cw - 12); }
    top = Math.max(12, Math.min(top, window.innerHeight - ch - 12));   // the card always stays in the window
    if (top < t + h && top + ch > t && left < l + w && left + cw > l) left = window.innerWidth - cw - 12;   // over the lit part: to the right edge, where shop rows are empty
    Object.assign(card.style, { top: `${top}px`, left: `${left}px`, width: `${cw}px` });
  }
  let raf = 0;
  const schedule = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; place(); }); };
  addEventListener("scroll", schedule, { passive: true });
  addEventListener("resize", schedule);
  new ResizeObserver(schedule).observe(document.body);
  function scrollToLit() {
    const el = lit();
    if (el) el.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
    setTimeout(place, 450);
  }

  /* ---------- The "Perde arkası" tab of the step */
  const tabUrl = (fresh) => `${BASE}/perde-arkasi/${st.i + 1}${fresh ? `?t=${Date.now()}` : ""}`;
  const openTab = (fresh) => { tabOpen = !!window.open(tabUrl(fresh), "perde-arkasi"); };   // one tab for the whole mission: each step loads into it
  function handOver() {                                         // what the tab needs: the call of the lit part and the page's calls
    try {
      const slim = (c) => c && { method: c.method, path: c.path, query: c.query, body: c.body, ok: c.ok, data: c.data, entries: c.entries, ms: c.ms, label: c.label };
      localStorage.setItem(`lm_perde_${st.i + 1}`, JSON.stringify({ at: Date.now(), trig: slim(calls[from]), page: lm.calls.map(slim) }));
    } catch (e) { /* storage full: the tab shows the parts that need no data */ }
  }

  /* ---------- The small card */
  function chips() { return (step.engines || []).map((e) => `<span class="chip eng-${e}">${esc(ENGINE_LABEL[e] || e)}</span>`).join(""); }
  function nav() {
    return `<button type="button" class="quiet" data-c="restart">Baştan başla</button><span></span>
      <button type="button" data-c="back" ${st.i === 0 ? "disabled" : ""}>Geri</button>
      <button type="button" class="primary" data-c="next" ${actionDone ? "" : "disabled"}>${last ? "Görevi bitir" : "İleri"}</button>`;
  }
  function wire(root) {
    root.querySelector("[data-c=next]").addEventListener("click", next);
    root.querySelector("[data-c=back]").addEventListener("click", () => { st.i -= 1; save(st); go(steps[st.i]); });
    root.querySelector("[data-c=restart]").addEventListener("click", () => { save({ i: 0, done: {} }); go(steps[0]); });
  }
  function shortResult() {
    const after = calls.slice(from).filter((c) => !c.background).slice(0, 1);   // only the call of the lit part
    const lines = after.flatMap((c) => (c.entries || []).slice(0, 3).map((e) =>
      `<li><b>${esc(e.op)}</b> <span>${esc(e.engine || "")} · ${e.ms} ms${e.items !== undefined ? ` · ${e.items} kayıt` : ""}${e.capacity ? ` · ${esc(String(e.capacity).replace(/\s*\(.*\)$/, ""))}` : ""}</span></li>`)).join("");
    return `<div class="coach-bts"><b>Perde arkası</b><p>${esc(step.result || "")}</p>${lines ? `<ol>${lines}</ol>` : ""}</div>`;
  }
  function tabBox() {
    return `<div class="coach-bts coach-tab"><b>Perde arkası</b><p>${tabOpen
      ? "Bu adımın perde arkası \"Perde arkası\" sekmesinde açıldı: simülasyon, gerçek ölçümler, komutun açıklaması ve isteğin yolu orada. Okuduktan sonra bu sekmeye dön ve İleri'ye bas."
      : "Bu adımın perde arkası ayrı bir \"Perde arkası\" sekmesinde açılır (bütün adımlar aynı sekmeyi kullanır): simülasyon, gerçek ölçümler, komutun açıklaması ve isteğin yolu. Okuduktan sonra bu sekmeye dön ve İleri'ye bas."}</p>
      <button type="button" class="coach-tab-btn" data-c="tab">${tabOpen ? "Perde arkası sekmesine git" : "Perde arkasını aç"} ↗</button></div>`;
  }
  function renderCard() {
    card.innerHTML = `<header><span>${chips()}${step.use_case ? `<em>${esc(step.use_case)}</em>` : ""}</span><small>${st.i + 1} / ${steps.length}</small></header>
      <h2>${esc(step.title)}</h2>
      ${actionDone ? "" : `<p>${esc(step.why || "")}</p>`}
      <p class="coach-do ${actionDone ? "done" : ""}">${esc(step.do || "Aydınlık bölüme bak, sonra İleri'ye bas.")}</p>
      ${actionDone ? (step.panel ? tabBox() : shortResult()) : ""}
      <footer>${nav()}</footer>`;
    wire(card);
    const tb = card.querySelector("[data-c=tab]");
    if (tb) tb.addEventListener("click", () => { openTab(false); renderCard(); schedule(); });
  }
  function render() {
    renderCard();
    cover.hidden = !(step.action === "look" || actionDone);       // after the action, the lit part is for reading only
    schedule();
  }
  function complete() {
    if (actionDone) return;
    actionDone = true;
    st.done[st.i] = true; save(st);
    if (step.panel) handOver();
    if (step.focus) phase = "look-result";
    render();
    scrollToLit();
    setTimeout(scrollToLit, 1200);                               // parts of the page that load later can move the lit part
  }
  function next() {
    if (last) { save({ i: 0, done: {}, finished: true }); window.location.href = LM.mission.finish_url || "/"; return; }
    st.i += 1; save(st);
    const n = steps[st.i];
    if (n.page === LM.page.id && n.path === step.path) begin(); else go(n);   // same page: continue in place, the page keeps its state
  }

  /* ---------- Wait for the action */
  function matches(c) {
    if (!w.path || (!c.ok && !w.any)) return false;
    if (w.method && w.method !== c.method) return false;
    if (!(w.path.endsWith("*") ? c.path.startsWith(w.path.slice(0, -1)) : c.path === w.path)) return false;
    const same = (got, want) => (want === "*" ? got !== undefined && got !== "" : String(got) === String(want));
    for (const [k, v] of Object.entries(w.query || {})) if (!same(c.query[k], v)) return false;
    for (const [k, v] of Object.entries(w.body || {})) if (!same(c.body[k], v)) return false;
    return true;
  }
  function onCall(c) {
    calls.push(c);
    if (!actionDone && matches(c) && ++seen >= (w.count || 1)) { from = calls.length - 1; complete(); }
    else if (actionDone && !step.panel) renderCard();
  }
  document.addEventListener("lm:call", (e) => onCall(e.detail));

  /* ---------- Only the lit control accepts input */
  const inLit = (el) => { const t = lit(); return t && (t === el || t.contains(el)); };
  function guard(e) {
    const el = e.target instanceof Element ? e.target : e.target && e.target.parentElement;
    if (!el || el.closest(".coach-card, dialog")) return;
    if (!actionDone && step.action !== "look" && inLit(el)) {
      if (e.type === "click" && step.panel && !tabOpen && step.action === "click") openTab(true);   // the click is the gesture the new tab needs
      const link = el.closest("a[href]");
      if (link && !link.target) { e.preventDefault(); e.stopPropagation(); return; }   // pages change only with İleri
      if (e.type === "click" && w.click && !w.path) setTimeout(complete, 50);
      if (e.type === "change" && w.change && !w.path) setTimeout(complete, 50);
      if (e.type === "input" && w.value !== undefined && String(el.value) === String(w.value)) setTimeout(complete, 50);
      return;
    }
    e.preventDefault(); e.stopPropagation();
    card.classList.remove("shake"); void card.offsetWidth; card.classList.add("shake");
  }
  ["click", "submit", "change", "input", "keydown", "dblclick", "contextmenu"].forEach((t) => document.addEventListener(t, (e) => {
    if (t === "keydown" && !["Enter", " ", "Spacebar"].includes(e.key) && !e.target.closest?.(".coach-card") && inLit(e.target)) return;  // typing in the lit field
    if (t === "keydown" && e.key === "Tab") return;
    guard(e);
  }, true));
  ["mousedown", "pointerdown"].forEach((t) => layer.addEventListener(t, (e) => e.preventDefault()));

  /* ---------- Start a step */
  function begin() {
    step = steps[st.i];
    last = st.i === steps.length - 1;
    w = step.wait || {};
    actionDone = !step.wait; phase = "do"; calls = []; seen = 0; from = 0; tabOpen = false;
    bar();
    if (step.action === "look" && !w.fresh) lm.calls.forEach(onCall);   // a "look" step waits for a call that the page made at load; other steps wait for the user's own action
    if (actionDone && step.focus) phase = "look-result";
    render();
    setTimeout(scrollToLit, 350);
  }
  document.body.classList.add("coach-on");
  begin();
})();
