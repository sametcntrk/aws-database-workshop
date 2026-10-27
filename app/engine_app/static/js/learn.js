/* Lale Market 101: reads the clicked call from localStorage, gives small helpers to the lesson script. */
(function () {
  "use strict";
  const $ = (sel, root = document) => root.querySelector(sel);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const tl = (n) => new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY", maximumFractionDigits: 2 }).format(n);

  const qs = new URLSearchParams(location.search);
  let rec = null;
  try { rec = JSON.parse(localStorage.getItem("lm_learn") || "{}")[qs.get("k")] || null; } catch (e) { rec = null; }
  const entry = rec ? rec.entries[Number(qs.get("i") || 0)] || rec.entries[0] : null;
  if (rec && rec.page) $("#learn-back").href = rec.page;

  /** fetch an Engine App API; returns {data, trace}. The 101 page has no Behind-the-Scenes Panel. */
  async function call(url, body) {
    const init = body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {};
    const res = await fetch(url, init);
    const json = await res.json().catch(() => ({ ok: false, error: `HTTP ${res.status}` }));
    if (json.ok === false) throw new Error(json.error || "The call failed.");
    return { data: json.data, trace: json.trace || [] };
  }

  /** Make a call record like the one lm.js keeps, for a page opened without a clicked call. */
  async function sample(url, label) {
    const t0 = performance.now();
    const r = await call(url);
    return { rec: { label, url, method: "GET", entries: r.trace, data: r.data, ms: Math.round(performance.now() - t0), sample: true }, entry: r.trace[0] };
  }

  /** Show "your call" in the hero. */
  function showCall(r, e) {
    const box = $("#yourcall");
    box.hidden = false;
    box.innerHTML = `${r.sample ? `<p class="yourcall-note">You opened this page directly, so below is an example call. Make your own call in the shop and click the <b>101</b> link in the panel to see your own data.</p>` : ""}
      <dl>
        <div><dt>Action in the shop</dt><dd>${esc(r.label)}</dd></div>
        <div><dt>Engine operation</dt><dd><code>${esc(e.op)}</code></dd></div>
        <div><dt>Result</dt><dd>${e.items !== undefined ? `${e.items} records` : "–"}</dd></div>
        <div><dt>Time in the Engine</dt><dd>${e.ms} ms</dd></div>
      </dl>`;
  }

  /** Pretty JSON; top-level keys in `keep` are marked, the others are dimmed. */
  function jsonView(obj, keep) {
    const val = (v) => esc(JSON.stringify(v, null, 2)).replace(/\n/g, "\n  ");
    const rows = Object.entries(obj).map(([k, v]) => {
      const cls = keep ? (keep.has(k) ? "kept" : "dropped") : "";
      return `<span class="jrow ${cls}">  <span class="jk">"${esc(k)}"</span>: ${val(v)}</span>`;
    });
    return `<pre class="json">{\n${rows.join(",\n")}\n}</pre>`;
  }

  /* ---------------- Tree: the nested structure of one record, with a type label for each field */
  const TYPE = (v) => (v === null ? "null" : Array.isArray(v) ? `list, ${v.length} items` : typeof v === "object" ? `object, ${Object.keys(v).length} fields`
    : typeof v === "number" ? "number" : typeof v === "boolean" ? "true/false" : "text");
  /** mark(path) returns a CSS class for a field ("kept", "dropped", "key", ...) or "" */
  function tree(obj, mark = () => "", path = "") {
    return `<ul class="tree">${Object.entries(obj).map(([k, v]) => {
      const p = path ? `${path}.${k}` : k, cls = mark(p);
      const head = `<span class="tk">${esc(k)}</span><span class="tt">${TYPE(v)}</span>`;
      if (v && typeof v === "object") {
        return `<li class="${cls}"><details open><summary>${head}</summary>${tree(v, mark, p)}</details></li>`;
      }
      return `<li class="${cls}">${head}<span class="tv">${esc(typeof v === "string" ? `"${v}"` : v)}</span></li>`;
    }).join("")}</ul>`;
  }

  /* ---------------- Zoom: the big picture (every record as a tile) -> the selected record -> its nested structure
   * opts: { groups: [{label, items: [{id, title, cls}]}], selected, overview (html), onSelect: async (id) => html } */
  function zoom(el, opts) {
    el.classList.add("zoom");
    el.innerHTML = `<div class="zoom-big"><div class="zoom-over">${opts.overview || ""}</div>
        <div class="shelves">${opts.groups.map((g) => `<div class="shelf"><span class="shelf-label">${esc(g.label)}</span><div class="tiles">
          ${g.items.map((it) => `<button type="button" class="tile ${it.cls || ""}" data-id="${esc(it.id)}" title="${esc(it.title)}" aria-label="${esc(it.title)}"></button>`).join("")}
        </div></div>`).join("")}</div>
        ${opts.legend ? `<div class="legend">${opts.legend}</div>` : ""}</div>
      <div class="zoom-link" aria-hidden="true"></div>
      <div class="zoom-lens" aria-live="polite"><p class="wait">Select a square.</p></div>`;
    const lens = $(".zoom-lens", el);
    async function select(id) {
      el.querySelectorAll(".tile.sel").forEach((t) => t.classList.remove("sel"));
      const tile = el.querySelector(`.tile[data-id="${CSS.escape(id)}"]`);
      if (tile) tile.classList.add("sel");
      lens.classList.add("busy");
      try { lens.innerHTML = await opts.onSelect(id); } catch (e) { lens.innerHTML = `<p>Could not read the record: ${esc(e.message)}</p>`; }
      lens.classList.remove("busy"); lens.classList.remove("in"); void lens.offsetWidth; lens.classList.add("in");
    }
    el.addEventListener("click", (e) => { const t = e.target.closest(".tile"); if (t) select(t.dataset.id); });
    if (opts.selected) select(opts.selected);
    return { select };
  }

  /* ---------------- Generic lesson (templates/learn/lesson.html, content from lessons/<engine>.yaml) */
  function walk(v, fn) {
    if (Array.isArray(v)) v.forEach((x) => walk(x, fn));
    else if (v && typeof v === "object") { fn(v); Object.values(v).forEach((x) => walk(x, fn)); }
  }
  /** Values from the call that the big picture marks. spec: "path" | "query:<name>" | "data:<key>" | "keys" (one or a list) */
  function focusOf(spec, r) {
    if (!spec || !r) return [];
    const u = new URL(r.url, location.origin), out = [];
    for (const one of [].concat(spec)) {
      if (one === "path") out.push(decodeURIComponent(u.pathname.split("/").pop()));
      else if (one.startsWith("query:")) { const v = u.searchParams.get(one.slice(6)); if (v) out.push(v); }
      else if (one.startsWith("data:")) { const key = one.slice(5); walk(r.data, (o) => { if (o[key] !== undefined && o[key] !== null) out.push(String(o[key])); }); }
      else if (one === "keys") r.entries.forEach((e) => { const m = (e.request || "").match(/^[A-Z]+\s+(\S+)/); if (m) out.push(m[1]); });
    }
    return [...new Set(out)].slice(0, 80);
  }

  function stepHtml(op, x, en) {
    const facts = en ? [en.items !== undefined ? `<span><b>${en.items}</b> records</span>` : "", `<span><b>${en.ms}</b> ms</span>`,
      en.capacity ? `<span>Capacity: <b>${esc(en.capacity)}</b></span>` : "", en.cost ? `<span>Cost: <b>${esc(en.cost)}</b></span>` : ""].join("") : "";
    return `<li><h3>${esc(x.title || op)} <code>${esc(op)}</code></h3><div class="sp">${x.text || ""}
      ${en ? `<div class="facts">${facts}</div>
        ${en.note ? `<p class="enote"><span>Note in the panel:</span> ${esc(en.note)}</p>` : ""}
        ${en.error ? `<p class="enote bad">${esc(en.error)}</p>` : ""}
        <details class="req"><summary>Real request</summary><pre>${esc(en.request)}</pre>${en.plan ? `<pre>${esc(en.plan)}</pre>` : ""}</details>` : ""}</div></li>`;
  }

  async function renderLesson() {
    const C = window.LESSON, P = window.LEARN.prefix;
    let r = rec, e = entry;
    if (!r && C.sample) { try { ({ rec: r, entry: e } = await sample(C.sample.url, C.sample.label)); } catch (err) { r = null; } }
    if (r) showCall(r, e);
    else if (C.need) { const box = $("#yourcall"); box.hidden = false; box.innerHTML = `<p class="yourcall-note">${C.need}</p>`; }

    if (C.big) {
      try {
        const focus = focusOf(C.focus, r).join(",");
        const ov = (await call(`${P}/api/learn/overview?${new URLSearchParams({ lesson: C.id, focus })}`)).data;
        const first = ov.groups.flatMap((g) => g.items);
        zoom($("#zoom"), {
          overview: `<h3>${esc(ov.title)}</h3><p>${esc(ov.text || "")}</p>
            <div class="facts">${(ov.facts || []).map(([v, l]) => `<span><b>${esc(v)}</b> ${esc(l)}</span>`).join("")}</div>`,
          groups: ov.groups.map((g) => ({ label: g.label, items: g.items.map((it) => ({ id: it.id, title: it.title, cls: it.hit ? "hit" : "" })) })),
          legend: `<span><i class="h"></i>${esc(ov.hit_label || "Used by your call")}</span><span><i class="s"></i>Selected</span><span><i class="d"></i>Other records</span>`,
          selected: ov.selected || (first.find((it) => it.hit) || first[0] || {}).id,
          onSelect: async (id) => {
            const it = (await call(`${P}/api/learn/item?${new URLSearchParams({ lesson: C.id, id })}`)).data;
            return `<div class="lens-head"><span class="tile sel"></span><div><h3>${esc(it.title)}</h3><p>${esc(it.sub || "")}</p></div></div>
              ${tree(it.record, (p) => (it.marks || {})[p] || "")}
              ${C.big.legend ? `<div class="legend">${C.big.legend}</div>` : ""}`;
          },
        });
      } catch (err) { $("#zoom").innerHTML = `<p>Could not read the big picture: ${esc(err.message)}</p>`; }
    }

    const ex = C.explain || {};
    if (r) {
      $("#qsteps").innerHTML = r.entries.map((en) => stepHtml(en.op, ex[en.op] || {}, en)).join("");
    } else {
      $("#steps-intro").textContent = "You have no call yet. In the shop, these operations usually run in this order:";
      $("#qsteps").innerHTML = Object.entries(ex).map(([op, x]) => stepHtml(op, x, null)).join("");
    }
  }

  window.L = { $, esc, tl, rec, entry, call, sample, showCall, jsonView, tree, zoom, focusOf, renderLesson };
})();
