/* E2E tutorials: run a fixed query on the live Engine, checkpoint questions, Predict boxes, table of contents.
 * Progress: localStorage e2e_<engine> = {"quiz": {<id>: true|false}}. */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const engine = document.body.dataset.engine;
  const T = window.E2E_UI || {};
  const KEY = `e2e_${engine}`;
  const state = (() => { try { return JSON.parse(localStorage.getItem(KEY)) || { quiz: {} }; } catch (e) { return { quiz: {} }; } })();
  const save = () => localStorage.setItem(KEY, JSON.stringify(state));

  /* ---------- Table of contents from the h2 elements, with the section in view */
  const toc = $("#toc-list");
  const heads = $$(".lesson h2[id]");
  if (toc) {
    // Groups: an h2 inside a .part banner opens a group (Part A, B, ...); an h2 with data-group opens or continues a named group.
    // Each item shows the section number (the .sec span, for example A2) before its short title.
    const item = (h) => { const n = h.querySelector(".sec"); return `<li><a href="#${h.id}">${n ? `<span class="toc-n">${esc(n.textContent)}</span>` : ""}${esc(h.dataset.short || h.textContent.replace(/^\d+\s*/, ""))}</a></li>`; };
    let html = "", open = null;
    const close = () => { if (open !== null) { html += "</ol></li>"; open = null; } };
    heads.forEach((h) => {
      const banner = h.closest(".part");
      const g = banner ? (h.dataset.short || h.textContent) : h.dataset.group;
      if (banner) { close(); html += `<li class="toc-g"><a class="toc-gh" href="#${h.id}">${esc(g)}</a><ol>`; open = g; return; }
      if (g && g !== open) { close(); html += `<li class="toc-g"><a class="toc-gh" href="#${h.id}">${esc(g)}</a><ol>`; open = g; }
      html += item(h);
    });
    close();
    toc.innerHTML = html;
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
        <tbody>${rows.map((r) => `<tr>${r.map((v) => `<td>${cell(v)}</td>`).join("")}</tr>`).join("") || `<tr><td colspan="${d.columns.length}">${esc(T.no_rows)}</td></tr>`}</tbody></table></div>`;
    } else if (d.json !== undefined) {
      body = `<pre>${esc(JSON.stringify(d.json, null, 2))}</pre>`;
    } else if (d.text !== undefined) {
      body = `<pre>${esc(d.text)}</pre>`;
    }
    const t = json.trace || [];
    const engineMs = t.reduce((s, e) => s + (e.ms || 0), 0);
    out.innerHTML = `<div class="meta"><span>${esc(T.round_trip)} <b>${ms} ms</b></span><span>${esc(T.engine_time)} <b>${Math.round(engineMs * 10) / 10} ms</b></span>
      ${d.rows ? `<span>${esc(T.rows)} <b>${d.rows.length}${d.total !== undefined ? ` ${esc(T.of)} ${d.total}` : ""}</b></span>` : ""}</div>
      ${d.note ? `<p class="note">${esc(d.note)}</p>` : ""}${body}
      ${t.length ? `<details class="tr"><summary>${esc(T.sent)} (${t.length})</summary>${t.map((e) => `<p><b>${esc(e.op)}</b> · ${e.ms} ms${e.items !== undefined ? ` · ${e.items} item(s)` : ""}${e.capacity ? ` · ${esc(e.capacity)}` : ""}</p>
        <pre>${esc(e.request)}</pre>${e.explain ? `<pre>${esc(typeof e.explain === "string" ? e.explain : JSON.stringify(e.explain, null, 2))}</pre>` : ""}${e.plan ? `<pre>${esc(e.plan)}</pre>` : ""}${e.note ? `<p>${esc(e.note)}</p>` : ""}`).join("")}</details>` : ""}`;
  }
  $$("[data-run]").forEach((box) => {
    const btn = $("button", box), out = $(".run-out", box);
    btn.addEventListener("click", async () => {
      btn.disabled = true; out.innerHTML = `<p>${esc(T.running)}</p>`;
      const t0 = performance.now();
      let json;
      try {
        const res = await fetch(`/${box.dataset.run.replace("/", "/api/e2e/")}`);
        json = await res.json().catch(() => ({ ok: false, error: `HTTP ${res.status}: the Engine App did not return JSON.` }));
      } catch (e) { json = { ok: false, error: `The request did not reach the Engine App: ${e.message}` }; }
      render(out, json, Math.round(performance.now() - t0));
      btn.disabled = false; btn.textContent = T.run_again;
    });
  });

  /* ---------- Checkpoint questions */
  const quizzes = $$(".quiz");
  function score() {
    const el = $("#score");
    if (!el) return;
    const ok = quizzes.filter((q) => state.quiz[q.id] === true).length;
    el.innerHTML = T.score.replace("{ok}", ok).replace("{total}", quizzes.length);
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
      else { why.hidden = false; why.dataset.keep = why.dataset.keep || why.innerHTML; why.innerHTML = T.not_correct; }
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
    btn.addEventListener("click", () => { ans.hidden = !ans.hidden; btn.textContent = ans.hidden ? T.show : T.hide; });
  });
})();

/* ---------- Simulations (e2e_sims.py): input tables, a result table, one step at a time */
(function () {
  "use strict";
  const T = window.E2E_UI || {};
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (v) => (typeof v === "number" && !Number.isInteger(v) ? v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : v);
  function table(t, rows, marks) {
    const head = t.cols.map((c, i) => `<th class="${t.key.includes(i) ? "k" : t.ref.includes(i) ? "r" : ""}">${esc(c)}</th>`).join("");
    const body = rows.length ? rows.map((r, i) => `<tr class="${marks && marks[i] ? `m-${marks[i]}` : ""}">${r.map((v) => `<td>${esc(fmt(v))}</td>`).join("")}</tr>`).join("")
      : `<tr><td colspan="${t.cols.length}" class="empty">${esc(T.no_rows)}</td></tr>`;
    return `<figure class="simt"><figcaption>${esc(t.name)}</figcaption><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></figure>`;
  }
  document.querySelectorAll(".sim").forEach((box) => {
    const spec = JSON.parse(box.querySelector("script[type='application/json']").textContent);
    const stage = box.querySelector(".sim-stage"), say = box.querySelector(".sim-say"), pos = box.querySelector(".sim-pos");
    const [bPlay, bBack, bNext, bReset] = ["play", "back", "next", "reset"].map((k) => box.querySelector(`[data-sim=${k}]`));
    let i = -1, timer = null;
    function draw() {
      const st = i >= 0 ? spec.steps[i] : { marks: {}, rows: {}, out: [], count: {} };
      const ins = spec.tables.map((t) => table(t, (st.rows && st.rows[t.id]) || t.rows, (st.marks || {})[t.id])).join("");
      const out = spec.out ? table({ name: spec.out.name, cols: spec.out.cols, key: [], ref: [] }, st.out || [], st.outmarks) : "";
      const cnt = Object.entries(st.count || {}).map(([k, v]) => `<span>${esc(k)}: <b>${esc(v)}</b></span>`).join("");
      stage.innerHTML = `<div class="sim-in">${ins}</div>${out ? `<div class="sim-out">${out}</div>` : ""}${cnt ? `<div class="sim-count">${cnt}</div>` : ""}`;
      say.textContent = i >= 0 ? st.say : T.sim_start;
      pos.textContent = i >= 0 ? T.sim_step.replace("{n}", i + 1).replace("{total}", spec.steps.length) : "";
      bBack.disabled = i <= 0; bNext.disabled = i >= spec.steps.length - 1;
      bPlay.textContent = timer ? T.sim_pause : (i >= spec.steps.length - 1 ? T.sim_replay : T.sim_play);
    }
    function stop() { clearInterval(timer); timer = null; }
    bNext.addEventListener("click", () => { stop(); i = Math.min(i + 1, spec.steps.length - 1); draw(); });
    bBack.addEventListener("click", () => { stop(); i = Math.max(i - 1, 0); draw(); });
    bReset.addEventListener("click", () => { stop(); i = -1; draw(); });
    bPlay.addEventListener("click", () => {
      if (timer) { stop(); draw(); return; }
      if (i >= spec.steps.length - 1) i = -1;
      i += 1; draw();
      timer = setInterval(() => { if (i >= spec.steps.length - 1) { stop(); draw(); return; } i += 1; draw(); }, 3200);
      draw();
    });
    draw();
  });
})();
