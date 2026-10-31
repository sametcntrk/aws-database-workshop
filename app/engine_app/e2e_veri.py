"""Simulations of the 00 tutorial "Veri nedir?" (templates/e2e/veri.tr.html). Turkish only.

The four simulations use the teaching data of e2e_sims (the same orders, order lines, customers and products as the
other tutorials), so the numbers on the page and in the simulations agree. static/js/e2e.js draws them.
"""
import json
from copy import deepcopy

from . import e2e_sims
from .e2e_sims import CUSTOMERS, ITEMS, ORDERS, PRODUCTS, T, _table

ROWS_PER_BLOCK = 3   # a teaching disk block holds three rows (a real block holds thousands)


def _cell(v):
    return f"{v}"


def tl(v):
    """Turkish money format: 48.324,99"""
    return f"{v:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")


# ---------------------------------------------------------------- 1. Row layout and column layout on disk
def row_vs_column(lang):
    """The same order lines on disk twice: row by row, then column by column. The report needs qty and unit_price."""
    cols, rows = ITEMS["cols"], ITEMS["rows"]
    need = [cols.index("qty"), cols.index("unit_price")]
    row_blocks = [[f"blok {b + 1}", " | ".join(", ".join(_cell(v) for v in r) for r in rows[b * ROWS_PER_BLOCK:(b + 1) * ROWS_PER_BLOCK])]
                  for b in range((len(rows) + ROWS_PER_BLOCK - 1) // ROWS_PER_BLOCK)]
    col_blocks = [[f"blok {i + 1}", f"{c}: " + ", ".join(_cell(r[i]) for r in rows)] for i, c in enumerate(cols)]
    total = round(sum(r[need[0]] * r[need[1]] for r in rows), 2)
    n_vals = len(rows) * len(cols)
    steps = [{"say": T(lang, None, f"Soru: bütün sipariş satırlarının cirosu ne? Yani her satırda qty × unit_price, sonra hepsinin toplamı. "
                                   f"Aynı {len(rows)} satır diskte iki kez duruyor: solda satır düzeninde, sağda sütun düzeninde. Bir blokta {ROWS_PER_BLOCK} satır ya da bir sütun var."),
              "marks": {}, "count": {"satır düzeni: okunan değer": 0, "sütun düzeni: okunan değer": 0}}]
    read_row = 0
    for b in range(len(row_blocks)):
        read_row += len(rows[b * ROWS_PER_BLOCK:(b + 1) * ROWS_PER_BLOCK]) * len(cols)
        steps.append({"say": T(lang, None, f"Satır düzeni, blok {b + 1}: bu bloktaki satırların hepsi gelir, order_id ve product_id de. "
                                           f"Rapor bu iki sütunu kullanmaz ama blok bir bütün olarak okunur."),
                      "marks": {"row": {**{i: "done" for i in range(b)}, b: "read"}},
                      "count": {"satır düzeni: okunan değer": read_row, "sütun düzeni: okunan değer": 0}})
    read_col = 0
    for i, c in enumerate(cols):
        used = i in need
        if used:
            read_col += len(rows)
        steps.append({"say": T(lang, None, f"Sütun düzeni, blok {i + 1} ({c}): " + (f"rapor bu sütunu kullanır, okunur." if used else
                                           f"rapor bu sütunu kullanmaz, blok hiç okunmaz.")),
                      "marks": {"row": {k: "done" for k in range(len(row_blocks))},
                                "col": {**{k: ("match" if k in need else "skip") for k in range(i)}, i: "read" if used else "skip"}},
                      "count": {"satır düzeni: okunan değer": read_row, "sütun düzeni: okunan değer": read_col}})
    steps.append({"say": T(lang, None, f"Sonuç ikisinde de aynı: ciro {tl(total)} TL. Satır düzeni {read_row} değer okudu, sütun düzeni {read_col}. "
                                       f"Rapor 4 sütunun 2'sini kullandığı için sütun düzeni işin yarısını yaptı. 100 sütunlu bir tabloda 3 sütun kullanan bir rapor için fark 30 kattan fazladır."),
                  "marks": {"row": {k: "done" for k in range(len(row_blocks))}, "col": {k: ("match" if k in need else "skip") for k in range(len(cols))}},
                  "out": [["ciro", tl(total)]], "outmarks": {0: "new"},
                  "count": {"satır düzeni: okunan değer": read_row, "sütun düzeni: okunan değer": read_col}})
    assert read_row == n_vals
    return {"tables": [{"id": "row", "name": T(lang, None, "satır düzeni (row-oriented)"), "cols": ["blok", T(lang, None, "içerik")], "rows": row_blocks, "key": [], "ref": []},
                       {"id": "col", "name": T(lang, None, "sütun düzeni (column-oriented)"), "cols": ["blok", T(lang, None, "içerik")], "rows": col_blocks, "key": [], "ref": []}],
            "out": {"name": T(lang, None, "sonuç"), "cols": [T(lang, None, "ölçü"), T(lang, None, "değer")]}, "steps": steps}


# ---------------------------------------------------------------- 2. The same orders as CSV, JSON and a columnar file
def _csv(rows, cols):
    return [",".join(cols)] + [",".join(_cell(v) for v in r) for r in rows]


def _json(rows, cols):
    return [json.dumps(dict(zip(cols, r)), ensure_ascii=False) for r in rows]


def file_formats(lang):
    cols, rows = ORDERS["cols"], ORDERS["rows"]
    csv_lines, json_lines = _csv(rows, cols), _json(rows, cols)
    csv_b = sum(len(x.encode()) + 1 for x in csv_lines)
    json_b = sum(len(x.encode()) + 1 for x in json_lines)
    names_b = len(rows) * sum(len(c.encode()) + 4 for c in cols)       # "name": plus quotes, colon and comma, in every object
    si = cols.index("status")
    dict_vals = sorted({r[si] for r in rows})
    col_rows = [[c, ", ".join(_cell(r[i]) for r in rows)] for i, c in enumerate(cols)]
    col_rows[si] = ["status", f"sözlük: {', '.join(f'{k}={v}' for k, v in enumerate(dict_vals))} · değerler: " +
                    ", ".join(str(dict_vals.index(r[si])) for r in rows)]
    ti = cols.index("total")
    stats = [["total", f"min {min(r[ti] for r in rows)} · max {max(r[ti] for r in rows)}"],
             ["order_date", f"min {min(r[2] for r in rows)} · max {max(r[2] for r in rows)}"]]
    want = "cancelled"
    hit = [i for i, r in enumerate(rows) if r[si] == want]
    steps = [{"say": T(lang, None, f"Aynı {len(rows)} sipariş üç dosya biçiminde. Soru: iptal edilen (status = '{want}') siparişlerin toplam tutarı ne?"),
              "marks": {}, "count": {"CSV byte": csv_b, "JSON byte": json_b}},
             {"say": T(lang, None, f"CSV: ilk satır sütun adlarını bir kez söyler, sonra her satır virgülle ayrılmış metindir. Dosya {csv_b} byte. "
                                   f"Bir okuyucu status'u bulmak için her satırı baştan sona okuyup virgülleri saymak zorundadır."),
              "marks": {"csv": {i: "read" for i in range(len(csv_lines))}}, "count": {"CSV byte": csv_b, "JSON byte": json_b}},
             {"say": T(lang, None, f"JSON: her sipariş kendi alan adlarını taşır. Dosya {json_b} byte; bunun {names_b} byte'ı tekrar eden alan adları ve tırnaklar. "
                                   f"Şema dosyada yazmaz, her satır kendini anlatır. Arama yine her satırı okur."),
              "marks": {"csv": {i: "done" for i in range(len(csv_lines))}, "json": {i: "read" for i in range(len(json_lines))}},
              "count": {"CSV byte": csv_b, "JSON byte": json_b}},
             {"say": T(lang, None, "Sütun bazlı ikili dosya (Parquet gibi): değerler sütun sütun durur. status sütunu sözlükle kodlanmış: "
                                   f"{len(dict_vals)} farklı metin bir kez yazılır, her satırda sadece küçük bir sayı durur. Dosyanın sonunda şema ve her sütunun min/max istatistiği vardır."),
              "marks": {"csv": {i: "done" for i in range(len(csv_lines))}, "json": {i: "done" for i in range(len(json_lines))}, "st": {0: "read", 1: "read"}},
              "count": {"CSV byte": csv_b, "JSON byte": json_b}},
             {"say": T(lang, None, f"Sorgu sadece status ve total sütunlarını okur. status'ta '{want}' sözlükte {dict_vals.index(want)} numaradır; "
                                   f"{len(hit)} satır eşleşir. order_id, customer_id ve order_date hiç okunmaz."),
              "marks": {"pq": {**{i: "skip" for i in range(len(cols))}, si: "read", ti: "read"}, "st": {0: "done", 1: "done"}},
              "out": [[rows[i][0], rows[i][ti]] for i in hit], "outmarks": {k: "new" for k in range(len(hit))},
              "count": {"CSV byte": csv_b, "JSON byte": json_b, "sütun dosyasında okunan sütun": 2}},
             {"say": T(lang, None, f"Sonuç üç biçimde de aynı: {tl(sum(rows[i][ti] for i in hit))} TL. Farkı ölçek yapar: milyonlarca satırda CSV ve JSON her byte'ı okur, "
                                   "sütun dosyası sadece gereken sütunları okur, min/max istatistiği aranan değeri içeremeyecek parçaları hiç açmadan atlar (bu küçük örnekte tek parça olduğu için atlanacak parça yok). Bu sayfadaki küçük örnekte sütun dosyasının byte sayısını vermiyoruz: "
                                   "başlık ve istatistik bölümü az satırda dosyayı büyütür, avantaj büyük veride ortaya çıkar."),
              "marks": {"pq": {**{i: "skip" for i in range(len(cols))}, si: "match", ti: "match"}},
              "out": [[rows[i][0], rows[i][ti]] for i in hit],
              "count": {"CSV byte": csv_b, "JSON byte": json_b, "sütun dosyasında okunan sütun": 2}}]
    return {"tables": [{"id": "csv", "name": "orders.csv", "cols": [T(lang, None, "satır")], "rows": [[x] for x in csv_lines], "key": [], "ref": []},
                       {"id": "json", "name": "orders.json (JSON Lines)", "cols": [T(lang, None, "satır")], "rows": [[x] for x in json_lines], "key": [], "ref": []},
                       {"id": "pq", "name": T(lang, None, "orders.parquet: sütun parçaları"), "cols": [T(lang, None, "sütun"), T(lang, None, "değerler")], "rows": col_rows, "key": [], "ref": []},
                       {"id": "st", "name": T(lang, None, "dosya sonu: istatistikler"), "cols": [T(lang, None, "sütun"), "min / max"], "rows": stats, "key": [], "ref": []}],
            "out": {"name": T(lang, None, "sonuç"), "cols": ["order_id", "total"]}, "steps": steps}


# ---------------------------------------------------------------- 3. A database connection, packet by packet
# Message names from the PostgreSQL frontend/backend protocol (https://www.postgresql.org/docs/current/protocol-flow.html).
# One row = one round trip (the client sends, then waits for the answer).
CONNECT = [
    ("Uygulama", "Sürücü", "getConnection(\"jdbc:postgresql://aurora-host:5432/shop?sslmode=verify-full\")", "Uygulamanın içinde: URL'nin başı (jdbc:postgresql) hangi sürücünün çalışacağını seçer.", 0, True),
    ("Sürücü", "DNS", "aurora-host adresini sor", "Ad, bir IP adresine çevrilir. Adres önbellekte yoksa DNS sunucusuna bir gidiş-dönüş gerekir; burada sayıyoruz.", 1, True),
    ("Sürücü", "Veritabanı", "TCP: SYN · SYN-ACK · ACK", "İki makine arasında bir bağlantı kurulur.", 1, True),
    ("Sürücü", "Veritabanı", "SSLRequest", "\"Şifreli konuşalım mı?\" Sunucu tek harfle cevap verir: S (evet).", 1, True),
    ("Sürücü", "Veritabanı", "TLS el sıkışması (TLS 1.3)", "Sunucu sertifikasını gösterir, sürücü onu doğrular, şifreleme anahtarı belirlenir.", 1, True),
    ("Sürücü", "Veritabanı", "StartupMessage (user=app, database=shop)", "Kim olduğunu ve hangi veritabanını istediğini söyler. Sunucu: AuthenticationSASL.", 1, True),
    ("Sürücü", "Veritabanı", "SASLInitialResponse (SCRAM-SHA-256)", "Şifre ağdan hiç geçmez; iki taraf şifreden türetilen değerlerle birbirini doğrular.", 1, True),
    ("Sürücü", "Veritabanı", "SASLResponse", "Kimlik doğrulandı: AuthenticationOk, ardından ReadyForQuery.", 1, True),
    ("Uygulama", "Veritabanı", "Query: SELECT name, price FROM products WHERE product_id = 'P0001'", "Sorgu metin olarak gider.", 1, False),
    ("Veritabanı", "Uygulama", "RowDescription · DataRow · CommandComplete · ReadyForQuery", "Önce sütunların adı ve tipi, sonra satır, sonra \"bitti\" gelir.", 0, False),
]


def connection(lang):
    rows = [[f"{a} → {b}", m] for a, b, m, _, _, _ in CONNECT]
    steps = [{"say": T(lang, None, "Bir Java uygulaması bir ürünün adını ve fiyatını istiyor (Lale Market'in Python kodu psycopg ile aynı mesajları gönderir). Henüz açık bir bağlantı yok: her şey sıfırdan kurulacak. "
                                   "Sayaç gidiş-dönüşleri sayar: bir mesaj gider, cevabı beklenir."),
              "marks": {}, "count": {"gidiş-dönüş": 0}}]
    rt = 0
    for i, (_, _, _, say, trip, _) in enumerate(CONNECT):
        rt += trip
        steps.append({"say": T(lang, None, say), "marks": {"c": {**{k: "done" for k in range(i)}, i: "read"}}, "count": {"gidiş-dönüş": rt}})
    setup = sum(t for *_, t, s in CONNECT if s)
    steps.append({"say": T(lang, None, f"Toplam {rt} gidiş-dönüş; bunların {setup} tanesi sadece bağlantıyı kurmak için. Sorgunun kendisi 1 gidiş-dönüş. "
                                       "Şimdi bağlantı havuzu (connection pool) ile aynı istek:"),
                  "marks": {"c": {k: ("skip" if CONNECT[k][5] else "match") for k in range(len(CONNECT))}}, "count": {"gidiş-dönüş": rt}})
    q = [i for i, c in enumerate(CONNECT) if not c[5]]
    steps.append({"say": T(lang, None, "Havuz, açık ve kimliği doğrulanmış bağlantıları saklar. Uygulama hazır bir bağlantı ödünç alır: DNS, TCP, TLS ve kimlik doğrulama atlanır. "
                                       "Sadece sorgu gider ve satır gelir. Bitince bağlantı kapanmaz, havuza geri döner."),
                  "marks": {"c": {**{k: "skip" for k in range(len(CONNECT)) if CONNECT[k][5]}, **{k: "match" for k in q}}},
                  "out": [[T(lang, None, "havuzsuz"), rt], [T(lang, None, "havuzlu"), rt - setup]], "outmarks": {1: "new"},
                  "count": {"gidiş-dönüş": rt - setup}})
    return {"tables": [{"id": "c", "name": T(lang, None, "bağlantının adımları"), "cols": [T(lang, None, "kimden → kime"), T(lang, None, "mesaj")], "rows": rows, "key": [], "ref": []}],
            "out": {"name": T(lang, None, "gidiş-dönüş sayısı"), "cols": [T(lang, None, "durum"), T(lang, None, "gidiş-dönüş")]}, "steps": steps}


# ---------------------------------------------------------------- 4. OLTP and OLAP on the same data
def oltp_olap(lang):
    pid, qty = "P0001", 1
    p_i = next(i for i, r in enumerate(PRODUCTS["rows"]) if r[0] == pid)
    prods = deepcopy(PRODUCTS["rows"])
    stock0 = prods[p_i][4]
    steps = [{"say": T(lang, None, f"Solda bir müşteri {pid}'den {qty} adet satın alıyor (OLTP). Sağda bir analist şehre göre ciroyu istiyor (OLAP). Aynı veri, iki farklı iş."),
              "marks": {}, "count": {"OLTP: dokunulan satır": 0, "OLAP: okunan satır": 0}}]
    prods[p_i][4] = stock0 - qty
    steps.append({"say": T(lang, None, f"OLTP 1: ürünün satırı key ile bulunur ve stok düşer: önce {stock0}, şimdi {stock0 - qty}. Tek satır; işlem bitene kadar kilitli, yani aynı satıra yazmak isteyen başka bir işlem bekler."),
                  "marks": {"p": {p_i: "lock"}}, "rows": {"p": deepcopy(prods)}, "count": {"OLTP: dokunulan satır": 1, "OLAP: okunan satır": 0}})
    steps.append({"say": T(lang, None, "OLTP 2: sipariş ve sipariş satırı yazılır, sonra COMMIT. Toplam 3 satıra dokunuldu ve iş milisaniyeler içinde bitti. Yoğun bir mağazada bu saniyede yüzlerce, binlerce kez olur."),
                  "marks": {"p": {p_i: "done"}}, "rows": {"p": deepcopy(prods)}, "count": {"OLTP: dokunulan satır": 3, "OLAP: okunan satır": 0}})
    city = {r[0]: r[3] for r in CUSTOMERS["rows"]}
    groups, read = {}, 0
    orows = [r for r in ORDERS["rows"] if r[3] != "cancelled"]
    for i, r in enumerate(ORDERS["rows"]):
        read += 1
        ok = r[3] != "cancelled"
        if ok:
            groups[city[r[1]]] = round(groups.get(city[r[1]], 0) + r[4], 2)
        steps.append({"say": T(lang, None, f"OLAP: sipariş {r[0]} okunur" + (f". Müşterisinin şehri {city[r[1]]}; tutarı o şehrin toplamına eklenir." if ok else ", iptal edilmiş; toplama girmez.")),
                      "marks": {"o": {**{k: "done" for k in range(i)}, i: "read" if ok else "skip"}, "p": {p_i: "done"}},
                      "out": [[c, tl(v)] for c, v in groups.items()],
                      "count": {"OLTP: dokunulan satır": 3, "OLAP: okunan satır": read}})
    steps.append({"say": T(lang, None, f"OLAP bitti: {read} siparişin hepsi okundu ve {len(groups)} satırlık bir sonuç çıktı. Gerçekte bu sorgu yıllarca birikmiş milyonlarca satırı okur. "
                                       "Bu yüzden OLAP genellikle ayrı bir analiz veritabanında çalışır: OLTP'nin kısa işlerini yavaşlatmasın."),
                  "marks": {"o": {k: ("done" if ORDERS["rows"][k][3] != "cancelled" else "skip") for k in range(len(ORDERS["rows"]))}, "p": {p_i: "done"}},
                  "out": [[c, tl(v)] for c, v in groups.items()], "outmarks": {k: "new" for k in range(len(groups))},
                  "count": {"OLTP: dokunulan satır": 3, "OLAP: okunan satır": read}})
    assert len(orows) <= read
    return {"tables": [_table("p", "products", PRODUCTS, key=[0]), _table("o", "orders", ORDERS, key=[0], ref=[1])],
            "out": {"name": T(lang, None, "OLAP sonucu: şehre göre ciro"), "cols": ["city", T(lang, None, "ciro (TL)")]}, "steps": steps}


def veri(lang):
    return {"rowcol": row_vs_column(lang), "formats": file_formats(lang), "connect": connection(lang), "oltp_olap": oltp_olap(lang)}


e2e_sims.SIMS["veri"] = veri
