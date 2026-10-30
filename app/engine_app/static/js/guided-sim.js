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
  const TICK_MS = 900;   // a spec can set its own tick_ms

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
    // Who works in each frame: the app sends the command and gets the documents back; the database reads in between.
    const APP = "Uygulama", DB = spec.engine_label || "DocumentDB", L = spec.labels || {};
    const wrap = (frames, send, back) => [frames[0], { ...frames[1], ...base, who: APP, say: send }, ...frames.slice(1).map((f) => ({ ...f, who: f.who || DB })),
      { ...frames[frames.length - 1], who: APP, say: back }];
    idx.splice(0, idx.length, ...wrap(idx, spec.send_index || "Uygulama find komutunu gönderiyor. Komutta index adı yok; DocumentDB uygun index'i kendisi seçecek.",
      spec.back_index || `Uygulama ${ordered.length} dokümanı aldı ve tarayıcıya gönderdi.`));
    scan.splice(0, scan.length, ...wrap(scan, spec.send_scan || "Uygulama aynı find komutunu, sonuna hint ekleyerek gönderiyor: \"index'i kullanma, baştan sona oku\".",
      spec.back_scan || `Uygulama ${matches.length} dokümanı aldı ve tarayıcıya gönderdi. Liste soldakiyle aynı.`));
    const actors = `<div class="gs-actors" aria-hidden="true"><span data-a="app" data-hl="app">Uygulama (sunucudaki program)</span><i>⇄</i><span data-a="db" data-hl="db">${esc(DB)} (veritabanı)</span></div>`;
    const html = `${actors}<div class="gs-lanes">${lane("index", L.index || "Index ile", indexList + table(false), "index")}${lane("scan", L.scan || "Index olmadan (collection scan)", table(true), "scan")}</div>
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
      L.querySelector(".gs-say").innerHTML = `${f.who ? `<b class="gs-who ${f.who === APP ? "app" : "db"}">${esc(f.who)}</b> ` : ""}${esc(f.say)}`;
      L.dataset.who = f.who === APP ? "app" : f.who ? "db" : "";
      const ws = [...root.querySelectorAll(".gs-lane")].map((x) => x.dataset.who).filter(Boolean);
      root.querySelectorAll(".gs-actors [data-a]").forEach((x) => x.classList.toggle("on", ws.includes(x.dataset.a)));
    }
    return { html, lanes: { index: idx, scan }, paint, final: (root) => { root.querySelector(".gs-sum").hidden = false; } };
  }

  /* ---------- Shared parts of the kinds below: a lane with a title, a count, a body, a result box and a narration line */
  const shell = (id, title, body, o = {}) => `<section class="gs-lane" data-lane="${id}" data-hl="${o.hl || ""}">
      <header><h4>${esc(title)}</h4><span class="gs-count">${esc(o.count || "Okunan")}: <b>0</b></span></header>
      <div class="gs-body${o.col ? " col" : ""}">${body}</div>
      ${o.result === false ? "" : `<div class="gs-result" data-hl="result"><span>${esc(o.result || "Sonuç")}</span><ol></ol></div>`}
      <p class="gs-say" aria-live="polite"></p></section>`;
  const START = "Başlamak için Oynat'a bas.";
  const laneOf = (root, id) => root.querySelector(`[data-lane="${id}"]`);
  const chips = (L, items) => { L.querySelector(".gs-result ol").innerHTML = items.length ? items.join("") : '<li class="empty">henüz boş</li>'; };
  const summary = (text) => `<p class="gs-sum" hidden>${text}</p>`;
  const showSum = (root) => { const s = root.querySelector(".gs-sum"); if (s) s.hidden = false; };

  /* ---------- race: many buyers take the last pieces of one counter. Left: read, then write. Right: one atomic DECR. */
  function race(spec) {
    const DB = spec.engine_label || "ElastiCache";
    const stock = spec.stock, buyers = spec.buyers, key = spec.key || "stok";
    const naive = [{ counter: stock, rows: buyers.map(() => ({})), active: null, sold: 0, say: START }];
    let s = { counter: stock, rows: buyers.map(() => ({})), sold: 0 };
    for (let i = 0; i < buyers.length; i += 2) {
      const pair = [i, i + 1].filter((k) => k < buyers.length);
      pair.forEach((k) => {
        const rows = s.rows.map((r) => ({ ...r })); rows[k].read = s.counter;
        s = { ...s, rows, active: k, op: "get", who: DB,
          say: `${buyers[k]}: GET ${key} → ${s.counter}. "Stokta ${s.counter} parça var" diye düşünüyor.${pair.length > 1 && k === pair[1] ? ` ${buyers[pair[0]]} henüz yazmadı, o yüzden ikisi de aynı değeri gördü.` : ""}` };
        naive.push(s);
      });
      pair.forEach((k) => {
        const rows = s.rows.map((r) => ({ ...r })), read = rows[k].read;
        if (read > 0) { rows[k].wrote = read - 1; rows[k].won = true; } else rows[k].lost = true;
        s = { ...s, rows, active: k, op: "set", counter: read > 0 ? read - 1 : s.counter, sold: s.sold + (read > 0 ? 1 : 0), who: APP_NAME,
          say: read > 0 ? `${buyers[k]}: uygulama okunan ${read} değerine bakıp karar verdi ve SET ${key} ${read - 1} gönderdi. Satın aldı.${k === pair[1] && pair.length > 1 ? ` Ama ${buyers[pair[0]]} de aynı ${read} değerinden ${read - 1} yazmıştı: iki kişi tek bir parçayı aldı, sayaç sadece 1 azaldı.` : ""}`
            : `${buyers[k]}: uygulama okunan değere baktı: 0, satın alamadı.` };
        naive.push(s);
      });
    }
    const over = s.sold - stock;
    naive.push({ ...s, active: null, done: true, say: `Bitti. Stokta ${stock} parça vardı, ${s.sold} kişi satın aldı: ${over > 0 ? `${over} parça, olmayan bir parçaydı.` : "fazla satış yok."}` });

    const atomic = [{ counter: stock, rows: buyers.map(() => ({})), active: null, sold: 0, say: START }];
    let a = { counter: stock, rows: buyers.map(() => ({})), sold: 0 };
    buyers.forEach((b, k) => {
      const rows = a.rows.map((r) => ({ ...r })), v = a.counter - 1;
      rows[k].decr = v; if (v >= 0) rows[k].won = true; else rows[k].lost = true;
      a = { ...a, rows, active: k, op: "decr", counter: v, sold: a.sold + (v >= 0 ? 1 : 0), who: DB,
        say: `${b}: DECR ${key} → ${v}. ${v >= 0 ? "Sonuç 0 veya üstü: satın aldı." : "Sonuç 0'ın altında: parça kalmadı, satın alamadı."} Okuma ve yazma tek komut, araya kimse giremez.` };
      atomic.push(a);
    });
    atomic.push({ ...a, active: null, done: true, say: `Bitti. Tam ${a.sold} kişi satın aldı, stok kadar. Sayaç ${a.counter}'e indi ama eksi değerde kimse ürün almadı.` });

    const sendR = spec.send || `Uygulama ${buyers.length} alıcıyı aynı anda başlatıyor; her alıcı için ElastiCache'e kendi komutlarını gönderecek.`;
    const backR = spec.back || "Uygulama kazananları saydı, fazla satışı hesapladı ve sonucu tarayıcıya gönderdi.";
    naive.splice(0, naive.length, ...actorize(naive, sendR, backR, DB, { active: null }));
    atomic.splice(0, atomic.length, ...actorize(atomic, sendR, backR, DB, { active: null }));
    const table = (cols, kind) => `<table class="gs-table"><thead><tr>${cols.map(([k, l]) => `<th data-hl="${k}">${esc(l)}</th>`).join("")}</tr></thead>
      <tbody>${buyers.map((b, i) => `<tr data-i="${i}">${cols.map(([k]) => `<td data-k="${k}" data-hl="${k}">${k === "buyer" ? esc(b) : ""}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    const counter = `<div class="gs-counter" data-hl="counter"><span>${esc(key)}</span><b>${stock}</b><small>bellekteki sayaç</small></div>`;
    const html = `${actorBar(DB)}<div class="gs-lanes">${shell("naive", spec.labels?.naive || "Önce oku, sonra yaz", counter + table([["buyer", "Alıcı"], ["get", "GET ile okudu"], ["set", "SET ile yazdı"], ["res", "Sonuç"]]), { hl: "naive", count: "Satılan", result: false, col: true })}
      ${shell("atomic", spec.labels?.atomic || "Atomik DECR", counter + table([["buyer", "Alıcı"], ["decr", "DECR sonucu"], ["res", "Sonuç"]]), { hl: "atomic", count: "Satılan", result: false, col: true })}</div>
      ${summary(`Aynı ${buyers.length} alıcı, aynı ${stock} parça: "önce oku, sonra yaz" yolu ${s.sold} parça sattı, atomik DECR tam ${a.sold}.`)}`;
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = `${f.sold} / ${stock}`;
      L.classList.toggle("done", !!f.done);
      const c = L.querySelector(".gs-counter b"); c.textContent = f.counter; c.classList.toggle("neg", f.counter < 0);
      L.querySelectorAll("tbody tr").forEach((tr) => {
        const i = Number(tr.dataset.i), r = f.rows[i] || {};
        tr.classList.toggle("active", f.active === i);
        tr.classList.toggle("hit", !!r.won); tr.classList.toggle("miss", !!r.lost);
        const set = (k, v) => { const td = tr.querySelector(`[data-k="${k}"]`); if (td) td.textContent = v ?? ""; };
        set("get", r.read); set("set", r.wrote); set("decr", r.decr);
        set("res", r.won ? "✓ aldı" : r.lost ? "✗ alamadı" : "");
      });
      L.classList.toggle("over", !!f.done && f.sold > stock);
      sayWho(L, f);
    }
    return { html, lanes: { naive, atomic }, paint, final: showSum };
  }

  /* ---------- partition: Keyspaces / Cassandra wide rows. One INSERT into the user's partition, then one SELECT of it. */
  function partition(spec) {
    const parts = spec.partitions, me = parts.findIndex((p) => p.me), ins = spec.insert, cap = spec.app_limit || 8, lim = spec.read_limit || 40;
    const rowsOf = (p, withNew) => (withNew && p.me ? [{ ...ins, fresh: true }, ...p.rows] : p.rows);
    const APP = "Uygulama", DB = "Keyspaces";
    const frames = [{ say: START, phase: 0 }];
    const mine = rowsOf(parts[me], true), total = parts.reduce((n, p) => n + rowsOf(p, true).length, 0);
    // 1) the write: the app sends, the engine stores
    frames.push({ phase: 0, who: APP, say: spec.send_insert || `Sayfa açıldı. Uygulama "bu ürüne baktın" bilgisini bir INSERT komutuyla Keyspaces'e gönderiyor. Satırın user_id'si bu tarayıcının kimliği.` });
    frames.push({ phase: 1, who: DB, lit: me, say: `INSERT geldi: user_id = ${parts[me].label}. Keyspaces bu değere bakar ve satırın hangi partition'a gideceğini bulur. Diğer partition'lara dokunmaz.` });
    frames.push({ phase: 2, who: DB, lit: me, inserted: true, say: "Yeni satır partition'ın en üstüne girdi. Tablo satırları event_time'a göre yeniden eskiye sıralı tutuyor; sıralama yazarken yapılıyor, okurken değil." });
    // 2) the read: the app asks, the engine returns rows as they are
    frames.push({ phase: 3, who: APP, lit: me, inserted: true, select: true, touched: 1, say: spec.send_select || `Şimdi uygulama "Son baktıkların" şeridi için SELECT ... WHERE user_id = ${parts[me].label} LIMIT ${lim} gönderiyor.` });
    frames.push({ phase: 4, who: DB, lit: me, inserted: true, select: true, touched: 1, read: mine.length, stage: "db",
      say: `Keyspaces sadece bu partition'ı açtı ve satırları baştan okudu: ${mine.length} satır (en fazla ${lim} olabilirdi). Satırları olduğu gibi uygulamaya geri gönderdi. Hangisinin şeride gireceğine Keyspaces karar vermez.` });
    // 3) the app's own work: keep only views, drop repeats, at most `cap`
    const seen = new Set(), result = [], keep = [], skip = [];
    mine.forEach((r, k) => {
      let why;
      if (r.type !== "view") { why = `event_type = ${r.type}: bakılan ürün değil, atlandı.`; skip.push(k); }
      else if (seen.has(r.product)) { why = `${r.product} zaten listede, tekrar eklenmedi.`; skip.push(k); }
      else { seen.add(r.product); result.push(r.product); keep.push(k); why = `${r.product}: listeye eklendi.`; }
      frames.push({ phase: 5, who: APP, lit: me, inserted: true, select: true, touched: 1, read: mine.length, check: k + 1, stage: "app",
        keep: [...keep], skip: [...skip], result: [...result], say: `Uygulama ${k + 1}. satıra bakıyor (${r.time}). ${why}` });
    });
    frames.push({ ...frames[frames.length - 1], check: 0, done: true, stage: "out",
      say: spec.back ? `${spec.back} (Burada ${result.length} ürün var.)` : `Uygulama listenin en fazla ${cap} ürününü tarayıcıya gönderdi (burada ${result.length} ürün var). Tabloda ${total} satır var; Keyspaces sadece ${mine.length} tanesini okudu, süzmeyi uygulama yaptı.` });
    const block = (p, i) => `<div class="gs-part" data-p="${i}" data-hl="pk${p.me ? " where" : ""}">
      <div class="gs-part-key" data-hl="pk">user_id = <b>${esc(p.label)}</b>${p.me ? " <em>(sen)</em>" : ""}</div>
      <table class="gs-table"><thead><tr><th data-hl="ck">event_time ↓</th><th data-hl="type">event_type</th><th>product</th></tr></thead><tbody>
      ${rowsOf(p, true).map((r, k) => `<tr data-k="${k}" class="${r.fresh ? "fresh" : ""}" ${r.fresh ? 'data-hl="insert"' : ""}><td data-hl="ck">${esc(r.time)}</td><td data-hl="type">${esc(r.type)}</td><td>${esc(r.product)}</td></tr>`).join("")}
      </tbody></table></div>`;
    const html = `<div class="gs-lanes one">${shell("table", spec.title || "Keyspaces tablosu", `<div class="gs-pwrap"><div class="gs-actors" aria-hidden="true"><span data-a="app" data-hl="app">Uygulama (sunucudaki program)</span><i>⇄</i><span data-a="db" data-hl="db">Keyspaces (veritabanı)</span></div><div class="gs-parts">${parts.map(block).join("")}</div></div>`, { count: "Okunan satır", result: spec.result_title || "Son baktıkların" })}</div>
      ${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = `${f.read || 0} · dokunulan partition: ${f.touched || (f.phase >= 1 ? 1 : 0)} / ${parts.length}`;
      L.classList.toggle("done", !!f.done);
      L.querySelectorAll(".gs-part").forEach((el) => {
        const i = Number(el.dataset.p);
        el.classList.toggle("lit", f.lit === i); el.classList.toggle("dim", f.lit !== undefined && f.lit !== i);
        el.querySelectorAll("tbody tr").forEach((tr) => {
          const k = Number(tr.dataset.k);
          if (tr.classList.contains("fresh")) tr.hidden = !f.inserted;
          tr.classList.toggle("active", i === me && (f.check ? f.check === k + 1 : f.stage === "db"));
          tr.classList.toggle("read", i === me && (f.read || 0) > k);
          tr.classList.toggle("gs-keep", i === me && (f.keep || []).includes(k));
          tr.classList.toggle("gs-skip", i === me && (f.skip || []).includes(k));
        });
      });
      chips(L, (f.result || []).map((x) => `<li>${esc(x)}</li>`));
      L.querySelector(".gs-say").innerHTML = `${f.who ? `<b class="gs-who ${f.who === APP ? "app" : "db"}">${esc(f.who)}</b> ` : ""}${esc(f.say)}`;
      L.querySelectorAll(".gs-actors [data-a]").forEach((x) => x.classList.toggle("on", x.dataset.a === (f.who === APP ? "app" : f.who ? "db" : "")));
    }
    return { html, lanes: { table: frames }, paint, final: showSum };
  }

  /* ---------- condition-write: DynamoDB UpdateItem with and without a ConditionExpression, on the same item */
  function conditionWrite(spec) {
    const rows = spec.rows, ti = rows.findIndex((r) => r.target), cur = rows[ti].qty, add = spec.add, max = spec.max;
    const room = max - add, ok = cur <= room;
    const base = (say) => ({ say, active: null, qty: cur });
    const req = `UpdateItem geldi: ${rows[ti].name} için qty'ye ${add} ekle (ADD qty :q, :q = ${add}).`;
    const find = "pk + sk ile doğrudan bu item bulundu. Anahtar bilindiği için diğer item'lara bakılmadı.";
    const cond = [base(START), { ...base(req), req: true }, { ...base(find), req: true, active: ti, read: 1 },
      { ...base(`Koşul: qty ≤ :max. Kural "en fazla ${max} adet" ve ${add} adet eklenecek, o yüzden :max = ${max} − ${add} = ${room}. Şu anki qty ${cur}. ${cur} ≤ ${room} mü? ${ok ? "Evet ✓" : "Hayır ✗"}`), req: true, active: ti, read: 1, check: ok ? "ok" : "fail" },
      { ...base(ok ? `Yazıldı: qty = ${cur + add}.` : `Yazma yapılmadı, qty ${cur} kaldı. DynamoDB ConditionalCheckFailedException döndü. Kontrol ve yazma tek adımda yapıldı: arada başka bir yazma araya giremez.`),
        req: true, active: ti, read: 1, check: ok ? "ok" : "fail", qty: ok ? cur + add : cur, done: true, refused: !ok }];
    const free = [base(START), { ...base(req), req: true }, { ...base(find), req: true, active: ti, read: 1 },
      { ...base("Koşul yok: DynamoDB hiçbir şeyi kontrol etmeden yazar."), req: true, active: ti, read: 1, check: "none" },
      { ...base(`qty = ${cur} + ${add} = ${cur + add} yazıldı. Kural bozuldu: sepette ${cur + add} adet var.`), req: true, active: ti, read: 1, check: "none", qty: cur + add, done: true, broke: cur + add > max }];
    const DB = spec.engine_label || "DynamoDB";
    const sendC = spec.send_cond || `Uygulama kuralı koşula çeviriyor: :max = ${max} − ${add} = ${room}. Sonra UpdateItem'ı koşuluyla birlikte DynamoDB'ye gönderiyor.`;
    const backC = spec.back_cond || (ok ? "Uygulama sepeti yeniden okudu (Query) ve tarayıcıya gönderdi." :
      `Uygulama "koşul tutmadı" cevabını yakaladı, sepeti yeniden okudu (Query) ve "en fazla ${max} adet" mesajıyla tarayıcıya gönderdi.`);
    const sendF = spec.send_free || "Uygulama aynı UpdateItem'ı koşulsuz gönderiyor.";
    const backF = spec.back_free || `Uygulama sepeti yeniden okudu ve ${cur + add} adetlik sepeti tarayıcıya gönderdi; kimse uyarılmadı.`;
    cond.splice(0, cond.length, ...actorize(cond, sendC, backC, DB, { active: null, qty: cur }));
    free.splice(0, free.length, ...actorize(free, sendF, backF, DB, { active: null, qty: cur }));
    const table = `<table class="gs-table"><thead><tr><th data-hl="key">pk</th><th data-hl="key">sk</th><th>name</th><th data-hl="add">qty</th></tr></thead><tbody>
      ${rows.map((r, i) => `<tr data-i="${i}"><td data-hl="key">${esc(r.pk)}</td><td data-hl="key">${esc(r.sk)}</td><td>${esc(r.name)}</td><td data-hl="add" data-k="qty">${esc(r.qty)}</td></tr>`).join("")}</tbody></table>`;
    const lane = (id, title) => shell(id, title, `<div class="gs-req" data-hl="add">ADD qty ${add}</div>${table}<div class="gs-check" data-hl="cond"></div>`, { hl: id, count: "Okunan item", result: false, col: true });
    const html = `${actorBar(DB)}<div class="gs-lanes">${lane("cond", spec.labels?.cond || "Koşulla")}${lane("free", spec.labels?.free || "Koşulsuz")}</div>
      ${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = f.read || 0;
      L.classList.toggle("done", !!f.done); L.classList.toggle("broke", !!f.broke);
      L.querySelector(".gs-req").classList.toggle("on", !!f.req && !f.done);
      L.querySelectorAll("tbody tr").forEach((tr) => {
        const i = Number(tr.dataset.i);
        tr.classList.toggle("active", f.active === i && !f.done);
        tr.classList.toggle("hit", f.active === i && f.done && !f.refused && !f.broke);
        tr.classList.toggle("miss", f.active === i && (f.refused || f.broke) && !!f.done);
        tr.classList.toggle("dimrow", f.active !== null && f.active !== i);
        if (i === ti) tr.querySelector('[data-k="qty"]').textContent = f.qty;
      });
      const ck = L.querySelector(".gs-check");
      ck.className = `gs-check ${f.check || ""}`;
      ck.textContent = f.check === "fail" ? `${cur} ≤ ${room} ✗ koşul tutmadı` : f.check === "ok" ? "koşul tuttu ✓" : f.check === "none" ? "koşul yok" : "";
      sayWho(L, f);
    }
    return { html, lanes: { cond, free }, paint, final: showSum };
  }

  /* ---------- graph-walk: Neptune follows edges hop by hop, then counts how many paths reach each product */
  function graphWalk(spec) {
    const lanes = {}, specs = spec.lanes;
    specs.forEach((ln) => {
      const fr = [{ hop: -1, say: START }, { hop: 0, edges: 0, say: ln.start_say || `Yürüyüş ${ln.start.label} düğümünden başlıyor.` }];
      let edges = 0;
      ln.hops.forEach((h, k) => {
        edges += h.nodes.reduce((n, x) => n + (x.from || []).length, 0);
        fr.push({ hop: k + 1, edges, say: h.say || h.title });
      });
      const last = ln.hops[ln.hops.length - 1].nodes.filter((x) => !x.excluded);
      const tally = last.map((x) => ({ ...x, score: new Set(x.from).size })).sort((p, q) => q.score - p.score || String(p.id).localeCompare(String(q.id)));
      fr.push({ hop: ln.hops.length, edges, tally, done: true, say: ln.end_say || "Her ürün, ona kaç farklı yoldan ulaşıldığına göre sayıldı. En çok yol, en güçlü öneri." });
      lanes[ln.id] = spec.engine_label === false ? fr : actorize(fr, ln.send_say || "Uygulama openCypher sorgusunu Neptune'a gönderiyor.",
        ln.back_say || "Uygulama önerileri olduğu gibi tarayıcıya gönderdi. Sayma, eleme ve sıralama sorgunun içinde, Neptune'da yapıldı.",
        spec.engine_label || "Neptune", { hop: -1 });
    });
    const nodeHtml = (x, hop) => `<span class="gs-node ${x.type || ""}" data-id="${esc(x.id)}" data-hop="${hop}" ${x.excluded ? 'data-hl="exclude"' : ""} title="${esc(x.excluded || "")}">${esc(x.label)}${x.excluded ? `<small>${esc(x.excluded)}</small>` : ""}</span>`;
    const laneHtml = (ln) => shell(ln.id, ln.title, `<div class="gs-graph"><svg class="gs-edges" aria-hidden="true"></svg>
        <div class="gs-hop" data-hl="start"><h5>${esc(ln.start_title || "Başlangıç")}</h5>${nodeHtml(ln.start, 0)}</div>
        ${ln.hops.map((h, k) => `<div class="gs-hop" data-hl="hop${k + 1}"><h5>${esc(h.title)}</h5>${h.nodes.map((x) => nodeHtml(x, k + 1)).join("")}</div>`).join("")}</div>`,
      { hl: ln.id, count: "Yürünen kenar (edge)", result: ln.result_title || "Öneri (ortak müşteri sayısı)" });
    const html = `${actorBar(spec.engine_label || "Neptune")}<div class="gs-lanes">${specs.map(laneHtml).join("")}</div>${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const ln = specs.find((x) => x.id === id), L = laneOf(root, id), g = L.querySelector(".gs-graph");
      L.querySelector(".gs-count b").textContent = f.edges || 0;
      L.classList.toggle("done", !!f.done);
      L.querySelectorAll(".gs-node").forEach((n) => { const h = Number(n.dataset.hop); n.classList.toggle("seen", h <= f.hop); n.classList.toggle("now", h === f.hop && !f.done); });
      // edges of the reached hops, drawn between node centres
      const svg = g.querySelector("svg"), box = g.getBoundingClientRect();
      svg.setAttribute("width", box.width); svg.setAttribute("height", box.height);
      const at = (hop, nid) => g.querySelector(`.gs-node[data-hop="${hop}"][data-id="${CSS.escape(nid)}"]`);
      let lines = "";
      ln.hops.forEach((h, k) => {
        if (k + 1 > f.hop) return;
        h.nodes.forEach((x) => (x.from || []).forEach((src) => {
          const a = at(k, src), b = at(k + 1, x.id);
          if (!a || !b) return;
          const p = a.getBoundingClientRect(), q = b.getBoundingClientRect();
          lines += `<line x1="${p.right - box.left}" y1="${p.top + p.height / 2 - box.top}" x2="${q.left - box.left}" y2="${q.top + q.height / 2 - box.top}" class="${k + 1 === f.hop && !f.done ? "now" : ""}${x.excluded ? " ex" : ""}"/>`;
        }));
      });
      svg.innerHTML = lines;
      chips(L, (f.tally || []).map((x) => `<li>${esc(x.label)} <small>${x.score}</small></li>`));
      sayWho(L, f);
    }
    return { html, lanes, paint, final: showSum };
  }

  /* ---------- doc-group: an aggregation ($group) counts on the server (left); the "what if" lane ships every document
   * to the app, which counts them itself (right). The count is what crossed the network to the app. */
  function docGroup(spec) {
    const rows = spec.rows, key = spec.group_by || "category", mf = spec.min_field || "price", DB = spec.engine_label || "DocumentDB";
    const money = (v) => `₺${Number(v).toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    const add = (g, r) => { const c = g[r[key]] || { n: 0, min: Infinity }; return { ...g, [r[key]]: { n: c.n + 1, min: Math.min(c.min, r[mf]) } }; };
    const sorted = (g) => Object.keys(g).sort((x, y) => x.localeCompare(y, "tr"));
    const start = { say: START, active: null, read: 0, groups: {}, shipped: 0, ship: [] };
    // left: the database groups while it reads
    const srv = [start];
    let s = { ...start };
    rows.forEach((r, k) => {
      const g = add(s.groups, r);
      s = { ...s, active: k, read: k + 1, groups: g, say: `${r.name} okundu: ${key} = ${r[key]}. "${r[key]}" grubunun sayacı ${g[r[key]].n} oldu, en düşük ${mf === "price" ? "fiyat" : mf} ${money(g[r[key]].min)}.` };
      srv.push(s);
    });
    s = { ...s, active: null, sorted: true, say: `$sort: gruplar ada göre dizildi. ${sorted(s.groups).length} satırlık sonuç hazır.` };
    srv.push(s);
    s = { ...s, shipped: sorted(s.groups).length, done: true, say: `DocumentDB uygulamaya sadece ${sorted(s.groups).length} küçük satır gönderdi. ${rows.length} dokümanın hiçbiri ağdan gitmedi.` };
    srv.push(s);
    // right: every document goes to the app, the app counts
    const cli = [start];
    let c = { ...start };
    rows.forEach((r, k) => {
      c = { ...c, active: k, read: k + 1, shipped: k + 1, ship: [...c.ship, k], say: `${r.name} okundu ve olduğu gibi uygulamaya gönderildi. Ağdan giden doküman: ${k + 1}.` };
      cli.push(c);
    });
    const all = rows.reduce(add, {});
    c = { ...c, active: null, groups: all, sorted: true, who: APP_NAME, say: `Uygulama gelen ${rows.length} dokümanı kendi belleğinde grupladı ve saydı. Sonuç soldakiyle aynı, ama bütün dokümanlar ağdan geçti.` };
    cli.push(c);
    c = { ...c, done: true, say: c.say };
    cli.push(c);
    const L = spec.labels || {};
    const lanes = {
      server: actorize(srv, spec.send_server || "Uygulama aggregate komutunu gönderiyor: kategoriye göre grupla, say, en düşük fiyatı bul.",
        spec.back_server || "Uygulama gelen satırları tarayıcıya gönderdi; tarayıcı kategori kutularını çizecek.", DB, { active: null }),
      client: actorize(cli, spec.send_client || "Olsaydı: uygulama bütün dokümanları isterdi (find, filtresiz).",
        spec.back_client || "Uygulama kendi saydığı sonucu tarayıcıya gönderirdi.", DB, { active: null }),
    };
    const table = `<table class="gs-table" data-hl="table"><thead><tr><th>Ürün no</th><th>Ürün</th><th data-hl="group">${esc(key)}</th><th data-hl="min">${esc(mf)}</th></tr></thead><tbody>
      ${rows.map((r, k) => `<tr data-k="${k}"><td>${esc(r.id)}</td><td>${esc(r.name)}</td><td data-hl="group">${esc(r[key])}</td><td data-hl="min">${money(r[mf])}</td></tr>`).join("")}</tbody></table>`;
    const lane = (id, title) => shell(id, title, table, { hl: id, count: "Ağdan uygulamaya giden", result: spec.result_title || "Sonuç (kategori · ürün sayısı · en düşük fiyat)", col: true });
    const html = `${actorBar(DB)}<div class="gs-lanes">${lane("server", L.server || "DocumentDB'de grupla")}${lane("client", L.client || "Olsaydı: hepsini çek, uygulamada say")}</div>${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const Ln = laneOf(root, id);
      Ln.querySelector(".gs-count b").textContent = f.shipped || 0;
      Ln.classList.toggle("done", !!f.done);
      Ln.querySelectorAll("tbody tr").forEach((tr) => {
        const k = Number(tr.dataset.k);
        tr.classList.toggle("active", f.active === k);
        tr.classList.toggle("read", (f.read || 0) > k);
        tr.classList.toggle("shipped", (f.ship || []).includes(k));
      });
      chips(Ln, sorted(f.groups || {}).map((g) => `<li data-hl="count">${esc(g)} <small>${f.groups[g].n} · ${money(f.groups[g].min)}</small></li>`));
      sayWho(Ln, f);
    }
    return { html, lanes, paint, final: showSum };
  }

  /* ---------- kv: key-value reads in memory. The app sends one command per key; the database computes where the key lives
   * (hash slot) and goes straight to it. spec.keys [{key, type, value, slot}], spec.commands [{cmd, key, returns, say_send,
   * say_find, say_back}]. One lane. */
  function kv(spec) {
    const keys = spec.keys, DB = spec.engine_label || "ElastiCache";
    const fr = [{ say: START, active: null, read: 0, log: [], vals: keys.map((x) => x.value) }];
    let s = { ...fr[0] };
    spec.commands.forEach((c) => {
      const k = keys.findIndex((x) => x.key === c.key);
      s = { ...s, active: null, who: APP_NAME, say: c.say_send || `Uygulama ${c.cmd} ${c.key} gönderiyor.` };
      fr.push(s);
      s = { ...s, active: k, who: DB, read: s.read + 1, say: c.say_find || `${c.key} anahtarının yeri hesaplandı (slot ${keys[k].slot}). Doğrudan o kayda gidildi; başka anahtara bakılmadı.` };
      fr.push(s);
      const vals = c.set !== undefined ? s.vals.map((v, i) => (i === k ? c.set : v)) : s.vals;     // a write changes the value on screen
      s = { ...s, who: DB, vals, changed: c.set !== undefined ? k : null, log: [...s.log, `${c.cmd} ${c.key} → ${c.returns}`], say: c.say_back || `${DB} cevabı döndü: ${c.returns}.` };
      fr.push(s);
    });
    fr.push({ ...s, active: null, who: APP_NAME, done: true, say: spec.back || "Uygulama iki cevabı birleştirdi ve tarayıcıya gönderdi." });
    const table = `<table class="gs-table" data-hl="table"><thead><tr><th data-hl="key">Anahtar</th><th>Tür</th><th>Değer</th><th data-hl="slot">Slot</th></tr></thead><tbody>
      ${keys.map((x, i) => `<tr data-i="${i}"><td data-hl="key"><code>${esc(x.key)}</code></td><td>${esc(x.type)}</td><td>${esc(x.value)}</td><td data-hl="slot">${esc(x.slot)}</td></tr>`).join("")}</tbody></table>`;
    const html = `${actorBar(DB)}<div class="gs-lanes one">${shell("kv", spec.title || `${DB} (bellek)`, table, { count: "Okunan anahtar", result: spec.result_title || "Komutlar ve cevapları", col: true })}</div>${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = `${f.read || 0} / ${keys.length}`;
      L.classList.toggle("done", !!f.done);
      L.querySelectorAll("tbody tr").forEach((tr) => {
        const i = Number(tr.dataset.i);
        tr.classList.toggle("active", f.active === i);
        tr.classList.toggle("dimrow", f.active !== null && f.active !== undefined && f.active !== i);
        tr.classList.toggle("fresh", f.changed === i);
        tr.children[2].textContent = (f.vals || [])[i] ?? keys[i].value;
      });
      chips(L, (f.log || []).map((x) => `<li data-hl="result"><code>${esc(x)}</code></li>`));
      sayWho(L, f);
    }
    return { html, lanes: { kv: fr }, paint, final: showSum };
  }

  /* ---------- nested-filter: a filter on a field inside the document (attributes.renk). Left: the real plan, an index on
   * { category, rating } narrows to the category and every document of it is read to test the nested field. Right: an
   * index that also holds the nested field goes straight to the matching entries. */
  function nestedFilter(spec) {
    const rows = spec.rows, want = spec.value, DB = spec.engine_label || "DocumentDB", L = spec.labels || {};
    const byRating = [...rows].sort((a, b) => b.rating - a.rating || a.id.localeCompare(b.id));
    const byNested = [...rows].sort((a, b) => a.renk.localeCompare(b.renk, "tr") || b.rating - a.rating || a.id.localeCompare(b.id));
    const start = { say: START, active: null, read: [], hit: [], miss: [], result: [], entry: null, range: false };
    const now = [start];
    let s = { ...start, range: true, say: `Index ${spec.index_now} ile "${spec.category}" bölümüne gidildi. Bu index renk bilmiyor: bölümdeki her doküman okunup renge bakılacak.` };
    now.push(s);
    byRating.forEach((r) => {
      const ok = r.renk === want;
      s = { ...s, active: r.id, entry: byRating.indexOf(r), read: [...s.read, r.id], hit: ok ? [...s.hit, r.id] : s.hit, miss: ok ? s.miss : [...s.miss, r.id],
        result: ok ? [...s.result, r.id] : s.result,
        say: `${r.name} okundu. Dokümanın içinde attributes.renk = ${r.renk}. ${ok ? "✓ Eşleşti, sonuca girdi." : "✗ Eşleşmedi, boşuna okundu."}` };
      now.push(s);
    });
    now.push({ ...s, active: null, entry: null, done: true, say: `Bitti. ${rows.length} doküman okundu, ${s.result.length} tanesi sonuca girdi. Sonuç zaten puan sırasında.` });
    const better = [start];
    let b = { ...start, range: true, say: `Index ${spec.index_better} ile doğrudan "${spec.category} · ${want}" bölümüne gidildi. Renk index'in içinde olduğu için başka renge bakılmayacak.` };
    better.push(b);
    byNested.filter((r) => r.renk === want).forEach((r) => {
      b = { ...b, active: r.id, entry: byNested.indexOf(r), read: [...b.read, r.id], hit: [...b.hit, r.id], result: [...b.result, r.id],
        say: `Index ${r.name} kaydını gösterdi; doküman okundu ve doğrudan sonuca girdi.` };
      better.push(b);
    });
    better.push({ ...b, active: null, entry: null, done: true, say: `Bitti. ${b.read.length} doküman okundu, ${b.read.length}'ü de sonuca girdi.` });
    const lanes = {
      now: actorize(now, spec.send_now || "Uygulama find komutunu gönderiyor: kategori ve iç içe renk alanı, puana göre sıralı.", spec.back_now || "Uygulama dokümanları tarayıcıya gönderdi.", DB, { active: null }),
      better: actorize(better, spec.send_better || "Olsaydı: aynı komut, ama veritabanında üç alanlı bir index olsaydı.", spec.back_better || "Uygulama aynı listeyi tarayıcıya gönderirdi.", DB, { active: null }),
    };
    const idxList = (list, withNested, label, hl) => `<div class="gs-index" data-hl="${hl}"><div class="gs-index-cap">Index ${esc(label)}</div><ol>${list.map((r, k) =>
      `<li data-k="${k}" data-v="${esc(r.renk)}"><span>${esc(spec.category)}</span>${withNested ? `<span>${esc(r.renk)}</span>` : ""}<span>${esc(r.rating)}</span><span>→ ${esc(r.id)}</span></li>`).join("")}</ol></div>`;
    const table = `<table class="gs-table" data-hl="table"><thead><tr><th>Ürün no</th><th>Ürün</th><th data-hl="nested">attributes.renk</th><th data-hl="sort">Puan</th><th class="gs-mark"></th></tr></thead><tbody>
      ${byRating.map((r) => `<tr data-id="${esc(r.id)}"><td>${esc(r.id)}</td><td>${esc(r.name)}</td><td data-hl="nested"><code>${esc(r.renk)}</code></td><td data-hl="sort">${esc(r.rating)}</td><td class="gs-mark"></td></tr>`).join("")}</tbody></table>`;
    const lane = (id, title, list, nested, label, hl) => shell(id, title, idxList(list, nested, label, hl) + table, { hl: id, count: "Okunan doküman", result: spec.result_title || "Sonuç (puan sırasında)", col: true });
    const html = `${actorBar(DB)}<div class="gs-lanes">${lane("now", L.now || "Gerçek plan", byRating, false, spec.index_now, "index")}${lane("better", L.better || "Olsaydı: üç alanlı index", byNested, true, spec.index_better, "index2")}</div>${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const Ln = laneOf(root, id), list = id === "now" ? byRating : byNested;
      Ln.querySelector(".gs-count b").textContent = (f.read || []).length;
      Ln.classList.toggle("done", !!f.done);
      Ln.querySelectorAll("tbody tr").forEach((tr) => {
        const x = tr.dataset.id;
        tr.classList.toggle("active", f.active === x);
        tr.classList.toggle("read", (f.read || []).includes(x));
        tr.classList.toggle("hit", (f.hit || []).includes(x));
        tr.classList.toggle("miss", (f.miss || []).includes(x));
        tr.querySelector(".gs-mark").textContent = (f.hit || []).includes(x) ? "✓" : (f.miss || []).includes(x) ? "✗" : "";
      });
      Ln.querySelectorAll(".gs-index li").forEach((li) => {
        const k = Number(li.dataset.k);
        li.classList.toggle("range", !!f.range && (id === "now" || li.dataset.v === want));
        li.classList.toggle("active", f.entry === k);
      });
      chips(Ln, (f.result || []).map((x) => { const r = rows.find((y) => y.id === x); return `<li>${esc(r.name)} <small>${esc(r.rating)}</small></li>`; }));
      sayWho(Ln, f);
    }
    return { html, lanes, paint, final: showSum };
  }

  /* ---------- inverted-index: a search engine looks words up in its inverted index (term → documents). Each lane is one
   * request: spec.docs [{id, name}], spec.lanes [{id, title, field, terms [[term, [ids]]], analyze_say, tokens [..],
   * lookups [{token, term, say, fuzzy}], scores [[id, score]], score_say, send, back}]. */
  function invertedIndex(spec) {
    const DB = spec.engine_label || "OpenSearch", docs = spec.docs;
    const nameOf = (id) => (docs.find((d) => d.id === id) || { name: id }).name;
    const lanes = {};
    spec.lanes.forEach((ln) => {
      const fr = [{ say: START, tokens: [], term: null, found: [], scores: [] }];
      let s = { ...fr[0] };
      s = { ...s, tokens: ln.tokens, say: ln.analyze_say || `Sorgu analyzer'dan geçti: ${ln.tokens.join(", ")}.` };
      fr.push(s);
      ln.lookups.forEach((lk) => {
        const row = ln.terms.find(([t]) => t === lk.term);
        s = { ...s, term: lk.term, tok: lk.token, fuzzy: !!lk.fuzzy, found: [...new Set([...s.found, ...((row && row[1]) || [])])], say: lk.say };
        fr.push(s);
      });
      s = { ...s, term: null, tok: null, scores: ln.scores, done: true, say: ln.score_say || "Her ürüne bir skor verildi; en yüksek skor en üstte." };
      fr.push(s);
      lanes[ln.id] = actorize(fr, ln.send || "Uygulama arama isteğini OpenSearch'e gönderiyor.", ln.back || "Uygulama sonuçları tarayıcıya gönderdi.", DB, { term: null });
    });
    const laneHtml = (ln) => shell(ln.id, ln.title, `<div class="gs-tokens" data-hl="analyze"><span>Sorgunun kelimeleri (token)</span><ol></ol></div>
      <table class="gs-table" data-hl="index"><thead><tr><th>Terim (${esc(ln.field)})</th><th>Geçtiği ürünler</th></tr></thead><tbody>
      ${ln.terms.map(([t, ids]) => `<tr data-t="${esc(t)}"><td><code>${esc(t)}</code></td><td>${ids.map((x) => `<span class="gs-pid" data-id="${esc(x)}">${esc(x)}</span>`).join(" ")}</td></tr>`).join("")}</tbody></table>`,
      { hl: ln.id, count: "Bulunan ürün", result: spec.result_title || "Sonuç (skor sırasında)", col: true });
    const html = `${actorBar(DB)}<div class="gs-lanes${spec.lanes.length === 1 ? " one" : ""}">${spec.lanes.map(laneHtml).join("")}</div>${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = (f.found || []).length;
      L.classList.toggle("done", !!f.done);
      L.querySelector(".gs-tokens ol").innerHTML = (f.tokens || []).map((t) => `<li class="${f.tok === t ? "on" : ""}"><code>${esc(t)}</code></li>`).join("") || '<li class="empty">henüz yok</li>';
      L.querySelectorAll("tbody tr").forEach((tr) => {
        tr.classList.toggle("active", f.term === tr.dataset.t);
        tr.classList.toggle("fuzzy", f.term === tr.dataset.t && !!f.fuzzy);
        tr.classList.toggle("dimrow", !!f.term && f.term !== tr.dataset.t);
      });
      L.querySelectorAll(".gs-pid").forEach((x) => x.classList.toggle("hit", (f.found || []).includes(x.dataset.id)));
      chips(L, (f.scores || []).map(([x, sc]) => `<li>${esc(nameOf(x))} <small>${esc(sc)}</small></li>`));
      sayWho(L, f);
    }
    return { html, lanes, paint, final: showSum };
  }

  /* ---------- facets: the hits and their counts (aggregations) come from one pass over the matching documents. Left: the
   * query alone; right: the same query with a filter (no score change). spec.rows [{id, name, category, price, score}],
   * spec.ranges [[label, from, to]], spec.filter [field, value], spec.labels {all, filtered}. */
  function facets(spec) {
    const rows = spec.rows, DB = spec.engine_label || "OpenSearch", [ff, fv] = spec.filter, Lb = spec.labels || {};
    const money = (v) => `₺${Number(v).toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    const rangeOf = (p) => (spec.ranges.find(([, f, t]) => (f == null || p >= f) && (t == null || p < t)) || ["?"])[0];
    const run = (withFilter) => {
      const fr = [{ say: START, active: null, cats: {}, prices: {}, kept: [], out: [] }];
      let s = { ...fr[0] };
      rows.forEach((r, k) => {
        const keep = !withFilter || String(r[ff]) === String(fv);
        const cats = keep ? { ...s.cats, [r.category]: (s.cats[r.category] || 0) + 1 } : s.cats;
        const pr = rangeOf(r.price), prices = keep ? { ...s.prices, [pr]: (s.prices[pr] || 0) + 1 } : s.prices;
        s = { ...s, active: k, cats, prices, kept: keep ? [...s.kept, k] : s.kept, out: keep ? s.out : [...s.out, k],
          say: keep ? `${r.name} (skor ${r.score}) sonuca girdi; aynı anda sayılara eklendi: ${r.category} +1, ${pr} +1.`
            : `${r.name}: ${ff} = ${r[ff]}, filtreye uymadı, atlandı. Skoru hesaplanmaz, sayılara girmez.` };
        fr.push(s);
      });
      fr.push({ ...s, active: null, done: true, say: withFilter ? `Bitti. Filtreden geçen ${s.kept.length} ürün, skorları değişmeden; sayılar da sadece onlardan.` : `Bitti. ${s.kept.length} ürün ve sayıları aynı geçişte hazır; ayrı bir sayım sorgusu gerekmedi.` });
      return fr;
    };
    const lanes = {
      all: actorize(run(false), spec.send_all || "Uygulama arama isteğini gönderiyor: sonuçlar ve sayılar (aggs) aynı istekte.", spec.back_all || "Uygulama sonuçları ve sayıları tarayıcıya gönderdi.", DB, { active: null }),
      filtered: actorize(run(true), spec.send_filtered || "Uygulama aynı aramayı bir filtreyle gönderiyor.", spec.back_filtered || "Uygulama filtrelenmiş sonuçları tarayıcıya gönderdi.", DB, { active: null }),
    };
    const table = `<table class="gs-table" data-hl="table"><thead><tr><th>Ürün</th><th data-hl="filter">Kategori</th><th data-hl="price">Fiyat</th><th data-hl="score">Skor</th></tr></thead><tbody>
      ${rows.map((r, k) => `<tr data-k="${k}"><td>${esc(r.name)}</td><td data-hl="filter">${esc(r.category)}</td><td data-hl="price">${money(r.price)}</td><td data-hl="score">${esc(r.score)}</td></tr>`).join("")}</tbody></table>`;
    const buckets = `<div class="gs-buckets" data-hl="aggs"><div><b>Kategori sayıları</b><ol class="b-cat"></ol></div><div><b>Fiyat aralıkları</b><ol class="b-price"></ol></div></div>`;
    const lane = (id, title) => shell(id, title, table + buckets, { hl: id, count: "Sonuca giren", result: false, col: true });
    const html = `${actorBar(DB)}<div class="gs-lanes">${lane("all", Lb.all || "Sadece arama")}${lane("filtered", Lb.filtered || "Arama + filtre")}</div>${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = (f.kept || []).length;
      L.classList.toggle("done", !!f.done);
      L.querySelectorAll("tbody tr").forEach((tr) => {
        const k = Number(tr.dataset.k);
        tr.classList.toggle("active", f.active === k);
        tr.classList.toggle("hit", (f.kept || []).includes(k));
        tr.classList.toggle("miss", (f.out || []).includes(k));
      });
      const list = (o) => Object.entries(o || {}).map(([k, v]) => `<li>${esc(k)} <b>${v}</b></li>`).join("") || '<li class="empty">henüz yok</li>';
      L.querySelector(".b-cat").innerHTML = list(f.cats);
      L.querySelector(".b-price").innerHTML = list(f.prices);
      sayWho(L, f);
    }
    return { html, lanes, paint, final: showSum };
  }

  /* ---------- geo: a distance search. The index splits the map into cells; cells the circle never touches are not opened,
   * the stores of the other cells get their distance checked, the hits are sorted by distance.
   * spec.center {lat, lon, label}, spec.stores [{id, name, city, lat, lon}], spec.lanes [{id, title, km, window, send, back}]. */
  function geo(spec) {
    const DB = spec.engine_label || "OpenSearch", c = spec.center, rad = Math.PI / 180;
    const xy = (p) => ({ x: (p.lon - c.lon) * Math.cos(c.lat * rad) * 111.32, y: (p.lat - c.lat) * 110.57 });
    const dist = (p) => { const dLat = (p.lat - c.lat) * rad, dLon = (p.lon - c.lon) * rad;                // haversine, km
      const h = Math.sin(dLat / 2) ** 2 + Math.cos(c.lat * rad) * Math.cos(p.lat * rad) * Math.sin(dLon / 2) ** 2; return 2 * 6371 * Math.asin(Math.sqrt(h)); };
    const stores = spec.stores.map((st) => ({ ...st, ...xy(st), d: Math.round(dist(st) * 10) / 10 }));
    const lanes = {}, views = {};
    spec.lanes.forEach((ln) => {
      const W = ln.window, n = 4, size = (2 * W) / n, cells = [];
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
        const x0 = -W + i * size, y0 = -W + j * size, nx = Math.max(x0, Math.min(0, x0 + size)), ny = Math.max(y0, Math.min(0, y0 + size));
        cells.push({ x0, y0, size, touch: Math.hypot(nx, ny) <= ln.km });
      }
      const inCell = (st) => cells.findIndex((q) => st.x >= q.x0 && st.x < q.x0 + q.size && st.y >= q.y0 && st.y < q.y0 + q.size);
      const cand = stores.filter((st) => { const k = inCell(st); return k >= 0 && cells[k].touch; });
      views[ln.id] = { W, cells };
      const fr = [{ say: START, pruned: false, checked: [], hit: [], miss: [], order: [] }];
      let s = { ...fr[0], pruned: true, say: `Harita karelere bölünmüş (index'in BKD ağacı). ${ln.km} km'lik dairenin hiç değmediği kareler açılmadı; ${stores.length - cand.length} mağaza hiç okunmadı.` };
      fr.push(s);
      cand.forEach((st) => {
        const ok = st.d <= ln.km;
        s = { ...s, active: st.id, checked: [...s.checked, st.id], hit: ok ? [...s.hit, st.id] : s.hit, miss: ok ? s.miss : [...s.miss, st.id],
          say: `${st.name}: daireye değen bir karede. Uzaklığı hesaplandı: ${st.d} km. ${ok ? `✓ ${ln.km} km içinde.` : `✗ ${ln.km} km'nin dışında.`}` };
        fr.push(s);
      });
      const order = stores.filter((st) => s.hit.includes(st.id)).sort((p, q) => p.d - q.d).map((st) => st.id);
      fr.push({ ...s, active: null, order, done: true, say: `Daire içindeki ${order.length} mağaza uzaklığa göre sıralandı (_geo_distance sort): en yakın en üstte.` });
      lanes[ln.id] = actorize(fr, ln.send || "Uygulama geo_distance sorgusunu gönderiyor.", ln.back || "Uygulama mağazaları tarayıcıya gönderdi.", DB, { active: null });
    });
    const svgOf = (ln) => {
      const { W, cells } = views[ln.id], S = 260, k = S / (2 * W), X = (x) => (x + W) * k, Y = (y) => (W - y) * k;
      return `<svg class="gs-geomap" viewBox="0 0 ${S} ${S}" role="img" aria-label="Harita">
        ${cells.map((q, i) => `<rect data-cell="${i}" class="${q.touch ? "touch" : "far"}" x="${X(q.x0)}" y="${Y(q.y0 + q.size)}" width="${q.size * k}" height="${q.size * k}"/>`).join("")}
        <circle class="radius" data-hl="radius" cx="${X(0)}" cy="${Y(0)}" r="${ln.km * k}"/>
        <circle class="center" cx="${X(0)}" cy="${Y(0)}" r="4"/><text x="${X(0) + 6}" y="${Y(0) - 6}">${esc(c.label)}</text>
        ${stores.filter((st) => Math.abs(st.x) < W && Math.abs(st.y) < W).map((st) => `<g data-st="${esc(st.id)}"><circle cx="${X(st.x)}" cy="${Y(st.y)}" r="5"/></g>`).join("")}
      </svg>`;
    };
    const list = (ln) => `<table class="gs-table"><thead><tr><th>Mağaza</th><th>Şehir</th><th data-hl="sort">Uzaklık</th><th class="gs-mark"></th></tr></thead><tbody>
      ${stores.map((st) => `<tr data-st="${esc(st.id)}"><td>${esc(st.name)}</td><td>${esc(st.city)}</td><td data-hl="sort">${st.d} km</td><td class="gs-mark"></td></tr>`).join("")}</tbody></table>`;
    const html = `${actorBar(DB)}<div class="gs-lanes">${spec.lanes.map((ln) => shell(ln.id, ln.title, `<div class="gs-geo-wrap">${svgOf(ln)}${list(ln)}</div>`,
      { hl: ln.id, count: "Uzaklığı hesaplanan mağaza", result: spec.result_title || "Sonuç (en yakın önce)", col: true })).join("")}</div>${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = `${(f.checked || []).length} / ${stores.length}`;
      L.classList.toggle("done", !!f.done);
      L.querySelector(".gs-geomap").classList.toggle("pruned", !!f.pruned);
      L.querySelectorAll("[data-st]").forEach((el) => {
        const x = el.dataset.st;
        el.classList.toggle("active", f.active === x);
        el.classList.toggle("hit", (f.hit || []).includes(x));
        el.classList.toggle("miss", (f.miss || []).includes(x));
        el.classList.toggle("gs-pruned", !!f.pruned && !(f.checked || []).includes(x) && !!f.done);
        const m = el.querySelector(".gs-mark"); if (m) m.textContent = (f.hit || []).includes(x) ? "✓" : (f.miss || []).includes(x) ? "✗" : "";
      });
      chips(L, (f.order || []).map((x) => { const st = stores.find((y) => y.id === x); return `<li>${esc(st.name)} <small>${st.d} km</small></li>`; }));
      sayWho(L, f);
    }
    return { html, lanes, paint, final: showSum };
  }

  /* ---------- projection: one document read by _id; the projection decides which fields travel to the app.
   * spec.doc {field: value}, spec.lanes [{id, title, fields (null = all), send, back}]. The count is the bytes that travel. */
  function projection(spec) {
    const DB = spec.engine_label || "DocumentDB", doc = spec.doc, keys = Object.keys(doc);
    const size = (k) => new TextEncoder().encode(`"${k}":${JSON.stringify(doc[k])}`).length;
    const lanes = {};
    spec.lanes.forEach((ln) => {
      const fr = [{ say: START, found: false, sent: [], cut: [], bytes: 0 }];
      let s = { ...fr[0], found: true, say: `_id = "${doc._id}" ile doküman doğrudan bulundu (_id'nin index'i her koleksiyonda hazırdır). Tek okuma.` };
      fr.push(s);
      keys.forEach((k) => {
        const keep = !ln.fields || ln.fields.includes(k) || k === "_id";
        s = { ...s, active: k, sent: keep ? [...s.sent, k] : s.sent, cut: keep ? s.cut : [...s.cut, k], bytes: s.bytes + (keep ? size(k) : 0),
          say: keep ? `${k} cevaba kondu (${size(k)} bayt).` : `${k} projection'da yok, cevaba konmadı.` };
        fr.push(s);
      });
      fr.push({ ...s, active: null, done: true, say: `Bitti. Doküman bir kez okundu; uygulamaya ${s.sent.length} alan, yaklaşık ${s.bytes} bayt gitti.` });
      lanes[ln.id] = actorize(fr, ln.send || "Uygulama find_one komutunu gönderiyor.", ln.back || "Uygulama ürünü tarayıcıya gönderdi.", DB, { found: false });
    });
    const show = (v) => (typeof v === "object" ? JSON.stringify(v) : String(v));
    const body = `<table class="gs-table gs-doc" data-hl="table"><thead><tr><th>Alan</th><th>Değer</th><th class="gs-mark"></th></tr></thead><tbody>
      ${keys.map((k) => `<tr data-k="${esc(k)}"><td data-hl="${k === "_id" ? "id" : "field"}"><code>${esc(k)}</code></td><td>${esc(show(doc[k]).slice(0, 80))}</td><td class="gs-mark"></td></tr>`).join("")}</tbody></table>`;
    const html = `${actorBar(DB)}<div class="gs-lanes">${spec.lanes.map((ln) => shell(ln.id, ln.title, body, { hl: ln.id, count: "Ağdan giden (yaklaşık bayt)", result: false, col: true })).join("")}</div>${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = f.bytes || 0;
      L.classList.toggle("done", !!f.done);
      L.querySelectorAll("tbody tr").forEach((tr) => {
        const k = tr.dataset.k;
        tr.classList.toggle("active", f.active === k);
        tr.classList.toggle("hit", (f.sent || []).includes(k));
        tr.classList.toggle("miss", (f.cut || []).includes(k));
        tr.classList.toggle("read", !!f.found);
        tr.querySelector(".gs-mark").textContent = (f.sent || []).includes(k) ? "→" : (f.cut || []).includes(k) ? "✗" : "";
      });
      sayWho(L, f);
    }
    return { html, lanes, paint, final: showSum };
  }

  /* ---------- ddb-items: DynamoDB items grouped by partition key. spec.rows [{pk, sk, name, qty}], spec.ops: a list of
   * {op: "update", pk, sk, name, add, say_send, say_find, say_write} or {op: "query", pk, say_send, say_read}. One lane. */
  function ddbItems(spec) {
    const DB = spec.engine_label || "DynamoDB";
    let rows = spec.rows.map((r) => ({ ...r }));
    const fr = [{ say: START, rows: rows.map((r) => ({ ...r })), litPk: null, active: null, read: [], fresh: null, wcu: 0, rcu: 0 }];
    let s = { ...fr[0] };
    spec.ops.forEach((o) => {
      if (o.op === "update") {
        s = { ...s, litPk: null, active: null, read: [], who: APP_NAME, say: o.say_send || `Uygulama UpdateItem gönderiyor: ${o.pk} / ${o.sk}.` };
        fr.push(s);
        const has = rows.find((r) => r.pk === o.pk && r.sk === o.sk);
        s = { ...s, who: DB, litPk: o.pk, active: has ? `${o.pk}|${o.sk}` : null,
          say: o.say_find || `pk = ${o.pk} değerinden partition bulundu; içinde sk = ${o.sk} ${has ? "var" : "yok"}. Başka partition'a bakılmadı.` };
        fr.push(s);
        if (has) has.qty += o.add; else rows = [...rows, { pk: o.pk, sk: o.sk, name: o.name, qty: o.add }];
        rows.sort((p, q) => p.pk.localeCompare(q.pk) || p.sk.localeCompare(q.sk));
        s = { ...s, who: DB, rows: rows.map((r) => ({ ...r })), active: `${o.pk}|${o.sk}`, fresh: has ? null : `${o.pk}|${o.sk}`, wcu: s.wcu + 1,
          say: o.say_write || (has ? `Item vardı: qty ${o.add} arttı.` : `Item yoktu: ADD onu qty = ${o.add} ile oluşturdu.`) };
        fr.push(s);
      } else {
        s = { ...s, active: null, fresh: null, who: APP_NAME, say: o.say_send || `Uygulama Query gönderiyor: pk = ${o.pk}.` };
        fr.push(s);
        const mine = rows.filter((r) => r.pk === o.pk).map((r) => `${r.pk}|${r.sk}`);
        s = { ...s, who: DB, litPk: o.pk, read: mine, rcu: s.rcu + 1, say: o.say_read || `Partition'ın bütün item'ları sırayla okundu: ${mine.length} item.` };
        fr.push(s);
      }
    });
    fr.push({ ...s, who: APP_NAME, done: true, say: spec.back || "Uygulama sepeti tarayıcıya gönderdi." });
    const pks = () => [...new Set(fr[fr.length - 1].rows.map((r) => r.pk))];
    const body = `<div class="gs-parts">${pks().map((pk) => `<div class="gs-part" data-pk="${esc(pk)}"><div class="gs-part-key" data-hl="key">pk = <b>${esc(pk)}</b></div>
      <table class="gs-table"><thead><tr><th data-hl="key">sk</th><th>name</th><th data-hl="add">qty</th></tr></thead><tbody></tbody></table></div>`).join("")}</div>`;
    const html = `${actorBar(DB)}<div class="gs-lanes one">${shell("ddb", spec.title || `${DB} tablosu`, body, { count: "İşlem", result: false, col: true })}</div>${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = `${f.wcu || 0} yazma · ${f.rcu || 0} okuma`;
      L.classList.toggle("done", !!f.done);
      L.querySelectorAll(".gs-part").forEach((el) => {
        const pk = el.dataset.pk;
        el.classList.toggle("lit", f.litPk === pk); el.classList.toggle("dim", !!f.litPk && f.litPk !== pk);
        el.querySelector("tbody").innerHTML = (f.rows || []).filter((r) => r.pk === pk).map((r) => { const k = `${r.pk}|${r.sk}`;
          return `<tr class="${f.active === k ? "active" : ""} ${f.fresh === k ? "fresh" : ""} ${(f.read || []).includes(k) ? "read" : ""}"><td data-hl="key">${esc(r.sk)}</td><td>${esc(r.name)}</td><td data-hl="add">${esc(r.qty)}</td></tr>`; }).join("")
          || '<tr><td colspan="3" class="empty">boş</td></tr>';
      });
      sayWho(L, f);
    }
    return { html, lanes: { ddb: fr }, paint, final: showSum };
  }

  /* ---------- replicas: one item kept in several copies. A write reaches the copies one after the other; a read asks one
   * copy (eventual) or the leader / a majority (strong). spec.nodes [{id, label}], spec.key, spec.old, spec.new,
   * spec.lag (ids of the copies that do not have the new value yet), spec.lanes [{id, title, reads: [ids], cost, send, read_say, back}]. */
  function replicas(spec) {
    const DB = spec.engine_label || "DynamoDB", nodes = spec.nodes;
    const lanes = {};
    spec.lanes.forEach((ln) => {
      const fr = [{ say: START, val: {}, ask: [], got: null }];
      const before = Object.fromEntries(nodes.map((n) => [n.id, (spec.lag || []).includes(n.id) ? spec.old : spec.new]));
      let s = { ...fr[0], val: before, say: spec.state_say || `Az önceki yazma ana kopyaya geldi ve kopyalara yayılıyor. Şu an ${spec.lag.length} kopyada hâlâ eski değer var.` };
      fr.push(s);
      s = { ...s, ask: ln.reads, say: ln.read_say || `Okuma ${ln.reads.join(", ")} kopyasına gidiyor.` };
      fr.push(s);
      const vals = ln.reads.map((x) => before[x]), got = ln.pick === "newest" ? spec.new : vals[0];
      s = { ...s, got, cost: ln.cost, done: true, say: ln.got_say || `Cevap: ${spec.key} = ${got}. Harcanan: ${ln.cost}.` };
      fr.push(s);
      lanes[ln.id] = actorize(fr, ln.send || "Uygulama okuma isteğini gönderiyor.", ln.back || "Uygulama sonucu tarayıcıya gönderdi.", DB, { ask: [] });
    });
    const body = `<div class="gs-nodes">${nodes.map((n) => `<div class="gs-node-box" data-n="${esc(n.id)}" data-hl="node"><b>${esc(n.label)}</b><span>${esc(spec.key)} = <i></i></span></div>`).join("")}</div>`;
    const html = `${actorBar(DB)}<div class="gs-lanes">${spec.lanes.map((ln) => shell(ln.id, ln.title, body, { hl: ln.id, count: "Okunan kopya", result: spec.result_title || "Okumanın cevabı", col: true })).join("")}</div>${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = (f.ask || []).length;
      L.classList.toggle("done", !!f.done);
      L.querySelectorAll(".gs-node-box").forEach((el) => {
        const n = el.dataset.n, v = (f.val || {})[n];
        el.querySelector("i").textContent = v === undefined ? "…" : v;
        el.classList.toggle("stale", v !== undefined && v !== spec.new);
        el.classList.toggle("asked", (f.ask || []).includes(n));
      });
      chips(L, f.got !== null && f.got !== undefined ? [`<li>${esc(spec.key)} = <b>${esc(f.got)}</b> <small>${esc(f.cost || "")}</small></li>`] : []);
      sayWho(L, f);
    }
    return { html, lanes, paint, final: showSum };
  }

  /* ---------- spread: many writes at once. Left: keys spread over many partitions, every partition stays under its limit.
   * Right ("what if"): every write uses the same key, one partition takes them all and the excess is throttled.
   * spec.partitions (boxes), spec.waves (ticks), spec.per_wave (writes per tick), spec.limit (writes per partition per tick). */
  function spread(spec) {
    const DB = spec.engine_label || "DynamoDB", P = spec.partitions || 8, W = spec.waves || 5, K = spec.per_wave || 16, lim = spec.limit || 4, Lb = spec.labels || {};
    const lanes = {};
    const mk = (hot) => {
      const fr = [{ say: START, cnt: Array(P).fill(0), ok: 0, thr: 0, now: [] }];
      let s = { ...fr[0] };
      for (let w = 0; w < W; w++) {
        const add = Array(P).fill(0);
        for (let i = 0; i < K; i++) add[hot ? 0 : (w * K + i) % P] += 1;
        const okNow = add.map((x) => Math.min(x, lim)), thrNow = add.map((x, i) => x - okNow[i]);
        const cnt = s.cnt.map((c, i) => c + okNow[i]);
        const ok = s.ok + okNow.reduce((a, b) => a + b, 0), thr = s.thr + thrNow.reduce((a, b) => a + b, 0);
        s = { ...s, cnt, ok, thr, now: add.map((x, i) => (x ? i : -1)).filter((i) => i >= 0),
          say: hot ? `${w + 1}. dalga: ${K} yazmanın hepsi aynı anahtara, yani aynı partition'a geldi. Partition bu anda en fazla ${lim} yazma alabiliyor: ${thrNow[0]} yazma geri çevrildi (throttle).`
            : `${w + 1}. dalga: ${K} yazma, anahtarları farklı olduğu için ${s.now ? new Set(add.map((x, i) => (x ? i : -1)).filter((i) => i >= 0)).size : 0} partition'a dağıldı. Hiçbiri sınıra ulaşmadı.` };
        fr.push(s);
      }
      fr.push({ ...s, now: [], done: true, say: hot ? `Bitti. ${s.ok} yazma kabul edildi, ${s.thr} yazma geri çevrildi; uygulama onları yeniden denemek zorunda.` : `Bitti. ${s.ok} yazmanın hepsi kabul edildi; yük partition'lara eşit dağıldı.` });
      return fr;
    };
    lanes.spread = actorize(mk(false), spec.send_spread || "Uygulama yazmaları aynı anda gönderiyor.", spec.back_spread || "Uygulama ölçümleri tarayıcıya gönderdi.", DB, { now: [] });
    lanes.hot = actorize(mk(true), spec.send_hot || "Olsaydı: aynı yazmalar tek bir anahtarla gönderilseydi.", spec.back_hot || "Uygulama geri çevrilen yazmaları yeniden denemek zorunda kalırdı.", DB, { now: [] });
    const boxes = `<div class="gs-pgrid">${Array.from({ length: P }, (_, i) => `<div class="gs-pbox" data-i="${i}" data-hl="part"><span>Partition ${i + 1}</span><b>0</b><i></i></div>`).join("")}</div>
      <p class="gs-pstat">Kabul edilen: <b class="ok">0</b> · Geri çevrilen: <b class="thr">0</b></p>`;
    const html = `${actorBar(DB)}<div class="gs-lanes">${shell("spread", Lb.spread || "Anahtarlar dağınık", boxes, { hl: "spread", count: "Yazma", result: false, col: true })}${shell("hot", Lb.hot || "Olsaydı: tek anahtar", boxes, { hl: "hot", count: "Yazma", result: false, col: true })}</div>${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = (f.ok || 0) + (f.thr || 0);
      L.classList.toggle("done", !!f.done);
      L.querySelectorAll(".gs-pbox").forEach((el) => {
        const i = Number(el.dataset.i), c = (f.cnt || [])[i] || 0;
        el.querySelector("b").textContent = c;
        el.querySelector("i").style.width = `${Math.min(100, (100 * c) / (lim * W))}%`;
        el.classList.toggle("now", (f.now || []).includes(i));
        el.classList.toggle("hot", id === "hot" && i === 0 && (f.thr || 0) > 0);
      });
      L.querySelector(".gs-pstat .ok").textContent = f.ok || 0;
      L.querySelector(".gs-pstat .thr").textContent = f.thr || 0;
      sayWho(L, f);
    }
    return { html, lanes, paint, final: showSum };
  }

  /* ---------- txn: a relational transaction. Changes inside BEGIN … are pending (only this transaction sees them); COMMIT
   * makes them durable and visible, ROLLBACK undoes them. spec.tables {name: {cols: [...], key, rows: [...]}},
   * spec.lanes [{id, title, ops: [{sql, say, do: "begin"|"update"|"insert"|"fail"|"commit"|"rollback", table, key, set, row}], send, back}]. */
  function txn(spec) {
    const DB = spec.engine_label || "Aurora PostgreSQL", tabs = spec.tables, names = Object.keys(tabs);
    const clone = (o) => JSON.parse(JSON.stringify(o));
    const lanes = {};
    spec.lanes.forEach((ln) => {
      const base = Object.fromEntries(names.map((n) => [n, tabs[n].rows]));
      const fr = [{ say: START, data: clone(base), pend: {}, phase: "", sqlNow: "", log: [] }];
      let s = clone(fr[0]);
      ln.ops.forEach((o) => {
        const n = clone(s);
        n.sqlNow = o.sql || ""; n.say = o.say || ""; n.log = [...s.log, o.sql || o.do];
        if (o.do === "begin") n.phase = "open";
        if (o.do === "update") { const r = n.data[o.table].find((x) => String(x[tabs[o.table].key]) === String(o.key)); Object.assign(r, o.set); n.pend[`${o.table}|${o.key}`] = "upd"; }
        if (o.do === "insert") { n.data[o.table].push(o.row); n.pend[`${o.table}|${o.row[tabs[o.table].key]}`] = "ins"; }
        if (o.do === "fail") n.phase = "fail";
        if (o.do === "commit") { n.phase = "commit"; n.pend = Object.fromEntries(Object.keys(n.pend).map((k) => [k, "ok"])); }
        if (o.do === "rollback") { n.phase = "rollback"; n.data = clone(base); n.undone = Object.keys(s.pend); n.pend = {}; }
        s = n; fr.push(s);
      });
      fr.push({ ...s, done: true, say: ln.end_say || s.say });
      lanes[ln.id] = actorize(fr, ln.send || "Uygulama transaction'ı başlatıyor.", ln.back || "Uygulama sonucu tarayıcıya gönderdi.", DB, { phase: "" });
    });
    const tableHtml = (n) => `<div class="gs-tx-t"><b>${esc(n)}</b><table class="gs-table" data-t="${esc(n)}"><thead><tr>${tabs[n].cols.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead><tbody></tbody></table></div>`;
    const body = `<div class="gs-tx-phase"></div><div class="gs-tx">${names.map(tableHtml).join("")}</div><pre class="gs-tx-sql" data-hl="sql"></pre>`;
    const html = `${actorBar(DB)}<div class="gs-lanes${spec.lanes.length === 1 ? " one" : ""}">${spec.lanes.map((ln) => shell(ln.id, ln.title, body, { hl: ln.id, count: "Komut", result: false, col: true })).join("")}</div>${summary(spec.summary || "")}`;
    const PH = { "": "", open: "Transaction açık: değişiklikleri sadece bu transaction görüyor", fail: "Hata: transaction yarıda kaldı", commit: "COMMIT: değişiklikler kalıcı ve herkese görünür", rollback: "ROLLBACK: bütün değişiklikler geri alındı" };
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = (f.log || []).length;
      L.classList.toggle("done", !!f.done);
      const ph = L.querySelector(".gs-tx-phase"); ph.textContent = PH[f.phase || ""]; ph.className = `gs-tx-phase ${f.phase || ""}`;
      names.forEach((n) => {
        const key = tabs[n].key;
        L.querySelector(`table[data-t="${CSS.escape(n)}"] tbody`).innerHTML = ((f.data || {})[n] || []).map((r) => {
          const st = (f.pend || {})[`${n}|${r[key]}`] || ((f.undone || []).includes(`${n}|${r[key]}`) ? "undone" : "");
          return `<tr class="tx-${st}">${tabs[n].cols.map((c) => `<td>${esc(r[c] ?? "")}</td>`).join("")}</tr>`;
        }).join("") || `<tr><td colspan="${tabs[n].cols.length}" class="empty">satır yok</td></tr>`;
      });
      L.querySelector(".gs-tx-sql").textContent = f.sqlNow || "";
      sayWho(L, f);
    }
    return { html, lanes, paint, final: showSum };
  }

  /* ---------- fanout: one action, several databases one after the other. spec.steps [{engine (id), label, cmd, say_send,
   * say_done, fail}], the actor of each database frame is that database. One lane. */
  function fanout(spec) {
    const fr = [{ say: START, cur: null, done: [], failed: [] }];
    let s = { ...fr[0] };
    spec.steps.forEach((x, k) => {
      s = { ...s, cur: k, who: spec.sender || APP_NAME, say: x.say_send || `${x.label}: istek gönderiliyor.` };
      fr.push(s);
      s = { ...s, who: x.label, done: x.fail ? s.done : [...s.done, k], failed: x.fail ? [...s.failed, k] : s.failed, say: x.say_done || `${x.label} yazdı.` };
      fr.push(s);
    });
    fr.push({ ...s, cur: null, who: spec.sender || APP_NAME, done: s.done, end: true, say: spec.back || "Bitti." });
    const html = `<div class="gs-actors" aria-hidden="true"><span data-a="app" data-hl="app">${esc(spec.sender_label || "Tarayıcıdaki sayfa + uygulama")}</span><i>⇄</i><span data-a="db" data-hl="db">Veritabanları</span></div>
      <div class="gs-lanes one">${shell("fan", spec.title || "Bir sipariş, altı veritabanı", `<ol class="gs-fan">${spec.steps.map((x, k) =>
        `<li data-k="${k}" class="eng-${esc(x.engine)}"><span class="chip">${esc(x.label)}</span><code>${esc(x.cmd)}</code><em></em></li>`).join("")}</ol>`, { count: "Tamamlanan", result: false, col: true })}</div>${summary(spec.summary || "")}`;
    function paint(root, id, f) {
      const L = laneOf(root, id);
      L.querySelector(".gs-count b").textContent = `${(f.done || []).length} / ${spec.steps.length}`;
      L.classList.toggle("done", !!f.end);
      L.querySelectorAll(".gs-fan li").forEach((li) => {
        const k = Number(li.dataset.k);
        li.classList.toggle("now", f.cur === k);
        li.classList.toggle("ok", (f.done || []).includes(k));
        li.classList.toggle("bad", (f.failed || []).includes(k));
        li.querySelector("em").textContent = (f.done || []).includes(k) ? "✓" : (f.failed || []).includes(k) ? "✗" : f.cur === k ? "…" : "";
      });
      sayWho(L, { ...f, who: f.who === (spec.sender || APP_NAME) ? APP_NAME : f.who });
    }
    return { html, lanes: { fan: fr }, paint, final: showSum };
  }

  /* ---------- Who works in a frame (owner rule: work of the app is never credited to the database).
   * actorize(frames, send, back, db): after START the app sends, every middle frame is the database's (unless it names
   * its own `who`), the last frame is the app sending the answer on. actorBar(db) is the bar above the lanes;
   * sayWho(L, f) writes the narration with its badge and lights the actor(s) of the visible frames. */
  const APP_NAME = "Uygulama";
  function actorize(frames, send, back, db, reset) {
    return [frames[0], { ...frames[0], ...(reset || {}), who: APP_NAME, say: send },
      ...frames.slice(1).map((f) => ({ ...f, who: f.who || db })), { ...frames[frames.length - 1], who: APP_NAME, say: back }];
  }
  const actorBar = (db) => `<div class="gs-actors" aria-hidden="true"><span data-a="app" data-hl="app">Uygulama (sunucudaki program)</span><i>⇄</i><span data-a="db" data-hl="db">${esc(db)} (veritabanı)</span></div>`;
  function sayWho(L, f) {
    L.querySelector(".gs-say").innerHTML = `${f.who ? `<b class="gs-who ${f.who === APP_NAME ? "app" : "db"}">${esc(f.who)}</b> ` : ""}${esc(f.say)}`;
    L.dataset.who = f.who === APP_NAME ? "app" : f.who ? "db" : "";
    const root = L.closest(".gs");
    if (!root) return;
    const ws = [...root.querySelectorAll(".gs-lane")].map((x) => x.dataset.who).filter(Boolean);
    root.querySelectorAll(".gs-actors [data-a]").forEach((x) => x.classList.toggle("on", ws.includes(x.dataset.a)));
  }

  const KINDS = { fanout, txn, spread, replicas, "ddb-items": ddbItems, projection, geo, facets, "inverted-index": invertedIndex, "nested-filter": nestedFilter, kv, "doc-group": docGroup, "index-vs-scan": indexVsScan, race, partition, "condition-write": conditionWrite, "graph-walk": graphWalk };

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
      timer = setInterval(() => { t += 1; show(); }, spec.tick_ms || TICK_MS);
      show();
    }
    root.querySelector("[data-g=play]").addEventListener("click", play);
    root.querySelector("[data-g=step]").addEventListener("click", () => { stop(); t = t >= total ? 0 : t + 1; show(); });
    root.querySelector("[data-g=reset]").addEventListener("click", () => { stop(); t = 0; show(); });
    show();
    new ResizeObserver(() => { if (!timer) show(); }).observe(root);   // graph edges follow the layout
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
