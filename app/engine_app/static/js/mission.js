/* Mission of the Guided e-commerce app (tutorials/guided.yaml): coach marks and the "Perde arkası" panel. Turkish, 101 level.
 *
 * The page goes dark. Only the control of the current step stays lit and accepts input. A small coach card next to it says
 * what to do. When the page makes the expected Engine call, the lit part moves to the top of the window and the
 * "Perde arkası" panel opens at the bottom: need, concept, simulation (guided-sim.js), live numbers, the query line by
 * line, "Akılda kalsın" and why this database. It shows only the calls that fill the lit part. A step with no `panel`
 * shows its `result` text in the small card.
 * Step fields: page, path, engines, use_case, title, why, do, target (CSS selector of the control),
 *   action: click | look | type | change,  wait: {method, path, query, body, count, any} | {click} | {change} | {value},
 *   focus (selector to light after the action), result (short text, steps with no panel), panel {need, concept, sim, live, query, remember, why_db}.
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
  let last, actionDone, phase, calls, w, seen, from = 0, sim = null;

  /* ---------- Top bar: progress only */
  const bar = () => { $("#mission").innerHTML = `<div class="mission-head"><span class="tutor-badge">Görev</span><span class="mission-step">Adım ${st.i + 1} / ${steps.length}</span>
    <ol class="mission-dots" aria-hidden="true">${steps.map((_, k) => `<li class="${k < st.i ? "done" : k === st.i ? "now" : ""}"></li>`).join("")}</ol>
    <span class="mission-hint">Aydınlık kontrolü ve yanındaki kartı takip et.</span></div>`; };

  /* ---------- Dark layer with a hole, the small coach card and the bottom panel */
  const layer = document.createElement("div");
  layer.className = "coach-layer";
  layer.innerHTML = `<div class="coach-block" data-b="t"></div><div class="coach-block" data-b="l"></div><div class="coach-block" data-b="r"></div>
    <div class="coach-block" data-b="b"></div><div class="coach-ring"></div><div class="coach-cover" hidden></div>`;
  const card = document.createElement("section");
  card.className = "coach-card";
  card.setAttribute("role", "dialog");
  card.setAttribute("aria-live", "polite");
  const sheet = document.createElement("section");
  sheet.className = "gp";
  sheet.setAttribute("role", "dialog");
  sheet.setAttribute("aria-label", "Perde arkası");
  sheet.hidden = true;
  document.body.append(layer, card, sheet);
  const ring = $(".coach-ring", layer), cover = $(".coach-cover", layer);
  const blocks = Object.fromEntries([...layer.querySelectorAll(".coach-block")].map((b) => [b.dataset.b, b]));

  const panelOpen = () => !sheet.hidden && !sheet.classList.contains("min");
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
    Object.assign(card.style, { top: `${top}px`, left: `${left}px`, width: `${cw}px` });
  }
  let raf = 0;
  const schedule = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; place(); }); };
  addEventListener("scroll", schedule, { passive: true });
  addEventListener("resize", schedule);
  new ResizeObserver(schedule).observe(document.body);
  function scrollToLit() {
    const el = lit();
    const smooth = matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
    const head = document.querySelector(".topbar");                                     // sticky: the lit part goes below it
    const below = head ? head.getBoundingClientRect().height : 0;
    if (el && panelOpen()) window.scrollTo({ top: window.scrollY + el.getBoundingClientRect().top - below - 20, behavior: smooth });   // the lit part goes to the top, the panel is below
    else if (el) el.scrollIntoView({ behavior: smooth, block: "center" });
    setTimeout(place, 450);
  }

  /* ---------- The small card (before the action, and for steps with no panel) */
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
      `<li><b>${esc(e.op)}</b> <span>${esc(e.engine || "")} · ${e.ms} ms${e.items !== undefined ? ` · ${e.items} kayıt` : ""}</span></li>`)).join("");
    return `<div class="coach-bts"><b>Perde arkası</b><p>${esc(step.result || "")}</p>${lines ? `<ol>${lines}</ol>` : ""}</div>`;
  }
  function renderCard() {
    card.hidden = actionDone && !!step.panel;
    if (card.hidden) return;
    card.innerHTML = `<header><span>${chips()}${step.use_case ? `<em>${esc(step.use_case)}</em>` : ""}</span><small>${st.i + 1} / ${steps.length}</small></header>
      <h2>${esc(step.title)}</h2>
      ${actionDone ? "" : `<p>${esc(step.why || "")}</p>`}
      <p class="coach-do ${actionDone ? "done" : ""}">${esc(step.do || "Aydınlık bölüme bak, sonra İleri'ye bas.")}</p>
      ${actionDone ? shortResult() : ""}
      <footer>${nav()}</footer>`;
    wire(card);
  }

  /* ---------- The "Perde arkası" panel */
  const STAGE_RE = /"stage":\s*"(\w+)"/g;
  function entryOf(c) { return (c && c.entries && c.entries[0]) || null; }
  function liveFacts(e) {
    if (!e) return null;
    const m = /docs examined:\s*(\d+),\s*returned:\s*(\d+)/.exec(e.explain || "");
    const stages = [...String(e.plan || "").matchAll(STAGE_RE)].map((x) => x[1]).reverse();   // the plan is outer → inner; show the order of work
    return { examined: m ? Number(m[1]) : null, returned: m ? Number(m[2]) : e.items, ms: e.ms, stages, request: e.request };
  }
  function liveHtml(L, facts) {
    const max = Math.max(...facts.map((f) => (f && f.examined) || 0), 1);
    return `<div class="gp-runs">${L.runs.map((r, k) => {
      const f = facts[k];
      if (!f) return `<div class="gp-run"><h4>${esc(r.label)}</h4><p class="gp-wait">Ölçüm alınıyor…</p></div>`;
      const stages = f.stages.filter((s) => L.stages && L.stages[s]);
      return `<div class="gp-run"><h4>${esc(r.label)}</h4>
        <dl><div><dt>Okunan doküman</dt><dd>${f.examined ?? "?"}</dd></div><div><dt>Dönen doküman</dt><dd>${f.returned ?? "?"}</dd></div><div><dt>Süre</dt><dd>${f.ms} ms</dd></div></dl>
        <div class="gp-bar" aria-hidden="true"><span style="width:${Math.round(100 * (f.examined || 0) / max)}%"></span></div>
        ${stages.length ? `<p class="gp-stages-cap">DocumentDB'nin yaptığı işler, sırasıyla:</p><ol class="gp-stages">${stages.map((s) =>
          `<li><code>${esc(s)}</code> ${esc(L.stages[s])}</li>`).join("")}</ol>` : ""}</div>`;
    }).join("")}</div>`;
  }
  /* Section 5: the command as a Turkish sentence, as code, piece by piece, and the one difference between the two runs.
   * The same colour marks one piece in all four places (q0..q5). */
  function queryHtml(Q) {
    const parts = Q.parts || [];
    const col = (k) => `q${k % 6}`;
    const INDENT = new Set(["filter", "proj"]);
    const codeLines = (list, mark) => list.map((x) => {
      const k = parts.indexOf(x);
      return `<span class="gq-line ${col(k)}${mark && x.only_off ? " added" : ""}" data-q="${esc(x.id)}" tabindex="0"><b>${k + 1}</b>${INDENT.has(x.id) ? "  " : ""}${esc(x.code)}</span>`;
    }).join("");
    const D = Q.diff;
    return `<section class="gp-sec gq"><h3><span>5</span>${esc(Q.title || "Sorgu")}</h3><p>${esc(Q.intro || "")}</p>
      <div class="gq-row"><span class="gq-label">Türkçesi</span><p class="gq-say">${parts.map((x, k) =>
        `<span class="${col(k)}" data-q="${esc(x.id)}" tabindex="0">${esc(x.say)}</span>`).join(" ")}</p></div>
      <div class="gq-row"><span class="gq-label">Komut</span><pre class="gq-code">${codeLines(parts, false)}</pre></div>
      <ol class="gq-cards">${parts.map((x, k) => `<li class="${col(k)}" data-q="${esc(x.id)}" tabindex="0"><header><b>${k + 1}</b><strong>${esc(x.name || "")}</strong><code>${esc(x.code)}</code></header>
        <p>${esc(x.note)}</p></li>`).join("")}</ol>
      ${D ? `<h4 class="gq-diff-title">${esc(D.title)}</h4><div class="gq-diff">
        <div><span class="gq-label">${esc(D.label_on)}</span><pre class="gq-code">${codeLines(parts.filter((x) => !x.only_off), false)}</pre></div>
        <div><span class="gq-label">${esc(D.label_off)}</span><pre class="gq-code">${codeLines(parts, true)}</pre></div></div>
        <p class="gq-diff-note">${esc(D.note)}</p>` : ""}</section>`;
  }
  function renderPanel() {
    const P = step.panel;
    const trig = calls[from];
    const C = P.concept || {};
    sheet.className = `gp eng-${(step.engines || [])[0] || "docdb"}`;
    sheet.hidden = false;
    sheet.innerHTML = `<header class="gp-head"><div><span class="gp-kicker">Perde arkası</span>${chips()}${step.use_case ? `<em>${esc(step.use_case)}</em>` : ""}
        <h2>${esc(step.title)}</h2></div>
      <div class="gp-nav"><small>Adım ${st.i + 1} / ${steps.length}</small><button type="button" class="quiet" data-c="min" aria-expanded="true">Paneli küçült</button>${nav()}</div></header>
      <div class="gp-body">
        <div class="gp-intro"><section class="gp-sec"><h3><span>1</span>Ne lazım?</h3><p>${esc(P.need)}</p></section>
        <section class="gp-sec"><h3><span>2</span>Kavram: ${esc(C.term || "")}</h3><p>${esc(C.text || "")}</p></section></div>
        ${(C.terms || []).length ? `<dl class="gp-terms">${C.terms.map(([t, d]) => `<div><dt>${esc(t)}</dt><dd>${esc(d)}</dd></div>`).join("")}</dl>` : ""}
        ${P.sim ? `<section class="gp-sec"><h3><span>3</span>Simülasyon</h3><div class="gp-sim"></div></section>` : ""}
        ${P.live ? `<section class="gp-sec"><h3><span>4</span>${esc(P.live.title || "Sistemde gerçekte ne oldu?")}</h3><p>${esc(P.live.intro || "")}</p>
          <div class="gp-live"></div><p class="gp-reading">${esc(P.live.reading || "")}</p></section>` : ""}
        ${P.query ? queryHtml(P.query) : ""}
        <section class="gp-sec gp-keep"><h3>Akılda kalsın</h3><p>${esc(P.remember || "")}</p>${P.why_db ? `<p class="gp-why">${esc(P.why_db)}</p>` : ""}</section>
      </div>`;
    wire(sheet);
    const minBtn = sheet.querySelector("[data-c=min]");
    minBtn.addEventListener("click", () => {
      const min = sheet.classList.toggle("min");
      minBtn.textContent = min ? "Paneli aç" : "Paneli küçült";
      minBtn.setAttribute("aria-expanded", String(!min));
      document.body.classList.toggle("gp-on", !min);
      schedule();
    });
    if (P.sim && window.GuidedSim) {
      sim = GuidedSim.render(sheet.querySelector(".gp-sim"), P.sim);
      const io = new IntersectionObserver((seen) => {             // the simulation plays once, when it comes into view in the panel
        if (seen.some((x) => x.isIntersecting)) { io.disconnect(); setTimeout(() => sim.play(), 400); }
      }, { root: sheet.querySelector(".gp-body"), threshold: 0.35 });
      io.observe(sheet.querySelector(".gp-sim"));
    }
    sheet.querySelectorAll(".gq [data-q]").forEach((el) => {     // one piece of the command: the sentence, the code and the card light up together
      const part = (P.query.parts || []).find((x) => x.id === el.dataset.q) || {};
      const on = () => { sheet.querySelectorAll(`.gq [data-q="${el.dataset.q}"]`).forEach((x) => x.classList.add("on")); if (sim) sim.highlight(part.hl); };
      const off = () => { sheet.querySelectorAll(".gq .on").forEach((x) => x.classList.remove("on")); if (sim) sim.highlight(null); };
      el.addEventListener("mouseenter", on); el.addEventListener("focus", on);
      el.addEventListener("mouseleave", off); el.addEventListener("blur", off);
    });
    if (P.live) fillLive(P.live, trig);
    document.body.classList.add("gp-on");
  }
  async function fillLive(L, trig) {
    const box = sheet.querySelector(".gp-live");
    const facts = L.runs.map((r) => (r.trigger ? liveFacts(entryOf(trig)) : null));
    box.innerHTML = liveHtml(L, facts);
    await Promise.all(L.runs.map(async (r, k) => {
      if (!r.fetch) return;
      try { const j = await (await fetch(r.fetch)).json(); facts[k] = liveFacts((j.trace || [])[0]); }   // a measurement for the panel only, not a shop call
      catch (e) { facts[k] = null; }
    }));
    box.innerHTML = liveHtml(L, facts);
  }
  function render() {
    renderCard();
    if (actionDone && step.panel) renderPanel();
    else { sheet.hidden = true; document.body.classList.remove("gp-on"); }
    cover.hidden = !(step.action === "look" || actionDone);       // after the action, the lit part is for reading only
    schedule();
  }
  function complete() {
    if (actionDone) return;
    actionDone = true;
    st.done[st.i] = true; save(st);
    if (step.focus) phase = "look-result";
    render();
    scrollToLit();
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
    if (!el || el.closest(".coach-card, .gp, dialog")) return;
    if (!actionDone && step.action !== "look" && inLit(el)) {
      const link = el.closest("a[href]");
      if (link && !link.target) { e.preventDefault(); e.stopPropagation(); return; }   // pages change only with İleri
      if (e.type === "click" && w.click && !w.path) setTimeout(complete, 50);
      if (e.type === "change" && w.change && !w.path) setTimeout(complete, 50);
      if (e.type === "input" && w.value !== undefined && String(el.value) === String(w.value)) setTimeout(complete, 50);
      return;
    }
    e.preventDefault(); e.stopPropagation();
    const box = sheet.hidden ? card : sheet;
    box.classList.remove("shake"); void box.offsetWidth; box.classList.add("shake");
  }
  ["click", "submit", "change", "input", "keydown", "dblclick", "contextmenu"].forEach((t) => document.addEventListener(t, (e) => {
    if (t === "keydown" && !["Enter", " ", "Spacebar"].includes(e.key) && !e.target.closest?.(".coach-card, .gp") && inLit(e.target)) return;  // typing in the lit field
    if (t === "keydown" && e.key === "Tab") return;
    guard(e);
  }, true));
  ["mousedown", "pointerdown"].forEach((t) => layer.addEventListener(t, (e) => e.preventDefault()));

  /* ---------- Start a step */
  function begin() {
    step = steps[st.i];
    last = st.i === steps.length - 1;
    w = step.wait || {};
    actionDone = !step.wait; phase = "do"; calls = []; seen = 0; from = 0; sim = null;
    bar();
    if (step.action === "look" && !w.fresh) lm.calls.forEach(onCall);   // a "look" step waits for a call that the page made at load; other steps wait for the user's own action
    if (actionDone && step.focus) phase = "look-result";
    render();
    setTimeout(scrollToLit, 350);
  }
  document.body.classList.add("coach-on");
  begin();
})();
