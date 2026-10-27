/* Lale Market core: Visitor and Persona, API calls with the Behind-the-Scenes Panel, Tutorial and Guided journey. */
(function () {
  "use strict";
  const $ = (sel, root = document) => root.querySelector(sel);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const tl = (n) => new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY", maximumFractionDigits: 2 }).format(n);
  const ENGINE_LABEL = { docdb: "DocumentDB", opensearch: "OpenSearch", neptune: "Neptune", dynamodb: "DynamoDB", aurora: "Aurora",
    elasticache: "ElastiCache", keyspaces: "Keyspaces", s3: "S3", redshift: "Redshift", influxdb: "InfluxDB" };

  /* ---------------- Visitor and Persona (cookies, read by every Engine App) */
  function cookie(name) { return (document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)")) || [])[1]; }
  function setCookie(name, value) { document.cookie = `${name}=${value}; path=/; max-age=${60 * 60 * 24 * 30}; SameSite=Lax; Secure`; }
  if (!cookie("lm_visitor")) setCookie("lm_visitor", crypto.randomUUID());
  const visitor = cookie("lm_visitor");

  function persona() { return LM.personas.find((p) => p.id === cookie("lm_persona")); }
  function showPersona() {
    const p = persona();
    $("#persona-name").textContent = p ? p.name : "Choose a persona";
    $("#persona-avatar").textContent = p ? p.name[0] : "?";
  }
  const dialog = $("#persona-dialog");
  $("#persona-chip").addEventListener("click", () => dialog.showModal());
  dialog.addEventListener("close", () => {
    if (dialog.returnValue) { setCookie("lm_persona", dialog.returnValue); showPersona(); document.dispatchEvent(new CustomEvent("lm:persona")); }
  });
  showPersona();
  if (!persona()) dialog.showModal();

  /* ---------------- Behind-the-Scenes Panel */
  const list = $("#bts-list");
  let callNo = 0;
  function renderEntry(e, maxMs, learn) {
    const rows = [];
    const add = (k, v) => { if (v !== undefined && v !== null && v !== "") rows.push(`<dt>${k}</dt><dd>${esc(v)}</dd>`); };
    const params = e.params && Object.keys(e.params).length ? Object.entries(e.params).map(([k, v]) => `${k} = ${typeof v === "object" ? JSON.stringify(v) : v}`).join(", ") : "";
    add("Parameters", params);
    add("Result", e.items !== undefined ? `${e.items} item(s)` : "");
    add("Explain", e.explain);
    add("Capacity", e.capacity);
    add("Cost", e.cost);
    add("Network", e.path);
    add("Auth", e.auth);
    const width = Math.max(4, Math.min(100, (e.ms / Math.max(maxMs, 1)) * 100));
    return `<div class="entry">
      <div class="op"><span>${esc(e.op)}</span><span class="eng">${esc(e.engine || "")} · ${e.ms} ms</span></div>
      <div class="bar" aria-hidden="true"><span style="width:${width}%"></span></div>
      <pre>${esc(e.request)}</pre>
      <dl>${rows.join("")}</dl>
      ${e.plan ? `<pre>${esc(e.plan)}</pre>` : ""}
      ${e.note ? `<p class="note">${esc(e.note)}</p>` : ""}
      ${e.error ? `<p class="err">${esc(e.error)}</p>` : ""}
      ${learn ? `<a class="learn-link" href="${learn}" target="_blank" rel="noopener">101: What happened to the data? <span aria-hidden="true">↗</span></a>` : ""}
    </div>`;
  }
  /* ---------------- 101 lessons: the call goes to the lesson tab through localStorage */
  const LEARN_KEY = "lm_learn";
  function keepForLesson(rec) {
    let all = {};
    try { all = JSON.parse(localStorage.getItem(LEARN_KEY) || "{}"); } catch (e) { all = {}; }
    const id = `${Date.now().toString(36)}-${callNo}`;
    let data = rec.data;
    if (JSON.stringify(data ?? null).length > 60000) data = undefined;   // keep localStorage small
    all[id] = { ...rec, data, at: Date.now(), page: location.pathname };
    const ids = Object.keys(all).sort((a, b) => all[a].at - all[b].at);
    while (ids.length > 25) delete all[ids.shift()];
    try { localStorage.setItem(LEARN_KEY, JSON.stringify(all)); return id; } catch (e) { return null; }
  }

  function addCall({ label, url, method, entries, ms, ok, source, background, data }) {
    $("#bts-empty").hidden = true;
    callNo += 1;
    const engine = (url.match(/^\/(\w+)\//) || [])[1];
    const k = entries.length ? keepForLesson({ label, url, method, entries, ms, ok, engine, data }) : null;
    const learn = (e, i) => engine ? `/${engine}/learn?${new URLSearchParams({ op: e.op, ...(k ? { k, i } : {}) })}` : "";
    const li = document.createElement("li");
    li.className = "call" + (ok ? "" : " failed") + (background ? " background" : "");
    const maxMs = Math.max(...entries.map((e) => e.ms || 0), 1);
    li.innerHTML = `<div class="call-head"><strong>${callNo}. ${esc(label)}</strong><span class="ms">${ms} ms</span>
      <span class="src">${esc(method)} ${esc(url)} → ${esc(ENGINE_LABEL[engine] || engine)} Engine App</span></div>
      ${entries.map((e, i) => renderEntry(e, maxMs, learn(e, i))).join("") || '<div class="entry"><p class="note">The Engine App answered without an Engine call.</p></div>'}`;
    if (source) {
      li.addEventListener("mouseenter", () => document.querySelectorAll(source).forEach((el) => el.classList.add("source-hl")));
      li.addEventListener("mouseleave", () => document.querySelectorAll(".source-hl").forEach((el) => el.classList.remove("source-hl")));
    }
    list.appendChild(li);
  }
  $("#bts-clear").addEventListener("click", () => { list.innerHTML = ""; callNo = 0; $("#bts-empty").hidden = false; });

  /**
   * Call an Engine App API and show the call in the panel.
   * opts: {method, body, form, label, source (CSS selector of the shop element), background}
   */
  async function api(url, opts = {}) {
    const method = opts.method || (opts.body || opts.form ? "POST" : "GET");
    const init = { method, headers: {} };
    if (opts.body) { init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(opts.body); }
    if (opts.form) init.body = opts.form;
    if (opts.adminKey) init.headers["X-Admin-Key"] = opts.adminKey;
    const t0 = performance.now();
    let json;
    try {
      const res = await fetch(url, init);
      json = await res.json().catch(() => ({ ok: false, error: `HTTP ${res.status}: the Engine App did not return JSON.` }));
    } catch (err) {
      json = { ok: false, error: `The request did not reach the Engine App: ${err.message}` };
    }
    const ms = Math.round(performance.now() - t0);
    addCall({ label: opts.label || url, url, method, entries: json.trace || [], ms, ok: json.ok !== false, source: opts.source, background: opts.background, data: json.data });
    if (json.ok === false) { const e = new Error(json.error || "The call failed."); e.payload = json; throw e; }
    return json.data;
  }

  /* ---------------- Cart badge (kept in localStorage; the cart page refreshes it from DynamoDB) */
  function setCartCount(n) { localStorage.setItem("lm_cart_count", String(n)); $("#cart-count").textContent = n; }
  setCartCount(Number(localStorage.getItem("lm_cart_count") || 0));

  /* ---------------- Header search suggestions (OpenSearch) */
  const q = $("#header-q"), sug = $("#suggest");
  let timer;
  q.addEventListener("input", () => {
    clearTimeout(timer);
    if (q.value.trim().length < 3) { sug.hidden = true; return; }
    timer = setTimeout(async () => {
      try {
        const rows = await api(`/opensearch/api/suggest?q=${encodeURIComponent(q.value.trim())}`, { label: "Search suggestions", source: "#header-q" });
        sug.innerHTML = rows.map((r) => `<a href="/p/${r.product_id}">${esc(r.name)} <small>${esc(r.category)}</small></a>`).join("");
        sug.hidden = rows.length === 0;
      } catch (e) { sug.hidden = true; }
    }, 250);
  });
  document.addEventListener("click", (e) => { if (!sug.contains(e.target)) sug.hidden = true; });

  /* ---------------- Tutorial
   * The header toggle turns the Tutorial on or off for all pages (lm_tutor_off).
   * Close and Finish close it for this page only (lm_tutor_done_<page>). */
  const tutor = $("#tutor"), tut = LM.tutorial || {};
  const steps = tut.steps || [];
  const tKey = `lm_tutor_${LM.page.id}`, doneKey = `lm_tutor_done_${LM.page.id}`;
  let stepNo = Number(localStorage.getItem(tKey) || 0);
  const tutorOn = () => localStorage.getItem("lm_tutor_off") !== "1";
  const pageDone = () => localStorage.getItem(doneKey) === "1";
  const smooth = () => (matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth");
  const mini = $("#tutor-mini");
  function renderTutor(move = false) {
    document.querySelectorAll(".spotlight").forEach((el) => el.classList.remove("spotlight"));
    if (!steps.length || !tutorOn() || pageDone()) { tutor.hidden = true; mini.hidden = true; syncToggle(); return; }
    stepNo = Math.max(0, Math.min(stepNo, steps.length - 1));
    const s = steps[stepNo], last = stepNo === steps.length - 1;
    tutor.hidden = false;
    $("#tutor-step").textContent = `Step ${stepNo + 1} of ${steps.length}`;
    $("#tutor-dots").innerHTML = steps.map((_, i) => `<i class="${i < stepNo ? "done" : i === stepNo ? "now" : ""}"></i>`).join("");
    $("#tutor-title").textContent = s.title;
    $("#tutor-text").textContent = s.text;
    $("#tutor-mini-text").textContent = `Step ${stepNo + 1} of ${steps.length}: ${s.title}`;
    document.querySelectorAll("[data-tutor=back]").forEach((b) => { b.disabled = stepNo === 0; });
    document.querySelectorAll("[data-tutor=next]").forEach((b) => { b.textContent = last ? "Finish" : "Next"; });
    tutor.classList.remove("tick"); void tutor.offsetWidth; tutor.classList.add("tick");
    const targets = s.target ? [...document.querySelectorAll(s.target)] : [];
    targets.forEach((el) => el.classList.add("spotlight"));
    if (move && targets[0]) targets[0].scrollIntoView({ behavior: smooth(), block: "center" });
    localStorage.setItem(tKey, String(stepNo));
    syncToggle();
  }
  function closeForPage() { localStorage.setItem(doneKey, "1"); localStorage.removeItem(tKey); renderTutor(); }
  document.querySelectorAll("[data-tutor=next]").forEach((b) => b.addEventListener("click", () => {
    if (stepNo === steps.length - 1) { closeForPage(); return; }
    stepNo += 1; renderTutor(true);
  }));
  document.querySelectorAll("[data-tutor=back]").forEach((b) => b.addEventListener("click", () => { stepNo -= 1; renderTutor(true); }));
  document.querySelectorAll("[data-tutor=close]").forEach((b) => b.addEventListener("click", closeForPage));
  const toggle = $("#tutor-toggle");
  function syncToggle() { toggle.setAttribute("aria-pressed", tutor.hidden ? "false" : "true"); }
  toggle.addEventListener("click", () => {
    if (!tutor.hidden) localStorage.setItem("lm_tutor_off", "1");
    else { localStorage.setItem("lm_tutor_off", "0"); localStorage.removeItem(doneKey); stepNo = 0; }
    renderTutor();
    if (!tutor.hidden) window.scrollTo({ top: 0, behavior: smooth() });
  });
  // When the Tutorial box is out of view (the step target is lower on the page), a small bar keeps Back and Next near.
  new IntersectionObserver(([en]) => { mini.hidden = tutor.hidden || en.isIntersecting; }).observe(tutor);

  /* ---------------- Guided shopping journey */
  const jbar = $("#journey"), stops = (LM.journey && LM.journey.stops) || [];
  function renderJourney() {
    const at = Number(localStorage.getItem("lm_journey") ?? -1);
    if (at < 0 || !stops.length) { jbar.hidden = true; return; }
    const here = stops.findIndex((s) => s.page === LM.page.id);
    const now = here >= 0 ? here : at;
    if (here >= 0 && here > at) localStorage.setItem("lm_journey", String(here));
    const next = stops[now + 1];
    jbar.hidden = false;
    jbar.innerHTML = `<strong>Guided journey</strong>
      <ol aria-label="Journey progress">${stops.map((s, i) => `<li class="${i < now ? "done" : i === now ? "now" : ""}" title="${esc(s.title)}"></li>`).join("")}</ol>
      <span>${esc(stops[now].title)}: ${esc(stops[now].text)}</span>
      ${next ? `<a href="${next.href}">Next stop: ${esc(next.title)}</a>` : "<span>You finished the journey.</span>"}
      <button class="quiet" type="button" id="journey-stop">Stop the journey</button>`;
    $("#journey-stop").addEventListener("click", () => { localStorage.setItem("lm_journey", "-1"); renderJourney(); });
  }
  function startJourney() {
    localStorage.setItem("lm_journey", "0"); localStorage.setItem("lm_tutor_off", "0");
    Object.keys(localStorage).filter((k) => k.startsWith("lm_tutor_done_")).forEach((k) => localStorage.removeItem(k));
    window.location.href = stops[0].href;
  }
  renderJourney();
  renderTutor();

  /* ---------------- Session (ElastiCache, background call on each page) */
  api("/elasticache/api/session", { body: { page: location.pathname }, label: "Update the session", background: true }).catch(() => {});

  /* ---------------- Small UI helpers for pages */
  function stars(r) { const n = Math.round(r || 0); return "★".repeat(n) + "☆".repeat(5 - n); }
  function productCard(p, opts = {}) {
    return `<a class="card" href="/p/${p.product_id}" data-product="${p.product_id}">
      <img src="/s3/api/img/${p.product_id}" alt="" loading="lazy" width="240" height="240">
      <div class="body"><span class="name">${esc(p.name)}</span>
      <span class="meta">${esc(p.category || "")}${p.rating ? ` <span class="stars" aria-label="${p.rating} of 5">${stars(p.rating)}</span>` : ""}</span>
      ${p.price !== undefined ? `<span class="price">${tl(p.price)}</span>` : ""}
      ${opts.extra || ""}</div></a>`;
  }
  function segmented(container, onChange) {
    container.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      container.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
      onChange(b.dataset.value);
    }));
    return () => (container.querySelector('[aria-pressed="true"]') || container.querySelector("button")).dataset.value;
  }
  function errorBox(el, err) { el.innerHTML = `<div class="notice bad">${esc(err.message)}</div>`; }
  async function addToCart(p, qty = 1, limit = true, source) {
    const data = await api("/dynamodb/api/cart/items", { body: { product_id: p.product_id, name: p.name, unit_price: p.price, qty, limit },
      label: "Add to cart", source });
    setCartCount(data.items.reduce((s, i) => s + i.qty, 0));
    return data;
  }

  window.lm = { api, esc, tl, stars, productCard, segmented, errorBox, setCartCount, addToCart, persona, visitor, startJourney, $ };
})();
