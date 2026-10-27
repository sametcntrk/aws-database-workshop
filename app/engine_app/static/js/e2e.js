/* E2E tutorials: run a fixed query on the live Engine, checkpoint questions, Predict boxes, table of contents.
 * Progress: localStorage e2e_<engine> = {"quiz": {<id>: true|false}}. */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const engine = document.body.dataset.engine;
  const KEY = `e2e_${engine}`;
  const state = (() => { try { return JSON.parse(localStorage.getItem(KEY)) || { quiz: {} }; } catch (e) { return { quiz: {} }; } })();
  const save = () => localStorage.setItem(KEY, JSON.stringify(state));

  /* ---------- Table of contents from the h2 elements, with the section in view */
  const toc = $("#toc-list");
  const heads = $$(".lesson h2[id]");
  if (toc) {
    toc.innerHTML = heads.map((h) => `<li><a href="#${h.id}">${esc(h.dataset.short || h.textContent.replace(/^\d+\s*/, ""))}</a></li>`).join("");
    const links = $$("a", toc);
    const io = new IntersectionObserver((es) => es.forEach((e) => {
      if (e.isIntersecting) links.forEach((a) => a.classList.toggle("on", a.getAttribute("href") === `#${e.target.id}`));
    }), { rootMargin: "0px 0px -70% 0px" });
    heads.forEach((h) => io.observe(h));
  }

  /* ---------- Run a query on the live Engine */
  function cell(v) {
    if (v === null || v === undefined) return '<span class="muted">null</span>';
    if (typeof v === "object") return `<code>${esc(JSON.stringify(v))}</code>`;
    return esc(v);
  }
  function render(out, json, ms) {
    if (json.ok === false) { out.innerHTML = `<p class="err">${esc(json.error || "The query failed.")}</p>`; return; }
    const d = json.data || {};
    let body = "";
    if (d.columns) {
      const rows = d.rows || [];
      body = `<div class="scroll"><table class="data"><thead><tr>${d.columns.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>
        <tbody>${rows.map((r) => `<tr>${r.map((v) => `<td>${cell(v)}</td>`).join("")}</tr>`).join("") || `<tr><td colspan="${d.columns.length}">No rows.</td></tr>`}</tbody></table></div>`;
    } else if (d.json !== undefined) {
      body = `<pre>${esc(JSON.stringify(d.json, null, 2))}</pre>`;
    } else if (d.text !== undefined) {
      body = `<pre>${esc(d.text)}</pre>`;
    }
    const t = json.trace || [];
    const engineMs = t.reduce((s, e) => s + (e.ms || 0), 0);
    out.innerHTML = `<div class="meta"><span>Round trip <b>${ms} ms</b></span><span>Time in the Engine call(s) <b>${Math.round(engineMs * 10) / 10} ms</b></span>
      ${d.rows ? `<span>Rows <b>${d.rows.length}${d.total !== undefined ? ` of ${d.total}` : ""}</b></span>` : ""}</div>
      ${d.note ? `<p class="note">${esc(d.note)}</p>` : ""}${body}
      ${t.length ? `<details class="tr"><summary>What the Engine App sent (${t.length} call${t.length > 1 ? "s" : ""})</summary>${t.map((e) => `<p><b>${esc(e.op)}</b> · ${e.ms} ms${e.items !== undefined ? ` · ${e.items} item(s)` : ""}${e.capacity ? ` · ${esc(e.capacity)}` : ""}</p>
        <pre>${esc(e.request)}</pre>${e.explain ? `<pre>${esc(typeof e.explain === "string" ? e.explain : JSON.stringify(e.explain, null, 2))}</pre>` : ""}${e.plan ? `<pre>${esc(e.plan)}</pre>` : ""}${e.note ? `<p>${esc(e.note)}</p>` : ""}`).join("")}</details>` : ""}`;
  }
  $$("[data-run]").forEach((box) => {
    const btn = $("button", box), out = $(".run-out", box);
    btn.addEventListener("click", async () => {
      btn.disabled = true; out.innerHTML = "<p>The query runs on the live Engine.</p>";
      const t0 = performance.now();
      let json;
      try {
        const res = await fetch(`/${box.dataset.run.replace("/", "/api/e2e/")}`);
        json = await res.json().catch(() => ({ ok: false, error: `HTTP ${res.status}: the Engine App did not return JSON.` }));
      } catch (e) { json = { ok: false, error: `The request did not reach the Engine App: ${e.message}` }; }
      render(out, json, Math.round(performance.now() - t0));
      btn.disabled = false; btn.textContent = "Run again";
    });
  });

  /* ---------- Checkpoint questions */
  const quizzes = $$(".quiz");
  function score() {
    const el = $("#score");
    if (!el) return;
    const ok = quizzes.filter((q) => state.quiz[q.id] === true).length;
    el.innerHTML = `Checkpoints: <b>${ok} of ${quizzes.length}</b> correct`;
  }
  quizzes.forEach((q) => {
    const answer = Number(q.dataset.answer);
    const why = $(".why", q);
    const buttons = $$(".opts button", q);
    const finish = (k, first) => {
      const right = k === answer;
      buttons[k].classList.add(right ? "right" : "wrong");
      if (first && state.quiz[q.id] === undefined) { state.quiz[q.id] = right; save(); }
      if (right) { buttons.forEach((b) => { b.disabled = true; }); q.classList.add("ok"); why.hidden = false; }
      else { why.hidden = false; why.dataset.keep = why.dataset.keep || why.innerHTML; why.innerHTML = "<b>Not correct.</b> Read the section above again, then try another answer."; }
      if (right && why.dataset.keep) why.innerHTML = why.dataset.keep;
      score();
    };
    buttons.forEach((b, k) => b.addEventListener("click", () => finish(k, true)));
    if (state.quiz[q.id] !== undefined) { /* already answered on an earlier visit: show the answer */ buttons[answer].classList.add("right"); buttons.forEach((b) => { b.disabled = true; }); q.classList.add("ok"); why.hidden = false; }
  });
  score();

  /* ---------- Predict first, then look */
  $$(".predict").forEach((p) => {
    const btn = $("button", p), ans = $(".answer", p);
    btn.addEventListener("click", () => { ans.hidden = !ans.hidden; btn.textContent = ans.hidden ? "Show the answer" : "Hide the answer"; });
  });
})();
