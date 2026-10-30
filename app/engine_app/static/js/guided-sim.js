/* Simulations of the "Perde arkası" panel of the Guided mission (mission.js). One renderer, one function per visual kind.
 * The data of each simulation is in tutorials/guided.yaml (step.panel.sim). Usage:
 *   const sim = GuidedSim.render(box, spec);   sim.play(); sim.highlight("filter"); sim.highlight(null);
 * Every kind builds a list of frames per lane. The controls step all lanes together, so a lane with less work ends first.
 * prefers-reduced-motion: Oynat shows the last frame at once.
 */
(function () {
  "use strict";
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const TICK_MS = 900;

  /* ---------- index-vs-scan: the same filter + sort with an index (left) and with a collection scan (right) */
  function indexVsScan(spec) {
    const rows = spec.rows, cols = spec.columns;
    const [fField, fValue] = spec.filter, [sField, sDir] = spec.sort;
    const desc = sDir === "desc";
    const bySort = (a, b) => (desc ? b[sField] - a[sField] : a[sField] - b[sField]);
    const matches = rows.filter((r) => String(r[fField]) === String(fValue));
    const ordered = [...matches].sort(bySort);
    // The index: one entry per row, ordered by the filter field, then by the sort field. Each entry points to one row.
    const entries = [...rows].sort((a, b) => String(a[fField]).localeCompare(String(b[fField]), "tr") || bySort(a, b));
    const name = (r) => `${r.name} (${r.id})`;

    const base = { active: null, entry: null, range: false, read: [], hit: [], miss: [], result: [], sorted: false, sorting: false, done: false };
    const idx = [{ ...base, say: "Başlamak için Oynat'a bas." }];
    let s = { ...base };
    s = { ...s, range: true, say: `Index'te "${fValue}" bölümüne doğrudan gidildi. Index sıralı olduğu için ${fValue} kayıtları yan yana ve zaten ${sField === "rating" ? "puan" : sField} sırasında duruyor. Henüz hiç doküman okunmadı.` };
    idx.push(s);
    ordered.forEach((r, k) => {
      s = { ...s, active: r.id, entry: entries.indexOf(r), read: [...s.read, r.id], hit: [...s.hit, r.id], result: [...s.result, r.id], sorted: true,
        say: `Index ${k + 1}. kaydı gösteriyor: ${name(r)}. Bu doküman okundu ve doğrudan sonuca eklendi.` };
      idx.push(s);
    });
    idx.push({ ...s, active: null, entry: null, done: true,
      say: `Bitti. ${ordered.length} doküman okundu, ${ordered.length}'ü de sonuca girdi. Sonuç zaten sıralı geldi, ayrıca sıralama yapılmadı.` });

    const scan = [{ ...base, say: "Başlamak için Oynat'a bas." }];
    s = { ...base };
    rows.forEach((r, k) => {
      const ok = String(r[fField]) === String(fValue);
      s = { ...s, active: r.id, read: [...s.read, r.id], hit: ok ? [...s.hit, r.id] : s.hit, miss: ok ? s.miss : [...s.miss, r.id],
        result: ok ? [...s.result, r.id] : s.result,
        say: `${k + 1}. doküman okundu: ${name(r)}. Kategorisi ${r[fField]}. ${ok ? "✓ Eşleşti, kenara ayrıldı." : "✗ Eşleşmedi, atıldı."}` };
      scan.push(s);
    });
    s = { ...s, active: null, sorting: true, sorted: true, result: ordered.map((r) => r.id),
      say: `Eşleşen ${matches.length} doküman bellekte ${sField === "rating" ? "puana" : sField + " alanına"} göre sıralandı (SORT). Index olmadığı için bu ek bir iş.` };
    scan.push(s);
    scan.push({ ...s, sorting: false, done: true,
      say: `Bitti. ${rows.length} dokümanın hepsi okundu, ${matches.length}'ü sonuca girdi, ${rows.length - matches.length}'ü boşuna okundu.` });

    const th = cols.map(([k, label]) => `<th data-hl="columns${k === fField ? " filter" : ""}${k === sField ? " sort" : ""}">${esc(label)}</th>`).join("");
    const table = (mark) => `<table class="gs-table" data-hl="table"><thead><tr>${th}${mark ? "<th class=\"gs-mark\"></th>" : ""}</tr></thead><tbody>${rows.map((r) =>
      `<tr data-id="${esc(r.id)}">${cols.map(([k]) => `<td data-hl="${k === fField ? "filter" : ""}${k === sField ? " sort" : ""}">${esc(r[k])}</td>`).join("")}${mark ? "<td class=\"gs-mark\"></td>" : ""}</tr>`).join("")}</tbody></table>`;
    const lane = (id, title, body, hl) => `<section class="gs-lane" data-lane="${id}" data-hl="${hl}">
      <header><h4>${esc(title)}</h4><span class="gs-count">Okunan doküman: <b>0</b></span></header>
      <div class="gs-body">${body}</div>
      <div class="gs-result" data-hl="result"><span>Sonuç</span><ol></ol></div>
      <p class="gs-say" aria-live="polite"></p></section>`;
    const indexList = `<div class="gs-index" data-hl="index"><div class="gs-index-cap">Index ${esc(spec.index_name || "")}</div><ol>${entries.map((r, k) =>
      `<li data-k="${k}"><span>${esc(r[fField])}</span><span>${esc(r[sField])}</span><span>→ ${esc(r.id)}</span></li>`).join("")}</ol></div>`;
    const html = `<div class="gs-lanes">${lane("index", "Index ile", indexList + table(false), "index")}${lane("scan", "Index olmadan (collection scan)", table(true), "scan")}</div>
      <p class="gs-sum" hidden>Index ile <b>${ordered.length}</b> doküman okundu. Index olmadan <b>${rows.length}</b> doküman okundu ve bir de sıralama yapıldı.
      Sonuç ikisinde de aynı: ${ordered.map((r) => esc(r.id)).join(", ")}.</p>`;

    function paint(root, laneId, f) {
      const L = root.querySelector(`[data-lane="${laneId}"]`);
      L.querySelector(".gs-count b").textContent = f.read.length;
      L.classList.toggle("done", f.done);
      L.querySelectorAll("tbody tr").forEach((tr) => {
        const id = tr.dataset.id;
        tr.classList.toggle("active", f.active === id);
        tr.classList.toggle("read", f.read.includes(id));
        tr.classList.toggle("hit", f.hit.includes(id));
        tr.classList.toggle("miss", f.miss.includes(id));
        const m = tr.querySelector(".gs-mark");
        if (m) m.textContent = f.hit.includes(id) ? "✓" : f.miss.includes(id) ? "✗" : "";
      });
      L.querySelectorAll(".gs-index li").forEach((li) => {
        const r = entries[Number(li.dataset.k)];
        li.classList.toggle("range", f.range && String(r[fField]) === String(fValue));
        li.classList.toggle("active", f.entry === Number(li.dataset.k));
      });
      L.querySelector(".gs-result").classList.toggle("sorting", f.sorting);
      L.querySelector(".gs-result ol").innerHTML = f.result.map((id) => {
        const r = rows.find((x) => x.id === id);
        return `<li class="${f.sorted ? "" : "unsorted"}">${esc(r.name)} <small>${esc(r[sField])}</small></li>`;
      }).join("") || "<li class=\"empty\">henüz boş</li>";
      L.querySelector(".gs-say").textContent = f.say;
    }
    return { html, lanes: { index: idx, scan }, paint, final: (root) => { root.querySelector(".gs-sum").hidden = false; } };
  }

  const KINDS = { "index-vs-scan": indexVsScan };

  function render(box, spec) {
    const kind = KINDS[spec.kind];
    if (!kind) { box.innerHTML = `<p class="gs-missing">Bu simülasyon türü henüz yok: ${esc(spec.kind)}</p>`; return { play() {}, highlight() {} }; }
    const k = kind(spec);
    const total = Math.max(...Object.values(k.lanes).map((f) => f.length)) - 1;
    box.innerHTML = `<div class="gs gs-${esc(spec.kind)}">${spec.caption ? `<p class="gs-caption">${esc(spec.caption)}</p>` : ""}
      <div class="gs-controls"><button type="button" data-g="play">▶ Oynat</button><button type="button" data-g="step">⏭ Sonraki adım</button>
      <button type="button" data-g="reset">↺ Baştan</button><span class="gs-tick"></span></div>${k.html}</div>`;
    const root = box.firstElementChild;
    let t = 0, timer = 0;
    const show = () => {
      Object.entries(k.lanes).forEach(([id, frames]) => k.paint(root, id, frames[Math.min(t, frames.length - 1)]));
      root.querySelector(".gs-tick").textContent = `Adım ${t} / ${total}`;
      if (t >= total) { k.final(root); stop(); } else root.querySelector(".gs-sum") && (root.querySelector(".gs-sum").hidden = true);
      root.querySelector("[data-g=play]").textContent = timer ? "❚❚ Durdur" : t >= total ? "▶ Tekrar oynat" : "▶ Oynat";
    };
    function stop() { clearInterval(timer); timer = 0; }
    function play() {
      if (timer) { stop(); show(); return; }
      if (t >= total) t = 0;
      if (REDUCED) { t = total; show(); return; }
      t += 1;
      timer = setInterval(() => { t += 1; show(); }, TICK_MS);
      show();
    }
    root.querySelector("[data-g=play]").addEventListener("click", play);
    root.querySelector("[data-g=step]").addEventListener("click", () => { stop(); t = t >= total ? 0 : t + 1; show(); });
    root.querySelector("[data-g=reset]").addEventListener("click", () => { stop(); t = 0; show(); });
    show();
    return {
      play,
      highlight(key) {
        root.querySelectorAll(".gs-hl").forEach((el) => el.classList.remove("gs-hl"));
        if (key) root.querySelectorAll(`[data-hl~="${key}"]`).forEach((el) => el.classList.add("gs-hl"));
      },
    };
  }

  window.GuidedSim = { render };
})();
