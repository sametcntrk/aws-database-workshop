/* "Perde arkası" of one Guided step, in its own browser tab: /guided-e-commerce-app/perde-arkasi/<n> (templates/site/perde.html).
 *
 * The shop tab (mission.js) opens this tab when the reader does the step's action, and writes what happened to
 * localStorage "lm_perde_<n>" = {at, trig (the call that completed the step), page (every call of the shop page)}.
 * This tab draws the parts that need no data at once (need, concept, simulation, command), and the live numbers and the
 * request path when the data arrives. ?t=<ms> means "opened by this click": older data of an earlier visit is ignored.
 * Sections: need, concept, simulation (guided-sim.js), live numbers, the command piece by piece, the path of the request,
 * Akılda kalsın and why this database. Fields: ~/.claude/skills/guided-step/references/panel-schema.md.
 */
(function () {
  "use strict";
  const root = document.getElementById("perde");
  if (!root || !window.PA) return;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ENGINE_LABEL = { docdb: "DocumentDB", opensearch: "OpenSearch", neptune: "Neptune", dynamodb: "DynamoDB", aurora: "Aurora PostgreSQL",
    elasticache: "ElastiCache (Valkey)", keyspaces: "Keyspaces", s3: "S3", redshift: "Redshift", influxdb: "Timestream for InfluxDB" };
  const steps = PA.mission.steps || [];
  const n = PA.n, step = steps[n - 1], P = step.panel || {};
  const KEY = `lm_perde_${n}`;
  const since = Number(new URLSearchParams(location.search).get("t") || 0);
  const read = () => { try { const d = JSON.parse(localStorage.getItem(KEY)); return d && d.at >= since ? d : null; } catch (e) { return null; } };

  /* ---------- Live numbers */
  const STAGE_RE = /"stage":\s*"(\w+)"/g;
  const entryOf = (c) => (c && c.entries && c.entries[0]) || null;
  // One measured run: the first trace entry and the response data of one call. A metric names its source:
  // "ms", "items", "capacity" (trace entry), "examined", "returned" (DocumentDB explain), "data.<path>" (response body).
  const runOf = (c) => (c ? { e: entryOf(c) || {}, all: c.entries || [], data: c.data || {} } : null);
  function metric(run, key) {
    const e = run.e;
    if (key.startsWith("data.")) return key.slice(5).split(".").reduce((o, k) => (o == null ? undefined : o[k]), run.data);
    const nth = /^e(\d)\.(\w+)$/.exec(key);                     // "e1.ms": a field of the call's second trace entry
    if (nth) { const x = (run.all || [])[Number(nth[1])] || {}; return nth[2] === "ms" && x.ms !== undefined ? `${x.ms} ms` : x[nth[2]]; }
    const m = /docs examined:\s*(\d+),\s*returned:\s*(\d+)/.exec(e.explain || "");
    if (key === "examined") return m ? Number(m[1]) : undefined;
    if (key === "returned") return m ? Number(m[2]) : e.items;
    if (key === "ms") return e.ms !== undefined ? `${e.ms} ms` : undefined;
    if (key === "capacity") return e.capacity ? String(e.capacity).replace(/\s*\(.*\)$/, "") : undefined;   // "1 WRU (a failed ...)" → "1 WRU"
    return e[key];
  }
  const METRICS = [["Okunan doküman", "examined"], ["Dönen doküman", "returned"], ["Süre", "ms"]];
  function liveHtml(L, runs) {
    const metrics = L.metrics || METRICS;
    const max = L.bar ? Math.max(...runs.map((r) => (r && !r.error && Number(metric(r, L.bar))) || 0), 1) : 1;
    return `<div class="gp-runs">${L.runs.map((r, k) => {
      const run = runs[k];
      if (!run) return `<div class="gp-run"><h4>${esc(r.label)}</h4><p class="gp-wait">Ölçüm bekleniyor…</p></div>`;
      if (run.error) return "";                                    // a refused or failed call is left out
      const stages = [...String(run.e.plan || "").matchAll(STAGE_RE)].map((x) => x[1]).reverse().filter((x) => L.stages && L.stages[x]);   // the plan is outer → inner
      return `<div class="gp-run"><h4>${esc(r.label)}</h4>
        <dl>${(r.metrics || metrics).map(([label, key, map]) => {             // map {set, empty}: a text for a filled or an empty value
          const v = metric(run, key);
          return `<div><dt>${esc(label)}</dt><dd>${esc(map ? (v ? map.set : map.empty) : v ?? "?")}</dd></div>`;
        }).join("")}</dl>
        ${L.bar ? `<div class="gp-bar" aria-hidden="true"><span style="width:${Math.round(100 * (Number(metric(run, L.bar)) || 0) / max)}%"></span></div>` : ""}
        ${stages.length ? `<p class="gp-stages-cap">${esc(L.stages_cap || "Veritabanının yaptığı işler, sırasıyla:")}</p><ol class="gp-stages">${stages.map((x) =>
          `<li><code>${esc(x)}</code> ${esc(L.stages[x])}</li>`).join("")}</ol>` : ""}</div>`;
    }).join("")}</div>`;
  }
  // Sources of a run: trigger (the call that completed the step), page_call {path, query} (a call the page made before),
  // fetch (a measurement for this tab only: GET, or method + body; body_from_trigger merges over the trigger's body).
  async function fillLive(L, d) {
    const box = root.querySelector(".gp-live");
    if (!box) return;
    const trig = d && d.trig, page = (d && d.page) || [];
    const same = (c, pc) => c.path === pc.path && Object.entries(pc.query || {}).every(([k, v]) => String((c.query || {})[k]) === String(v));
    const runs = L.runs.map((r) => (!d ? null : r.trigger ? (trig && trig.ok === false ? { error: true } : runOf(trig))
      : r.page_call ? runOf([...page].reverse().find((c) => same(c, r.page_call))) || { error: true } : null));
    box.innerHTML = liveHtml(L, runs);
    if (!d) return;
    await Promise.all(L.runs.map(async (r, k) => {
      if (!r.fetch) return;
      try {
        const body = r.body_from_trigger ? { ...((trig && trig.body) || {}), ...r.body_from_trigger } : r.body;
        const init = body ? { method: r.method || "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {};
        const j = await (await fetch(r.fetch, init)).json();
        runs[k] = j.ok === false ? { error: true } : runOf({ entries: j.trace, data: j.data });
      } catch (e) { runs[k] = { error: true }; }
    }));
    box.innerHTML = liveHtml(L, runs);
  }

  /* ---------- The command: each column (lane or command) as a Turkish sentence and as code, then one card per piece.
   * The same colour marks one piece in every place (q0..q5). */
  function queryHtml(Q, no) {
    const parts = Q.parts || [];
    const byId = Object.fromEntries(parts.map((x) => [x.id, x]));
    const col = (k) => `q${k % 6}`;
    const piece = (x) => `data-q="${esc(x.id)}" tabindex="0"`;
    const column = (c) => {
      const list = (c.parts || []).map((id) => byId[id]).filter(Boolean);
      const say = list.map((x) => `<span class="${col(parts.indexOf(x))}" ${piece(x)}>${esc(x.say)}</span>`).join(" ");
      const code = list.map((x) => `<span class="gq-line ${col(parts.indexOf(x))}${(c.mark || []).includes(x.id) ? " added" : ""}" ${piece(x)}><b>${parts.indexOf(x) + 1}</b>${" ".repeat(x.indent || 0)}${esc(x.code)}</span>`).join("");
      return `<div class="gq-col"><h4>${esc(c.label || "")}</h4>${c.sub ? `<p class="gq-sub">${esc(c.sub)}</p>` : ""}
        ${c.via ? `<p class="gq-via">${esc(c.via)}</p>` : ""}
        <span class="gq-label">Türkçesi</span><p class="gq-say">${say}${list.length && /[.!?]$/.test(list[list.length - 1].say) ? "" : "."}</p>
        <span class="gq-label">Komut</span><pre class="gq-code">${code}</pre></div>`;
    };
    const cols = Q.columns || [];
    return `<section class="gp-sec gq" id="pa-cmd"><h3><span>${no}</span>${esc(Q.title || "Sorgu")}</h3><p>${esc(Q.intro || "")}</p>
      <div class="${cols.length > 1 ? "gq-two" : "gq-one"}">${cols.map(column).join("")}</div>
      ${Q.note ? `<p class="gq-diff-note">${esc(Q.note)}</p>` : ""}
      <h4 class="gq-cards-title">${esc(Q.cards_title || "Parça parça")}</h4>
      <ol class="gq-cards">${parts.map((x, k) => `<li class="${col(k)}" ${piece(x)}><header><b>${k + 1}</b><strong>${esc(x.name || "")}</strong><code>${esc(x.code)}</code>
        ${x.tag ? `<em>${esc(x.tag)}</em>` : ""}</header><p>${esc(x.note)}</p></li>`).join("")}</ol></section>`;
  }

  /* ---------- The path of the request: browser → load balancer → app → database, from the trace entry */
  const AUTH = [
    [/IAM/i, "IAM rolü: şifre yok. Uygulama, AWS'nin verdiği geçici kimlikle her isteği imzalıyor (SigV4). Veritabanı imzayı kontrol ediyor."],
    [/Password/i, "Şifre: Uygulama şifreyi çalışırken AWS Secrets Manager'dan alıyor. Şifre kodda ya da sunucuda yazılı durmuyor."],
  ];
  // The last stop, by the kind of endpoint in the trace path (catalog.META[engine].via)
  const last = (via) => (/gateway endpoint/i.test(via)
    ? "Bu, AWS'nin bölge çapında çalışan bir servisi. Uygulama ona internete çıkmadan, VPC'nin gateway endpoint'i (AWS'nin iç ağına açılan özel bir kapı) üzerinden ulaşıyor."
    : /interface endpoint/i.test(via)
      ? "Bu, AWS'nin bölge çapında çalışan bir servisi. Uygulama ona internete çıkmadan, özel ağdaki bir interface endpoint (servise açılan özel bir ağ kartı) üzerinden ulaşıyor."
      : "Veritabanı internete kapalı veri alt ağında duruyor. Güvenlik grubu kuralı sadece bu veritabanının uygulama sunucusundan gelen bağlantıya izin veriyor.");
  function pathHtml(d) {
    const trig = d && d.trig, e = entryOf(trig);
    if (!e || !e.path) return `<p class="gp-wait">Yol, mağaza sekmesindeki istek bitince burada görünür.</p>`;
    const m = /^EC2\s+(\S+)\s*→\s*(.+)$/.exec(e.path) || [];
    const auth = (AUTH.find(([re]) => re.test(e.auth || "")) || [null, e.auth || ""])[1];
    const box = (title, tech, text) => `<div class="pa-hop"><b>${esc(title)}</b>${tech ? `<code>${esc(tech)}</code>` : ""}<p>${esc(text)}</p></div>`;
    return `<div class="pa-path">
        ${box("Tarayıcın", "", `${step.action === "look" ? "Sayfayı açtığın" : "Butona tıkladığın"} yer. Tarayıcı veritabanına hiçbir zaman doğrudan bağlanmaz.`)}
        <span class="pa-arrow">HTTPS →</span>
        ${box("Yük dengeleyici (ALB)", location.host, "İsteği karşılayan kapı. İsteği hangi veritabanının uygulama sunucusuna göndereceğine adrese bakarak karar verir.")}
        <span class="pa-arrow">→</span>
        ${box("Uygulama (EC2 sunucusu)", m[1] ? `özel ağdaki IP ${m[1]}` : "", "Mağazanın arka uç programı. İsteği alır, veritabanına komutu gönderir, cevabı hazırlar. İnternetten doğrudan erişilemeyen özel bir ağda çalışır.")}
        <span class="pa-arrow">→</span>
        ${box(e.engine || "Veritabanı", m[2] || "", last(m[2] || ""))}
      </div>
      <dl class="pa-facts">
        <div><dt>Kimlik doğrulama</dt><dd>${esc(auth)}</dd></div>
        <div><dt>Toplam süre (tarayıcıdan)</dt><dd>${esc(trig.ms)} ms</dd></div>
        <div><dt>Veritabanında geçen süre</dt><dd>${esc(e.ms)} ms</dd></div>
      </dl>
      <p class="gp-reading">Toplam süre, isteğin tarayıcından çıkıp cevabın geri gelmesine kadar geçen süre: internet, yük dengeleyici ve
        Uygulama da bu süreye dahil. Veritabanında geçen süre ise sadece uygulama ile veritabanı arasındaki kısım. Aradaki fark,
        çoğu zaman ağın ve uygulamanın payıdır.</p>`;
  }

  /* ---------- t-1: what was there before the action, and where the data comes from (panel.prior, panel.feed) */
  function priorHtml(R, F) {
    const paras = [].concat((R && R.text) || []).map((x, k) => (typeof x === "string" ? `<p>${esc(x)}</p>`
      : `<div class="pa-prep"><h4><span>${k + 1}</span>${esc(x.title || "")}</h4><p>${esc(x.text || "")}</p>${x.code ? `<pre class="pa-prep-code">${esc(x.code)}</pre>` : ""}</div>`)).join("");
    const feed = F ? `<div class="pa-feed"><h4>${esc(F.title || "Veri nereden geliyor?")}</h4><dl>
        ${[["Kim yazıyor?", F.writes], ["Kim okuyor?", F.reads], ["Nasıl besleniyor?", F.kind], ["Yanındaki veritabanları", F.with], ["En iyi uygulama", F.best]]
          .filter(([, v]) => v).map(([t, v]) => `<div><dt>${esc(t)}</dt><dd>${esc(v)}</dd></div>`).join("")}</dl></div>` : "";
    return paras + feed;
  }

  /* ---------- t0: the request on the wire, as three packets. Live values come from the call (net, trace path);
   * a value the app cannot see is marked "örnek". panel.wire describes the last hop of the engine. */
  const tag = (live) => `<em class="${live ? "pa-live" : "pa-ex"}">${live ? "gerçek" : "örnek"}</em>`;
  function packet(no, title, what, rows, body) {
    return `<div class="pa-pkt"><header><b>Paket ${no}</b><strong>${esc(title)}</strong></header><p>${esc(what)}</p>
      <table>${rows.map(([k, v, live, note]) => `<tr><th>${esc(k)}</th><td><code>${esc(v)}</code> ${tag(live)}</td><td>${esc(note || "")}</td></tr>`).join("")}</table>
      ${body ? `<span class="gq-label">${esc(body.label)}</span><pre class="pa-pkt-body">${esc(body.text)}</pre>` : ""}</div>`;
  }
  function packetsHtml(d) {
    const trig = d && d.trig, e = entryOf(trig), net = (trig && trig.net) || {}, W = P.wire || {};
    const m = /^EC2\s+(\S+)\s*→\s*(.+)$/.exec((e && e.path) || "") || [];
    const site = /^[\d.]+(:\d+)?$|^localhost/.test(location.host) ? "" : location.host;      // a preview by IP is not the real site name
    const host = net.host || site || "dbworkshop.tdsynnexlab.link", hostLive = !!(net.host || site), path = net.path || (trig ? trig.path + (Object.keys(trig.query || {}).length ? "?" + new URLSearchParams(trig.query) : "") : "/…");
    const method = net.method || (trig && trig.method) || "GET";
    const appIp = net.app || m[1];
    const p1 = packet(1, "Tarayıcın → Yük dengeleyici (ALB)",
      "Tarayıcın internet üzerinden ALB'ye bir HTTPS isteği gönderir. Yolda içerik şifrelidir; dışarıdan bakan sadece adresleri ve hangi siteye gidildiğini (SNI) görür.", [
        ["Kaynak", `${net.client || "88.230.14.x"} : rastgele port`, !!net.client, "Senin internet adresin (son kısmı gizlendi). Port, tarayıcının bu bağlantı için seçtiği geçici bir numara."],
        ["Hedef", `${host} : 443`, hostLive, "ALB'nin internete açık adresi. 443, HTTPS'in kapısı."],
        ["Şifreleme", "TLS 1.3 (ya da 1.2)", false, "ALB sadece TLS 1.2 ve 1.3 kabul eder. Hangisinin seçildiğini tarayıcı ile ALB anlaşır."],
        ["SNI", host, hostLive, "Şifreleme başlamadan önce tarayıcının söylediği site adı. ALB doğru sertifikayı buna göre seçer."],
      ], { label: "Şifrenin içindeki istek (ALB açar)", text: `${method} ${path} HTTP/1.1\nHost: ${host}\nCookie: lm_visitor=7f3a…   (bu tarayıcının kimliği)\nAccept: application/json` });
    const p2 = packet(2, "ALB → Uygulama (EC2 sunucusu)",
      `ALB şifreyi çözer ve adrese bakar: ${path.split("/")[1] ? `"/${path.split("/")[1]}/..." ile başlayan istekler bu veritabanıyla konuşan uygulama sunucusuna gider.` : "adrese göre doğru uygulamayı seçer."} İstek artık AWS'nin içindeki özel ağda.`, [
        ["Kaynak", `${net.lb || "10.20.x.x"} : rastgele port`, !!net.lb, "ALB'nin özel ağdaki adresi."],
        ["Hedef", `${appIp || "10.20.x.x"} : ${net.app_port || 8000}`, !!appIp, "Uygulamanın çalıştığı EC2 sunucusu ve uygulamanın dinlediği kapı."],
        ["Protokol", "HTTP (şifresiz, özel ağ içinde)", true, "Bu ağa internetten girilemez; güvenlik grubu sadece ALB'den gelen bağlantıyı kabul eder."],
      ], { label: "ALB'nin isteğe eklediği satırlar", text: `X-Forwarded-For: ${net.client || "88.230.14.x"}   (isteğin asıl sahibi: sen)\nX-Forwarded-Proto: ${net.proto || "https"}   (tarayıcı HTTPS ile gelmişti)` });
    const p3 = packet(3, `Uygulama → ${(e && e.engine) || "Veritabanı"}`, W.what || "Uygulama veritabanına bağlanır ve komutu gönderir.", [
        ["Kaynak", `${appIp || "10.20.x.x"}`, !!appIp, "Aynı EC2 sunucusu."],
        ["Hedef", W.dst || m[2] || "?", !!(W.dst || m[2]), W.dst_note || last(m[2] || "")],
        ...(W.rows || []).map((r) => [r[0], r[1], r[2] !== "örnek", r[3]]),
      ], W.body ? { label: W.body_label || "Gönderilen", text: W.body } : null);
    return `<div class="pa-pkts">${p1}${p2}${p3}</div>`;
  }

  /* ---------- t0: a short excerpt of the real route code (PA.code, built from the repo by web.py) */
  function codeHtml(list) {
    return (list || []).map((c) => `<div class="pa-code"><h4>${esc(c.title || "")}</h4>${c.sub ? `<p class="gq-sub">${esc(c.sub)}</p>` : ""}
      <ol>${c.lines.map((l) => `${l.gap ? `<li class="pa-gap">…</li>` : ""}<li ${l.hl ? `data-hl="${esc(l.hl)}"` : ""}><code><b>${l.no}</b>${esc(l.code.trim())}</code>
        <span>${[].concat(l.tag || []).map((t) => `<em class="${/içinde/.test(t) ? "in" : "go"}">${esc(t)}</em>`).join("")}${esc(l.say)}</span></li>`).join("")}</ol>
      <small>Kaynak: ${esc(c.file)} (repodaki gerçek kod; sadece bu adımla ilgili satırlar)</small></div>`).join("");
  }

  /* ---------- t+1: the answer goes back. {read}, {items}, {ms} in a text come from the call that completed the step. */
  function backHtml(B, d) {
    const e = entryOf(d && d.trig) || {};
    const val = (k) => (k === "items" ? (d && d.trig && Array.isArray(d.trig.data) ? d.trig.data.length : e.items) : e[k]);
    const fillIn = (t) => esc(t).replace(/\{(\w+)\}/g, (_, k) => (val(k) !== undefined ? `<b>${esc(val(k))}</b>` : `<b class="pa-ex">…</b>`));
    return `<ol class="pa-back">${(B.steps || []).map((x) => `<li><b class="pa-who">${esc(x.who)}</b><p>${fillIn(x.text)}</p></li>`).join("")}</ol>`;
  }

  /* ---------- The page */
  const chips = () => (step.engines || []).map((e) => `<span class="chip eng-${e}">${esc(ENGINE_LABEL[e] || e)}</span>`).join("");
  let sim = null;
  function draw() {
    const C = P.concept || {};
    let no = 0;
    const h = (title) => `<h3><span>${++no}</span>${esc(title)}</h3>`;
    const phase = (id, t, title, intro) => `<div class="pa-phase" id="${id}"><span>${t}</span><div><h2>${esc(title)}</h2>${intro ? `<p>${esc(intro)}</p>` : ""}</div></div>`;
    const strip = [["pa-need", "", "Ne lazım?"], ...(P.prior || P.feed ? [["pa-t1", "t-1", "Önceden"]] : []), ["pa-t0", "t0", step.action === "look" ? "Sayfa açılınca" : "Tıklaman"],
      ...(P.back ? [["pa-t2", "t+1", "Cevap dönünce"]] : []), ["pa-keep", "", "Akılda kalsın"]];
    root.className = `gp pa-page eng-${(step.engines || [])[0] || "docdb"}`;
    root.innerHTML = `<header class="gp-head pa-head"><div><span class="gp-kicker">Perde arkası</span>${chips()}${step.use_case ? `<em>${esc(step.use_case)}</em>` : ""}
        <h1>${esc(step.title)}</h1></div>
      <div class="gp-nav"><small>Adım ${n} / ${steps.length}</small><button type="button" class="primary" data-c="back">Mağaza sekmesine dön</button></div>
      <nav class="pa-strip" aria-label="Zaman şeridi">${strip.map(([id, t, l]) => `<a href="#${id}">${t ? `<b>${t}</b>` : ""}${esc(l)}</a>`).join("<i>→</i>")}</nav></header>
      <p class="pa-status" hidden></p>
      <div class="gp-body pa-body">
        <div class="gp-intro" id="pa-need"><section class="gp-sec">${h("Ne lazım?")}<p>${esc(P.need)}</p></section>
        <section class="gp-sec">${h(`Kavram: ${C.term || ""}`)}<p>${esc(C.text || "")}</p></section></div>
        ${(C.terms || []).length ? `<dl class="gp-terms">${C.terms.map(([t, d]) => `<div><dt>${esc(t)}</dt><dd>${esc(d)}</dd></div>`).join("")}</dl>` : ""}
        ${P.prior || P.feed ? phase("pa-t1", "t-1", "Önceden ne vardı?", (P.prior || {}).intro) : ""}
        ${P.prior || P.feed ? `<section class="gp-sec">${h((P.prior || {}).title || "Bu adımdan önce")}${priorHtml(P.prior, P.feed)}</section>` : ""}
        ${phase("pa-t0", "t0", P.now_title || (step.action === "look" ? "Sayfa açılınca ne oldu?" : "Senin tıklamanla ne oldu?"), P.now_intro)}
        ${P.scenario ? `<section class="gp-sec pa-scn">${h(P.scenario.title || "Ne oldu? Senin gözünden")}<p>${esc(P.scenario.intro || "")}</p>
          <ol>${(P.scenario.steps || []).map((x) => `<li><p>${esc(x.text)}</p>${(x.engines || []).length ? `<span class="pa-scn-db">${x.engines.map((e) =>
            `<span class="chip eng-${e}">${esc(ENGINE_LABEL[e] || e)}</span>`).join("")}</span>` : ""}</li>`).join("")}</ol></section>` : ""}
        ${P.sim ? `<section class="gp-sec">${h("Simülasyon")}<div class="gp-sim"></div></section>` : ""}
        <section class="gp-sec pa-route">${h("İstek nereden geçti?")}<p>${step.action === "look" ? "Sayfa açılırken giden" : "Senin tıklamanla giden"}
          istek, veritabanına ulaşana kadar bu duraklardan geçti. Bilgiler isteğin kendi kaydından geliyor.</p><div class="pa-path-box"></div>
          <h4 class="gq-cards-title">Yoldaki paketler</h4><p>Aynı yolculuk, ağın gördüğü hâliyle: her durakta bir paket. "gerçek" yazan değerler senin isteğinden ve bu kurulumdan,
          "örnek" yazanlar uygulamanın göremediği ama gerçekte buna benzeyen değerler.</p><div class="pa-pkts-box"></div></section>
        ${PA.code ? `<section class="gp-sec">${h(P.code_title || "Uygulamanın içinde: gerçek koddan kısa bir kesit")}<p>${esc(P.code_intro || "")}</p>
          <div class="${PA.code.length > 1 ? "gq-two" : "gq-one"}">${codeHtml(PA.code)}</div></section>` : ""}
        ${P.query ? queryHtml(P.query, ++no) : ""}
        ${P.live ? `<section class="gp-sec">${h(P.live.title || "Sistemde gerçekte ne oldu?")}<p>${esc(P.live.intro || "")}</p>
          <div class="gp-live"></div><p class="gp-reading">${esc(P.live.reading || "")}</p></section>` : ""}
        ${P.back ? `${phase("pa-t2", "t+1", P.back.title || "Cevap dönünce", P.back.intro)}
          <section class="gp-sec">${h(P.back.flow_title || "Cevabın yolu")}<div class="pa-back-box"></div></section>` : ""}
        <section class="gp-sec gp-keep" id="pa-keep"><h3>Akılda kalsın</h3><p>${esc(P.remember || "")}</p>${P.why_db ? `<p class="gp-why">${esc(P.why_db)}</p>` : ""}</section>
      </div>`;
    root.querySelector("[data-c=back]").addEventListener("click", () => { if (window.opener) { window.opener.focus(); window.close(); } else history.back(); });
    if (P.sim && window.GuidedSim) {
      sim = GuidedSim.render(root.querySelector(".gp-sim"), P.sim);
      const io = new IntersectionObserver((seen) => {                // the simulation plays once, when it comes into view
        if (seen.some((x) => x.isIntersecting)) { io.disconnect(); setTimeout(() => sim.play(), 400); }
      }, { threshold: 0.35 });
      io.observe(root.querySelector(".gp-sim"));
    }
    root.querySelectorAll(".pa-code li[data-hl]").forEach((el) => {    // a line of the app code lights its part of the simulation
      const on = () => sim && sim.highlight(el.dataset.hl), off = () => sim && sim.highlight(null);
      el.tabIndex = 0;
      el.addEventListener("mouseenter", on); el.addEventListener("focus", on); el.addEventListener("mouseleave", off); el.addEventListener("blur", off);
    });
    root.querySelectorAll(".gq [data-q]").forEach((el) => {        // one piece of the command: the sentence, the code and the card light up together
      const part = ((P.query || {}).parts || []).find((x) => x.id === el.dataset.q) || {};
      const on = () => { root.querySelectorAll(`.gq [data-q="${el.dataset.q}"]`).forEach((x) => x.classList.add("on")); if (sim) sim.highlight(part.hl); };
      const off = () => { root.querySelectorAll(".gq .on").forEach((x) => x.classList.remove("on")); if (sim) sim.highlight(null); };
      el.addEventListener("mouseenter", on); el.addEventListener("focus", on);
      el.addEventListener("mouseleave", off); el.addEventListener("blur", off);
    });
  }
  function fill() {
    const d = read();
    const status = root.querySelector(".pa-status");
    status.hidden = !!d;
    status.textContent = "Mağaza sekmesindeki istek bekleniyor. İstek bitince ölçümler ve isteğin yolu burada kendiliğinden görünür.";
    if (P.live) fillLive(P.live, d);
    root.querySelector(".pa-path-box").innerHTML = pathHtml(d);
    root.querySelector(".pa-pkts-box").innerHTML = packetsHtml(d);
    const bb = root.querySelector(".pa-back-box");
    if (bb) bb.innerHTML = backHtml(P.back, d);
    return !!d;
  }

  document.title = `Perde arkası · ${step.title} · Lale Market`;
  if (!step.panel) { root.innerHTML = `<p class="pa-status">Bu adımın perde arkası henüz hazırlanmadı.</p>`; return; }
  draw();
  if (!fill()) {
    const onStore = (ev) => { if (ev.key === KEY && fill()) removeEventListener("storage", onStore); };   // the shop tab writes the data
    addEventListener("storage", onStore);
  }
})();
