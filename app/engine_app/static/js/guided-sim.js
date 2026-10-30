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
    frames.push({ phase: 0, who: APP, say: `Sayfa açıldı. Uygulama "bu ürüne baktın" bilgisini bir INSERT komutuyla Keyspaces'e gönderiyor. Satırın user_id'si bu tarayıcının kimliği.` });
    frames.push({ phase: 1, who: DB, lit: me, say: `INSERT geldi: user_id = ${parts[me].label}. Keyspaces bu değere bakar ve satırın hangi partition'a gideceğini bulur. Diğer partition'lara dokunmaz.` });
    frames.push({ phase: 2, who: DB, lit: me, inserted: true, say: "Yeni satır partition'ın en üstüne girdi. Tablo satırları event_time'a göre yeniden eskiye sıralı tutuyor; sıralama yazarken yapılıyor, okurken değil." });
    // 2) the read: the app asks, the engine returns rows as they are
    frames.push({ phase: 3, who: APP, lit: me, inserted: true, select: true, touched: 1, say: `Şimdi uygulama "Son baktıkların" şeridi için SELECT ... WHERE user_id = ${parts[me].label} LIMIT ${lim} gönderiyor.` });
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
      say: `Uygulama listenin en fazla ${cap} ürününü tarayıcıya gönderdi (burada ${result.length} ürün var). Tabloda ${total} satır var; Keyspaces sadece ${mine.length} tanesini okudu, süzmeyi uygulama yaptı.` });
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

  const KINDS = { "index-vs-scan": indexVsScan, race, partition, "condition-write": conditionWrite, "graph-walk": graphWalk };

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
