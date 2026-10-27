/* Mission of the Guided e-commerce app (tutorials/guided.yaml).
 *
 * One step at a time. Each step lives on one page. Only the step target, the Mission bar, the section bar and the
 * Behind-the-Scenes Panel accept clicks. The step is complete when the page makes the expected Engine call
 * (`wait`) and the visitor answers the checkpoint question (`quiz`). Next goes to the next step, also on another page.
 * State: localStorage lm_mission = {"i": <step index>, "done": {<index>: true}}.
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
  const step = steps[st.i];
  const go = (s) => { window.location.href = BASE + s.path; };

  // A step that lives on another page: go there. The visitor cannot use a page out of order.
  if (step.page !== LM.page.id) { go(step); return; }

  const ENGINE_LABEL = { docdb: "DocumentDB", opensearch: "OpenSearch", neptune: "Neptune", dynamodb: "DynamoDB", aurora: "Aurora PostgreSQL",
    elasticache: "ElastiCache (Valkey)", keyspaces: "Keyspaces", s3: "S3", redshift: "Redshift", influxdb: "Timestream for InfluxDB" };
  const done = () => !!st.done[st.i];
  let waitOk = !step.wait, quizOk = !step.quiz;

  /* ---------- Render */
  $("#mission-step").textContent = `Step ${st.i + 1} of ${steps.length}`;
  $("#mission-dots").innerHTML = steps.map((_, k) => `<li class="${k < st.i ? "done" : k === st.i ? "now" : ""}"></li>`).join("");
  $("#mission-engine").innerHTML = (step.engines || []).map((e) => `<span class="chip eng-${e}">${esc(ENGINE_LABEL[e] || e)}</span>`).join("")
    + (step.use_case ? esc(step.use_case) : "");
  $("#mission-title").textContent = step.title;
  $("#mission-why").textContent = step.why || "";
  $("#mission-do").textContent = step.do || "Read the step, then select Next.";
  $("#mission-back").disabled = st.i === 0;
  const last = st.i === steps.length - 1;
  $("#mission-next").textContent = last ? "Finish the mission" : "Next";

  function renderQuiz() {
    const q = step.quiz, box = $("#mission-quiz");
    if (!q) return;
    box.hidden = !waitOk;   // the question comes after the action
    if (box.dataset.ready) return;
    box.dataset.ready = "1";
    // The options rotate by step number, so the right answer is not always in the same place.
    const order = q.options.map((_, k) => (k + st.i) % q.options.length);
    box.innerHTML = `<p>Checkpoint: ${esc(q.q)}</p><div class="opts">${order.map((k) => `<button type="button" data-k="${k}">${esc(q.options[k])}</button>`).join("")}</div>
      <p class="why" hidden></p>`;
    box.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      const right = Number(b.dataset.k) === q.answer;
      b.classList.add(right ? "right" : "wrong");
      const why = box.querySelector(".why");
      why.hidden = false;
      why.textContent = right ? `Correct. ${q.why}` : "Not correct. Read the panel again and try another answer.";
      if (right) { box.querySelectorAll("button").forEach((x) => { x.disabled = true; }); quizOk = true; check(); }
    }));
  }

  function check() {
    renderQuiz();
    const complete = waitOk && quizOk;
    if (complete && !done()) { st.done[st.i] = true; save(st); }
    $("#mission-do").classList.toggle("done", waitOk);
    if (waitOk && step.result) { $("#mission-result").hidden = false; $("#mission-result").innerHTML = `<p>${esc(step.result)}</p>`; }
    $("#mission-next").disabled = !(complete || done());
  }

  /* ---------- Wait for the Engine call of the step */
  function matches(c) {
    const w = step.wait;
    if (!w || (!c.ok && !w.any)) return false;   // any: a refused Load Simulation also counts
    if (w.method && w.method !== c.method) return false;
    if (w.path && !(w.path.endsWith("*") ? c.path.startsWith(w.path.slice(0, -1)) : c.path === w.path)) return false;
    const same = (got, want) => (want === "*" ? got !== undefined && got !== "" : String(got) === String(want));   // "*": any value
    for (const [k, v] of Object.entries(w.query || {})) if (!same(c.query[k], v)) return false;
    for (const [k, v] of Object.entries(w.body || {})) if (!same(c.body[k], v)) return false;
    if (w.background === false && c.background) return false;
    return true;
  }
  let seen = 0;
  function onCall(c) {
    if (waitOk || !matches(c)) return;
    seen += 1;
    if (seen >= (step.wait.count || 1)) { waitOk = true; check(); }
  }
  if (step.wait && !step.wait.fresh) lm.calls.forEach(onCall);   // calls that the page made before this script ran
  document.addEventListener("lm:call", (e) => onCall(e.detail));

  /* ---------- Lock: only the step target, the Mission and the panel accept input */
  document.body.classList.add("g-lock");
  const open = () => (step.target ? [...document.querySelectorAll(step.target)] : []);
  open().forEach((el) => el.classList.add("g-open"));
  const allowed = (el) => el.closest("#mission, .sitebar, #bts, dialog, .g-open, .g-toast");
  let toastTimer;
  function toast(text) {
    let t = $(".g-toast");
    if (!t) { t = document.createElement("div"); t.className = "g-toast"; t.setAttribute("role", "status"); document.body.appendChild(t); }
    t.textContent = text;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => t.remove(), 2600);
  }
  function guard(e) {
    const el = e.target instanceof Element ? e.target : e.target.parentElement;
    if (!el || !el.closest(".topbar, .catnav, .shop, .site-foot")) return;
    const link = el.closest("a[href]");
    // Links in the shop change the page. The Mission changes the page with Next, so the order of steps stays.
    const leaves = link && !link.target && link.closest(".shop, .topbar, .catnav");
    if (allowed(el) && !leaves) return;
    e.preventDefault(); e.stopPropagation();
    toast(leaves ? "In the mission, Next takes you to the next page." : "Do the step in the amber box first. The outlined part is open.");
  }
  ["click", "submit", "change", "input"].forEach((t) => document.addEventListener(t, guard, true));
  document.addEventListener("keydown", (e) => { if (e.key === "Enter") guard(e); }, true);

  /* ---------- Navigation */
  $("#mission-next").addEventListener("click", () => {
    if (last) { st.finished = true; save(st); window.location.href = LM.mission.finish_url || "/"; return; }
    st.i += 1; save(st);
    const next = steps[st.i];
    if (next.page === LM.page.id && next.path === step.path) { window.location.reload(); } else { go(next); }
  });
  $("#mission-back").addEventListener("click", () => { st.i -= 1; save(st); go(steps[st.i]); });
  $("#mission-restart").addEventListener("click", () => { save({ i: 0, done: {} }); go(steps[0]); });

  check();
  const first = open()[0];
  if (first && st.i > 0) setTimeout(() => first.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" }), 300);
})();
