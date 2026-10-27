/* Mission of the Guided e-commerce app (tutorials/guided.yaml): coach marks.
 *
 * The page goes dark. Only the control of the current step stays lit and accepts input. A coach card next to it says
 * what to do. When the page makes the expected Engine call, the card shows "Behind the scenes": what happened, and the
 * real calls with their time. Then a checkpoint question (if the step has one), then Next.
 * Step fields: page, path, engines, use_case, title, why, do, target (CSS selector of the control),
 *   action: click | look | type | change,  wait: {method, path, query, body, count, any} | {click} | {change} | {value},
 *   focus (selector to light after the action), result (the explanation), quiz {q, options, answer, why}.
 * State: localStorage lm_mission = {"i": step index, "done": {index: true}}.
 */
(function () {
  "use strict";
  if (!window.LM || !LM.mission || !document.getElementById("mission")) return;
  const { esc, $ } = lm;
  const steps = LM.mission.steps || [];
  const BASE = LM.mode.base;
  const KEY = "lm_mission";
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY)) || { i: 0, done: {} }; } catch (e) { return { i: 0, done: {} }; } };
  const save = (st) => localStorage.setItem(KEY, JSON.stringify(st));
  let st = load();
  st.i = Math.max(0, Math.min(st.i || 0, steps.length - 1));
  let step = steps[st.i];
  const go = (s) => { window.location.href = BASE + s.path; };
  if (step.page !== LM.page.id) { go(step); return; }          // a step on another page: go there

  const ENGINE_LABEL = { docdb: "DocumentDB", opensearch: "OpenSearch", neptune: "Neptune", dynamodb: "DynamoDB", aurora: "Aurora PostgreSQL",
    elasticache: "ElastiCache (Valkey)", keyspaces: "Keyspaces", s3: "S3", redshift: "Redshift", influxdb: "Timestream for InfluxDB" };
  let last, actionDone, quizOk, phase, calls, w, seen, from = 0;

  /* ---------- Top bar: progress only */
  const bar = () => { $("#mission").innerHTML = `<div class="mission-head"><span class="tutor-badge">Mission</span><span class="mission-step">Step ${st.i + 1} of ${steps.length}</span>
    <ol class="mission-dots" aria-hidden="true">${steps.map((_, k) => `<li class="${k < st.i ? "done" : k === st.i ? "now" : ""}"></li>`).join("")}</ol>
    <span class="mission-hint">Follow the lit control and the card next to it.</span></div>`; };

  /* ---------- Dark layer with a hole, and the coach card */
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
    if (el) el.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
    setTimeout(place, 450);
  }

  /* ---------- The card */
  function chips() { return (step.engines || []).map((e) => `<span class="chip eng-${e}">${esc(ENGINE_LABEL[e] || e)}</span>`).join(""); }
  function bts() {
    const after = calls.slice(from);                          // the call that completed the step, and the calls after it
    const main = after.filter((c) => !c.background);
    const shown = (main.length ? main : after).slice(0, 3);
    const lines = shown.flatMap((c) => (c.entries || []).slice(0, 4).map((e) =>
      `<li><b>${esc(e.op)}</b> <span>${esc(e.engine || "")} · ${e.ms} ms${e.items !== undefined ? ` · ${e.items} item(s)` : ""}${e.capacity ? ` · ${esc(e.capacity)}` : ""}</span>
       <pre>${esc(String(e.request || "").split("\n").slice(0, 6).join("\n"))}</pre>${e.explain ? `<p><b>${esc(typeof e.explain === "string" ? e.explain : JSON.stringify(e.explain))}</b></p>` : ""}${e.note ? `<p>${esc(e.note)}</p>` : ""}</li>`)).join("");
    return `<div class="coach-bts"><b>Behind the scenes</b><p>${esc(step.result || "")}</p>${lines ? `<ol>${lines}</ol>` : ""}
      <p class="coach-more">The full calls are in the Behind-the-scenes panel at the right, after the mission.</p></div>`;
  }
  function quizHtml() {
    const q = step.quiz;
    const order = q.options.map((_, k) => (k + st.i) % q.options.length);   // the right answer moves from step to step
    return `<div class="coach-quiz"><b>Checkpoint</b><p>${esc(q.q)}</p><div class="opts">${order.map((k) => `<button type="button" data-k="${k}">${esc(q.options[k])}</button>`).join("")}</div><p class="why" hidden></p></div>`;
  }
  function render() {
    const doneNow = actionDone;
    card.innerHTML = `<header><span>${chips()}${step.use_case ? `<em>${esc(step.use_case)}</em>` : ""}</span><small>${st.i + 1} / ${steps.length}</small></header>
      <h2>${esc(step.title)}</h2>
      ${doneNow ? "" : `<p>${esc(step.why || "")}</p>`}
      <p class="coach-do ${doneNow ? "done" : ""}">${esc(step.do || "Look at the lit part, then select Next.")}</p>
      ${doneNow ? bts() : ""}
      ${doneNow && step.quiz ? quizHtml() : ""}
      <footer>
        <button type="button" class="quiet" data-c="restart">Start again</button>
        <span></span>
        <button type="button" data-c="back" ${st.i === 0 ? "disabled" : ""}>Back</button>
        <button type="button" class="primary" data-c="next" ${doneNow && quizOk ? "" : "disabled"}>${last ? "Finish the mission" : "Next"}</button>
      </footer>`;
    card.querySelector("[data-c=next]").addEventListener("click", next);
    card.querySelector("[data-c=back]").addEventListener("click", () => { st.i -= 1; save(st); go(steps[st.i]); });
    card.querySelector("[data-c=restart]").addEventListener("click", () => { save({ i: 0, done: {} }); go(steps[0]); });
    card.querySelectorAll(".coach-quiz button").forEach((b) => b.addEventListener("click", () => {
      const right = Number(b.dataset.k) === step.quiz.answer, why = card.querySelector(".coach-quiz .why");
      b.classList.add(right ? "right" : "wrong");
      why.hidden = false;
      why.textContent = right ? `Correct. ${step.quiz.why}` : "Not correct. Read the Behind-the-scenes note again and try another answer.";
      if (right) { card.querySelectorAll(".coach-quiz button").forEach((x) => { x.disabled = true; }); quizOk = true; card.querySelector("[data-c=next]").disabled = false; }
      schedule();
    }));
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
    if (n.page === LM.page.id && n.path === step.path) begin(false); else go(n);   // same page: continue in place, the page keeps its state
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
    else if (actionDone) render();
  }
  document.addEventListener("lm:call", (e) => onCall(e.detail));

  /* ---------- Only the lit control accepts input */
  const inLit = (el) => { const t = lit(); return t && (t === el || t.contains(el)); };
  function guard(e) {
    const el = e.target instanceof Element ? e.target : e.target && e.target.parentElement;
    if (!el || el.closest(".coach-card, dialog")) return;
    if (!actionDone && step.action !== "look" && inLit(el)) {
      const link = el.closest("a[href]");
      if (link && !link.target) { e.preventDefault(); e.stopPropagation(); return; }   // pages change only with Next
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

  /* ---------- Start a step. replay: also count the calls that the page made before (first step after a page load). */
  function begin(replay) {
    step = steps[st.i];
    last = st.i === steps.length - 1;
    w = step.wait || {};
    actionDone = !step.wait; quizOk = !step.quiz; phase = "do"; calls = []; seen = 0; from = 0;
    bar();
    if (step.action === "look" && !w.fresh) lm.calls.forEach(onCall);   // a "look" step waits for a call that the page made at load; other steps wait for the user's own action
    if (actionDone && step.focus) phase = "look-result";
    render();
    setTimeout(scrollToLit, 350);
  }
  document.body.classList.add("coach-on");
  begin(true);
})();
