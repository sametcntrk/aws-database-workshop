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
    if (json.ok === false) throw new Error(json.error || "Çağrı başarısız oldu.");
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
    box.innerHTML = `${r.sample ? `<p class="yourcall-note">Bu sayfayı doğrudan açtın. Aşağıda örnek bir çağrı var: mağazada kendi çağrını yapıp panelden <b>101</b> bağlantısına tıklarsan kendi verini görürsün.</p>` : ""}
      <dl>
        <div><dt>Mağazadaki işlem</dt><dd>${esc(r.label)}</dd></div>
        <div><dt>Engine işlemi</dt><dd><code>${esc(e.op)}</code></dd></div>
        <div><dt>Sonuç</dt><dd>${e.items !== undefined ? `${e.items} kayıt` : "–"}</dd></div>
        <div><dt>Engine'de geçen süre</dt><dd>${e.ms} ms</dd></div>
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
  const TYPE = (v) => (v === null ? "boş" : Array.isArray(v) ? `liste, ${v.length} öğe` : typeof v === "object" ? `nesne, ${Object.keys(v).length} alan`
    : typeof v === "number" ? "sayı" : typeof v === "boolean" ? "doğru/yanlış" : "metin");
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
      <div class="zoom-lens" aria-live="polite"><p class="wait">Bir kare seç.</p></div>`;
    const lens = $(".zoom-lens", el);
    async function select(id) {
      el.querySelectorAll(".tile.sel").forEach((t) => t.classList.remove("sel"));
      const tile = el.querySelector(`.tile[data-id="${CSS.escape(id)}"]`);
      if (tile) tile.classList.add("sel");
      lens.classList.add("busy");
      try { lens.innerHTML = await opts.onSelect(id); } catch (e) { lens.innerHTML = `<p>Kayıt okunamadı: ${esc(e.message)}</p>`; }
      lens.classList.remove("busy"); lens.classList.remove("in"); void lens.offsetWidth; lens.classList.add("in");
    }
    el.addEventListener("click", (e) => { const t = e.target.closest(".tile"); if (t) select(t.dataset.id); });
    if (opts.selected) select(opts.selected);
    return { select };
  }

  window.L = { $, esc, tl, rec, entry, call, sample, showCall, jsonView, tree, zoom };
})();
