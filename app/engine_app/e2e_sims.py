"""Step-by-step simulations for the E2E tutorials (static/js/e2e.js draws them).

A simulation shows small input tables and plays the work of the Engine one step at a time:
which row it reads, which row matches, what goes to the result. The steps are computed here from the data,
so the text and the numbers always agree. No database is needed.

Spec: {"tables": [{"id", "name", "cols", "rows", "key": [col idx], "ref": [col idx], "caption"}],
       "out": {"name", "cols"} | None,
       "steps": [{"say", "marks": {table id: {row idx: cls}}, "rows": {table id: rows} (optional new values),
                  "out": [rows], "outmarks": {row idx: cls}, "count": {label: value}}]}
Mark classes: read, match, skip, lock, new, bad, done.
"""
from copy import deepcopy

# A small teaching copy of the Lale Market shop. Names and prices come from the real data; the stock values and
# the orders after O000001 are examples.
CUSTOMERS = {
    "cols": ["customer_id", "name", "email", "city", "segment"],
    "rows": [["C00001", "Ayşe Yılmaz", "ayse.yilmaz@example.com", "İstanbul", "premium"],
             ["C00002", "Mert Doğan", "mert.dogan@example.com", "Ankara", "kurumsal"],
             ["C00003", "Elif Kaya", "elif.kaya@example.com", "İzmir", "bireysel"],
             ["C00004", "Lukas Weber", "lukas.weber@example.com", "Frankfurt", "premium"],
             ["C00005", "Zeynep Şahin", "zeynep.sahin@example.com", "İstanbul", "bireysel"],
             ["C00006", "Can Demir", "can.demir@example.com", "Bursa", "bireysel"]],
}
PRODUCTS = {
    "cols": ["product_id", "name", "category", "price", "stock"],
    "rows": [["P0001", "Alpen Kablosuz Kulaklık 1", "Elektronik", 3373.84, 127],
             ["P0044", "Kapadokya Bulut Mimarisi 44", "Kitap", 2651.39, 216],
             ["P0095", "Anadolu Yün Kazak 95", "Moda", 2721.65, 76],
             ["P0142", "Ege Hava Temizleyici 142", "Ev & Yaşam", 2693.65, 84],
             ["P0179", "Toros Python ile Veri 179", "Kitap", 767.49, 445]],
}
ITEMS = {
    "cols": ["order_id", "product_id", "qty", "unit_price"],
    "rows": [["O000001", "P0044", 1, 2651.39], ["O000001", "P0095", 1, 2721.65], ["O000001", "P0142", 3, 2693.65],
             ["O000001", "P0179", 2, 767.49], ["O000102", "P0001", 5, 3373.84], ["O000102", "P0179", 10, 767.49],
             ["O000103", "P0044", 2, 2651.39], ["O000103", "P0179", 1, 767.49], ["O000104", "P0095", 1, 2721.65]],
}
_status = {"O000001": ("C00001", "2026-06-08", "delivered"), "O000102": ("C00002", "2026-09-04", "shipped"),
           "O000103": ("C00004", "2026-10-02", "delivered"), "O000104": ("C00005", "2026-10-20", "cancelled")}
ORDERS = {
    "cols": ["order_id", "customer_id", "order_date", "status", "total"],
    "rows": [[oid, c, d, s, round(sum(q * p for o, _, q, p in ITEMS["rows"] if o == oid), 2)] for oid, (c, d, s) in _status.items()],
}


def tables():
    """The sample tables for the page text (the same data as the simulations)."""
    out = {"customers": CUSTOMERS, "products": PRODUCTS, "orders": ORDERS, "order_items": ITEMS}
    out.update(EXTRA_TABLES)
    return out


EXTRA_TABLES = {}   # teaching tables of the other Engines (filled below their builders)


def money(v):
    return f"{v:,.2f}"


def T(lang, en, tr):
    """en may be None while a page is in review: then the Turkish text is used in both languages."""
    return tr if lang == "tr" or en is None else en


def _table(tid, name, data, key=(), ref=(), caption=None, rows=None):
    return {"id": tid, "name": name, "cols": data["cols"], "rows": deepcopy(rows if rows is not None else data["rows"]),
            "key": list(key), "ref": list(ref), "caption": caption}


# ---------------------------------------------------------------- 1. WHERE: the Engine tests each row
def where_city(lang):
    city = "İstanbul"
    rows = CUSTOMERS["rows"]
    steps = [{"say": T(lang, f"The query asks for the customers whose city is '{city}'. There is no index on city, so PostgreSQL starts at the first row and tests each row.",
                       f"Query, city değeri '{city}' olan müşterileri istiyor. city üzerinde index yok, bu yüzden PostgreSQL ilk row'dan başlar ve her row'u tek tek test eder."),
              "marks": {}, "out": [], "count": {"rows read": 0, "rows returned": 0}}]
    out, marks = [], {}
    for i, r in enumerate(rows):
        hit = r[3] == city
        marks = {**{k: ("match" if v == "match" else "done") for k, v in marks.items()}, i: "match" if hit else "read"}
        if hit:
            out.append([r[0], r[1], r[3]])
        say = (T(lang, f"Row {i + 1}: {r[1]}, city = '{r[3]}'. This is '{city}', so the row goes to the result.",
                 f"Row {i + 1}: {r[1]}, city = '{r[3]}'. Bu '{city}', bu yüzden row sonuca gider.") if hit else
               T(lang, f"Row {i + 1}: {r[1]}, city = '{r[3]}'. This is not '{city}', so PostgreSQL skips the row. It still had to read it.",
                 f"Row {i + 1}: {r[1]}, city = '{r[3]}'. Bu '{city}' değil, bu yüzden PostgreSQL row'u atlar. Ama yine de okumak zorunda kaldı."))
        steps.append({"say": say, "marks": {"c": dict(marks)}, "out": deepcopy(out), "outmarks": {len(out) - 1: "new"} if hit else {},
                      "count": {"rows read": i + 1, "rows returned": len(out)}})
        marks = {k: ("match" if v == "match" else "skip") for k, v in marks.items()}
    steps.append({"say": T(lang, f"Done. PostgreSQL read all {len(rows)} rows to return {len(out)}. With 1,000 customers it reads 1,000 rows. With 10 million, it reads 10 million.",
                           f"Bitti. PostgreSQL {len(out)} row döndürmek için {len(rows)} row'un hepsini okudu. 1.000 müşteride 1.000 row okur. 10 milyon müşteride 10 milyon row okur."),
                  "marks": {"c": {i: ("match" if r[3] == city else "skip") for i, r in enumerate(rows)}}, "out": out,
                  "count": {"rows read": len(rows), "rows returned": len(out)}})
    return {"tables": [_table("c", "customers", CUSTOMERS, key=[0])],
            "out": {"name": T(lang, "result", "sonuç"), "cols": ["customer_id", "name", "city"]}, "steps": steps}


# ---------------------------------------------------------------- 2. Seq Scan and Index Scan
def seq_vs_index(lang):
    rows = CUSTOMERS["rows"]
    target = "C00005"
    idx_rows = [[r[0], T(lang, f"row {i + 1}", f"row {i + 1}")] for i, r in enumerate(rows)]   # already sorted by id
    steps = [{"say": T(lang, "Left: the table, in the order that the rows arrived. Right: the primary key index customers_pkey. The index keeps every customer_id in sorted order, and each entry points to a row of the table. We look for C00005.",
                       "Solda: table, row'ların geldiği sırada. Sağda: primary key index'i customers_pkey. Index her customer_id'yi sıralı tutar ve her entry table'daki bir row'u gösterir. C00005'i arıyoruz."),
              "marks": {}, "count": {"index entries read": 0, "table rows read": 0}}]
    lo, hi, reads = 0, len(idx_rows) - 1, 0
    seen = {}
    while lo <= hi:
        mid = (lo + hi) // 2
        reads += 1
        key = idx_rows[mid][0]
        seen = {**{k: "skip" for k in seen}, mid: "read"}
        if key == target:
            seen[mid] = "match"
            steps.append({"say": T(lang, f"Look at the middle of the remaining range: {key}. This is the key we want. The entry says: {idx_rows[mid][1]}.",
                                   f"Kalan aralığın ortasına bak: {key}. Aradığımız key bu. Entry diyor ki: {idx_rows[mid][1]}."),
                          "marks": {"i": dict(seen)}, "count": {"index entries read": reads, "table rows read": 0}})
            break
        go_right = key < target
        steps.append({"say": T(lang, f"Look at the middle of the remaining range: {key}. {target} is {'greater' if go_right else 'smaller'}, so the search continues only in the {'lower' if go_right else 'upper'} part of the list. Half of the list is now out.",
                               f"Kalan aralığın ortasına bak: {key}. {target} {'daha büyük' if go_right else 'daha küçük'}, bu yüzden arama sadece listenin {'alt' if go_right else 'üst'} kısmında devam eder. Listenin yarısı artık dışarıda."),
                      "marks": {"i": dict(seen)}, "count": {"index entries read": reads, "table rows read": 0}})
        lo, hi = (mid + 1, hi) if go_right else (lo, mid - 1)
    pos = next(i for i, r in enumerate(rows) if r[0] == target)
    steps.append({"say": T(lang, f"Follow the pointer to {idx_rows[pos][1]} of the table and read only that row. Total work: {reads} index entries and 1 table row. A real B-tree does the same with nodes of hundreds of keys, so even 10 million keys need only 3 or 4 node reads.",
                           f"Pointer'ı takip et ({idx_rows[pos][1]}) ve table'da sadece o row'u oku. Toplam iş: {reads} index entry ve 1 table row. Gerçek bir B-tree aynı işi yüzlerce key taşıyan node'larla yapar, bu yüzden 10 milyon key için bile sadece 3-4 node okuması gerekir."),
                  "marks": {"i": {**seen}, "c": {pos: "match"}}, "count": {"index entries read": reads, "table rows read": 1}})
    return {"tables": [_table("c", "customers", CUSTOMERS, key=[0]),
                       {"id": "i", "name": "customers_pkey (index)", "cols": ["customer_id", T(lang, "points to", "gösterdiği yer")], "rows": idx_rows,
                        "key": [0], "ref": []}],
            "out": None, "steps": steps}


# ---------------------------------------------------------------- 3. JOIN: one order from four tables
def join_order(lang):
    oid = "O000001"
    o_i = next(i for i, r in enumerate(ORDERS["rows"]) if r[0] == oid)
    order = ORDERS["rows"][o_i]
    c_i = next(i for i, r in enumerate(CUSTOMERS["rows"]) if r[0] == order[1])
    cust = CUSTOMERS["rows"][c_i]
    out, steps = [], []
    base = {"o": {o_i: "match"}}
    steps.append({"say": T(lang, f"Step 1. WHERE o.order_id = '{oid}'. PostgreSQL finds the order row with the primary key index of orders. The row says customer_id = {order[1]}.",
                           f"Adım 1. WHERE o.order_id = '{oid}'. PostgreSQL sipariş row'unu orders'ın primary key index'i ile bulur. Row diyor ki customer_id = {order[1]}."),
                  "marks": deepcopy(base), "out": [], "count": {"rows in result": 0}})
    base["c"] = {c_i: "match"}
    steps.append({"say": T(lang, f"Step 2. JOIN customers c ON c.customer_id = o.customer_id. PostgreSQL takes the value {order[1]} from the order row and finds the customer row that owns this identifier: {cust[1]}.",
                           f"Adım 2. JOIN customers c ON c.customer_id = o.customer_id. PostgreSQL sipariş row'undan {order[1]} değerini alır ve bu identifier'ın sahibi olan müşteri row'unu bulur: {cust[1]}."),
                  "marks": deepcopy(base), "out": [], "count": {"rows in result": 0}})
    lines = [(i, r) for i, r in enumerate(ITEMS["rows"]) if r[0] == oid]
    base["oi"] = {i: "match" for i, _ in lines}
    steps.append({"say": T(lang, f"Step 3. JOIN order_items oi ON oi.order_id = o.order_id. Every order line that carries {oid} matches. There are {len(lines)} of them, so from now on the result has {len(lines)} rows.",
                           f"Adım 3. JOIN order_items oi ON oi.order_id = o.order_id. {oid} taşıyan her order line eşleşir. {len(lines)} tane var, bu yüzden bundan sonra sonucun {len(lines)} row'u olacak."),
                  "marks": deepcopy(base), "out": [], "count": {"rows in result": 0}})
    for n, (i, line) in enumerate(lines, start=1):
        p_i = next(k for k, r in enumerate(PRODUCTS["rows"]) if r[0] == line[1])
        prod = PRODUCTS["rows"][p_i]
        out.append([oid, order[2], cust[1], prod[1], line[2], money(line[3]), money(line[2] * line[3])])
        marks = deepcopy(base)
        marks["oi"] = {**{k: "done" for k, _ in lines}, i: "read"}
        marks["p"] = {p_i: "match"}
        steps.append({"say": T(lang, f"Step 4.{n}. JOIN products p ON p.product_id = oi.product_id. The line has product_id = {line[1]}. PostgreSQL finds the product row that owns this identifier ({prod[1]}) and builds one result row: {line[2]} × {money(line[3])} = {money(line[2] * line[3])}.",
                               f"Adım 4.{n}. JOIN products p ON p.product_id = oi.product_id. Line'da product_id = {line[1]} var. PostgreSQL bu identifier'ın sahibi olan ürün row'unu ({prod[1]}) bulur ve bir sonuç row'u kurar: {line[2]} × {money(line[3])} = {money(line[2] * line[3])}."),
                      "marks": marks, "out": deepcopy(out), "outmarks": {len(out) - 1: "new"}, "count": {"rows in result": len(out)}})
    steps.append({"say": T(lang, f"Done. {len(out)} result rows. The order date and the customer name repeat in each row, because each row is one order line together with its order and its customer. The tables themselves still keep each fact only once.",
                           f"Bitti. {len(out)} sonuç row'u. Sipariş tarihi ve müşteri adı her row'da tekrar eder, çünkü her row bir order line'ı, onun siparişi ve müşterisiyle birlikte gösterir. Table'ların kendisi her bilgiyi hâlâ sadece bir kez tutar."),
                  "marks": {**base, "oi": {i: "match" for i, _ in lines}}, "out": out, "count": {"rows in result": len(out)}})
    return {"tables": [_table("o", "orders", ORDERS, key=[0], ref=[1]), _table("c", "customers", CUSTOMERS, key=[0]),
                       _table("oi", "order_items", ITEMS, key=[0, 1], ref=[0, 1]), _table("p", "products", PRODUCTS, key=[0])],
            "out": {"name": T(lang, "result", "sonuç"), "cols": ["order_id", "order_date", "customer", "product", "qty", "unit_price", "line_total"]},
            "steps": steps}


# ---------------------------------------------------------------- 4. GROUP BY: buckets per category
def group_by_category(lang):
    status = {r[0]: r[3] for r in ORDERS["rows"]}
    cat = {r[0]: r[2] for r in PRODUCTS["rows"]}
    buckets = {}
    steps = [{"say": T(lang, "We want the revenue of each category. PostgreSQL reads the order lines one by one. For each line it checks the order status (WHERE), looks up the category of the product (JOIN), and then puts the line into the envelope of that category (GROUP BY).",
                       "Her kategorinin gelirini istiyoruz. PostgreSQL order line'ları tek tek okur. Her line için siparişin durumuna bakar (WHERE), ürünün kategorisini bulur (JOIN) ve line'ı o kategorinin zarfına koyar (GROUP BY)."),
              "marks": {}, "out": [], "count": {"lines read": 0, "lines in envelopes": 0}}]
    used = 0
    done = {}
    for i, (oid, pid, qty, price) in enumerate(ITEMS["rows"]):
        o_i = next(k for k, r in enumerate(ORDERS["rows"]) if r[0] == oid)
        p_i = next(k for k, r in enumerate(PRODUCTS["rows"]) if r[0] == pid)
        cur = {**done, i: "read"}
        if status[oid] == "cancelled":
            done[i] = "skip"
            say = T(lang, f"Line {i + 1}: {pid} × {qty} of order {oid}. The order status is 'cancelled', so WHERE o.status <> 'cancelled' is false. The line does not go into any envelope.",
                    f"Line {i + 1}: {oid} siparişinden {pid} × {qty}. Siparişin durumu 'cancelled', bu yüzden WHERE o.status <> 'cancelled' yanlış. Line hiçbir zarfa girmez.")
            marks = {"oi": cur, "o": {o_i: "bad"}}
        else:
            done[i] = "done"
            used += 1
            c = cat[pid]
            b = buckets.setdefault(c, {"orders": set(), "pieces": 0, "revenue": 0.0})
            b["orders"].add(oid)
            b["pieces"] += qty
            b["revenue"] += qty * price
            say = T(lang, f"Line {i + 1}: {pid} × {qty} at {money(price)}. Order {oid} is '{status[oid]}', so the line stays. The product is in category '{c}'. The line goes into the '{c}' envelope: +{qty} pieces, +{money(qty * price)} revenue.",
                    f"Line {i + 1}: {pid} × {qty}, birim fiyat {money(price)}. {oid} siparişinin durumu '{status[oid]}', bu yüzden line kalır. Ürünün kategorisi '{c}'. Line '{c}' zarfına girer: +{qty} adet, +{money(qty * price)} gelir.")
            marks = {"oi": cur, "o": {o_i: "match"}, "p": {p_i: "match"}}
        out = [[c, len(b["orders"]), b["pieces"], money(b["revenue"])] for c, b in buckets.items()]
        hl = {k: "new" for k, row in enumerate(out) if status[oid] != "cancelled" and row[0] == cat[pid]}
        steps.append({"say": say, "marks": marks, "out": out, "outmarks": hl, "count": {"lines read": i + 1, "lines in envelopes": used}})
    final = sorted(([c, len(b["orders"]), b["pieces"], money(b["revenue"])] for c, b in buckets.items()),
                   key=lambda r: -float(r[3].replace(",", "")))
    steps.append({"say": T(lang, "ORDER BY revenue DESC. All lines are in envelopes. Each envelope becomes one result row: count(DISTINCT order_id), sum(qty) and sum(qty × unit_price). Then PostgreSQL sorts the result rows by revenue, the largest first.",
                           "ORDER BY revenue DESC. Bütün line'lar zarflarda. Her zarf bir sonuç row'u olur: count(DISTINCT order_id), sum(qty) ve sum(qty × unit_price). Sonra PostgreSQL sonuç row'larını gelire göre, en büyük önce olacak şekilde sıralar."),
                  "marks": {"oi": done}, "out": final, "outmarks": {0: "match"}, "count": {"lines read": len(ITEMS["rows"]), "lines in envelopes": used}})
    return {"tables": [_table("oi", "order_items", ITEMS, key=[0, 1], ref=[0, 1]), _table("o", "orders", ORDERS, key=[0]),
                       _table("p", "products", PRODUCTS, key=[0])],
            "out": {"name": T(lang, "envelopes (groups)", "zarflar (gruplar)"), "cols": ["category", "orders", "pieces", "revenue"]}, "steps": steps}


# ---------------------------------------------------------------- 5. Constraints: three bad writes
def constraints(lang):
    steps = [{"say": T(lang, "Three programs try to write bad data. For each write, PostgreSQL checks the rules of the schema before it changes anything.",
                       "Üç program kötü veri yazmaya çalışıyor. PostgreSQL her yazmada, hiçbir şeyi değiştirmeden önce schema'nın kurallarını kontrol eder."),
              "marks": {}, "out": [], "count": {"writes refused": 0}}]
    log = []
    tries = [
        ("INSERT INTO customers VALUES ('C00003', 'Ece Arslan', ...)", "c", next(i for i, r in enumerate(CUSTOMERS["rows"]) if r[0] == "C00003"),
         T(lang, "PRIMARY KEY: the identifier C00003 already belongs to Elif Kaya. Two rows cannot own the same identifier.",
           "PRIMARY KEY: C00003 identifier'ı zaten Elif Kaya'ya ait. İki row aynı identifier'ın sahibi olamaz."),
         'ERROR: duplicate key value violates unique constraint "customers_pkey"'),
        ("INSERT INTO order_items VALUES ('O000001', 'P9999', 1, 10.00)", "p", None,
         T(lang, "FOREIGN KEY: the new line says product_id = P9999. PostgreSQL looks for the product that owns P9999 and finds none.",
           "FOREIGN KEY: yeni line product_id = P9999 diyor. PostgreSQL P9999'un sahibi olan ürünü arar ve bulamaz."),
         'ERROR: insert or update on table "order_items" violates foreign key constraint "order_items_product_id_fkey"'),
        ("UPDATE products SET stock = stock - 500 WHERE product_id = 'P0095'", "p", next(i for i, r in enumerate(PRODUCTS["rows"]) if r[0] == "P0095"),
         T(lang, "CHECK (stock >= 0): P0095 has stock 76. 76 - 500 = -424. A negative stock breaks the rule.",
           "CHECK (stock >= 0): P0095'in stoğu 76. 76 - 500 = -424. Negatif stok kuralı bozar."),
         'ERROR: new row for relation "products" violates check constraint "products_stock_check"'),
    ]
    for n, (stmt, tid, row, why, err) in enumerate(tries, start=1):
        log.append([stmt, err])
        marks = {tid: {row: "bad"}} if row is not None else {"p": {k: "read" for k in range(len(PRODUCTS["rows"]))}}
        steps.append({"say": f"{n}. {why} " + T(lang, "PostgreSQL refuses the statement. The tables do not change.", "PostgreSQL statement'ı reddeder. Table'lar değişmez."),
                      "marks": marks, "out": deepcopy(log), "outmarks": {len(log) - 1: "bad"}, "count": {"writes refused": n}})
    return {"tables": [_table("c", "customers", CUSTOMERS, key=[0]), _table("p", "products", PRODUCTS, key=[0])],
            "out": {"name": T(lang, "statements and answers", "statement'lar ve cevaplar"), "cols": ["statement", T(lang, "answer of PostgreSQL", "PostgreSQL'in cevabı")]},
            "steps": steps}


# ---------------------------------------------------------------- 6. Transaction: payment fails, ROLLBACK
def tx_rollback(lang):
    prods = deepcopy(PRODUCTS["rows"])
    orders = deepcopy(ORDERS["rows"])
    cart = [("P0001", 2), ("P0142", 1)]
    pi = {r[0]: i for i, r in enumerate(prods)}
    log, steps = [], []

    def snap(say, marks, extra=None):
        steps.append({"say": say, "marks": marks, "rows": {"p": deepcopy(prods), "o": deepcopy(orders)}, "out": deepcopy(log),
                      "outmarks": {len(log) - 1: extra or "new"} if log else {}, "count": {}})
    snap(T(lang, "Can Demir's cart has 2 × P0001 and 1 × P0142. Checkout starts. Look at the stock of the two products.",
           "Can Demir'in sepetinde 2 × P0001 ve 1 × P0142 var. Checkout başlıyor. İki ürünün stoğuna bak."),
         {"p": {pi["P0001"]: "read", pi["P0142"]: "read"}})
    log.append(["BEGIN;", T(lang, "transaction starts", "transaction başlar")])
    snap(T(lang, "BEGIN. From now on, PostgreSQL keeps every change of this session as one unit. Other sessions do not see these changes yet.",
           "BEGIN. Bundan sonra PostgreSQL bu session'ın her değişikliğini tek bir birim olarak tutar. Diğer session'lar bu değişiklikleri henüz görmez."), {})
    locked = {}
    for pid, q in cart:
        before = prods[pi[pid]][4]
        prods[pi[pid]][4] = before - q
        locked[pi[pid]] = "lock"
        log.append([f"UPDATE products SET stock = stock - {q} WHERE product_id = '{pid}' AND stock >= {q};",
                    T(lang, f"{before} becomes {before - q}", f"önce {before}, şimdi {before - q}")])
        snap(T(lang, f"The stock of {pid} goes from {before} to {before - q}. PostgreSQL also takes a row lock on this row until the transaction ends.",
               f"{pid} stoğu: önce {before}, şimdi {before - q}. PostgreSQL ayrıca transaction bitene kadar bu row üzerinde bir row lock alır."),
             {"p": dict(locked)})
    log.append([T(lang, "-- the payment service answers: card declined", "-- ödeme servisi cevap verir: kart reddedildi"), T(lang, "error in the app", "uygulamada hata")])
    snap(T(lang, "Now the payment fails. The stock is already lower, but no order exists. If the program stopped here, the shop would lose 3 pieces of stock for an order that does not exist.",
           "Şimdi ödeme başarısız oluyor. Stok zaten düştü ama hiçbir sipariş yok. Program burada dursaydı, mağaza var olmayan bir sipariş için 3 adet stok kaybederdi."),
         {"p": {pi["P0001"]: "lock", pi["P0142"]: "lock"}}, "bad")
    for pid, q in cart:
        prods[pi[pid]][4] += q
    log.append(["ROLLBACK;", T(lang, "every change since BEGIN is undone", "BEGIN'den beri her değişiklik geri alınır")])
    snap(T(lang, "ROLLBACK. PostgreSQL undoes every change since BEGIN: the two stock values are back at 127 and 84, and the row locks are gone. No order row was written. This is atomicity: all or nothing.",
           "ROLLBACK. PostgreSQL BEGIN'den beri yapılan her değişikliği geri alır: iki stok değeri 127 ve 84'e döner, row lock'lar kalkar. Hiçbir order row'u yazılmadı. Bu atomicity'dir: ya hepsi ya hiçbiri."),
         {"p": {pi["P0001"]: "match", pi["P0142"]: "match"}}, "match")
    return {"tables": [_table("p", "products", PRODUCTS, key=[0]), _table("o", "orders", ORDERS, key=[0], ref=[1])],
            "out": {"name": T(lang, "the session (statements in order)", "session (sırayla statement'lar)"), "cols": ["statement", T(lang, "effect", "etkisi")]},
            "steps": steps}


# ---------------------------------------------------------------- 7. Lost update and the row lock
def last_piece(lang, safe):
    prods = deepcopy(PRODUCTS["rows"])
    pid = "P0095"
    pi = next(i for i, r in enumerate(prods) if r[0] == pid)
    prods[pi][4] = 1
    log, steps, sold = [], [], 0

    def snap(say, cls, extra=None):
        steps.append({"say": say, "marks": {"p": {pi: cls}}, "rows": {"p": deepcopy(prods)}, "out": deepcopy(log),
                      "outmarks": {len(log) - 1: extra or "new"} if log else {}, "count": {T(lang, "pieces sold", "satılan adet"): sold}})
    snap(T(lang, f"Only 1 piece of {pid} is left. Ayşe and Mert press 'Place the order' in the same second. Each request runs in its own session.",
           f"{pid}'den sadece 1 adet kaldı. Ayşe ve Mert aynı saniyede 'Place the order'a basıyor. Her istek kendi session'ında çalışır."), "read")
    if not safe:
        log.append(["t1", T(lang, "SELECT stock returns 1", "SELECT stock, 1 döndürür"), ""])
        snap(T(lang, "t1: Ayşe's program reads the stock: 1. One piece is enough, so it plans to sell.",
               "t1: Ayşe'nin programı stoğu okur: 1. Bir adet yeterli, bu yüzden satmayı planlar."), "read")
        log.append(["t2", "", T(lang, "SELECT stock returns 1", "SELECT stock, 1 döndürür")])
        snap(T(lang, "t2: Mert's program reads the stock before Ayşe's program writes. It also sees 1.",
               "t2: Mert'in programı, Ayşe'nin programı yazmadan önce stoğu okur. O da 1 görür."), "read")
        prods[pi][4] = 0
        sold += 1
        log.append(["t3", "UPDATE products SET stock = 0", ""])
        snap(T(lang, "t3: Ayşe's program writes the value that it calculated: 1 - 1 = 0. Ayşe gets the piece.",
               "t3: Ayşe'nin programı hesapladığı değeri yazar: 1 - 1 = 0. Parçayı Ayşe alır."), "done")
        sold += 1
        log.append(["t4", "", "UPDATE products SET stock = 0"])
        snap(T(lang, "t4: Mert's program writes its value, also 1 - 1 = 0. It does not know that the value changed. The shop sold 2 pieces but had 1. The first update is lost.",
               "t4: Mert'in programı kendi değerini yazar, o da 1 - 1 = 0. Değerin değiştiğini bilmiyor. Mağaza 2 adet sattı ama 1 adedi vardı. İlk update kayboldu."), "bad", "bad")
    else:
        prods[pi][4] = 0
        sold += 1
        log.append(["t1", T(lang, "UPDATE ... SET stock = stock - 1 WHERE product_id = 'P0095' AND stock >= 1 changes 1 row", "UPDATE ... SET stock = stock - 1 WHERE product_id = 'P0095' AND stock >= 1, 1 row değiştirir"), ""])
        snap(T(lang, "t1: Ayşe's session runs the conditional UPDATE. The test (stock >= 1) and the change happen in one statement. PostgreSQL locks the row until Ayşe's transaction ends.",
               "t1: Ayşe'nin session'ı koşullu UPDATE'i çalıştırır. Test (stock >= 1) ve değişiklik tek bir statement'ta olur. PostgreSQL row'u Ayşe'nin transaction'ı bitene kadar kilitler."), "lock")
        log.append(["t2", "", T(lang, "UPDATE ... (the same statement) waits for the row lock", "UPDATE ... (aynı statement) row lock'u bekler")])
        snap(T(lang, "t2: Mert's session runs the same UPDATE on the same row. The row is locked, so this UPDATE waits. It does not read the old value 1.",
               "t2: Mert'in session'ı aynı row üzerinde aynı UPDATE'i çalıştırır. Row kilitli, bu yüzden bu UPDATE bekler. Eski değer olan 1'i okumaz."), "lock")
        log.append(["t3", "COMMIT", ""])
        snap(T(lang, "t3: Ayşe's transaction commits. The stock is now 0, and the lock goes away.",
               "t3: Ayşe'nin transaction'ı commit edilir. Stok artık 0 ve lock kalkar."), "done")
        log.append(["t4", "", T(lang, "UPDATE ... changes 0 rows, because stock >= 1 is false", "UPDATE ... 0 row değiştirir, çünkü stock >= 1 yanlış")])
        snap(T(lang, "t4: Mert's UPDATE continues. It tests the current value: 0 >= 1 is false, so it changes 0 rows. The app sees '0 rows' and tells Mert that the product is sold out. The shop sold exactly 1 piece.",
               "t4: Mert'in UPDATE'i devam eder. Güncel değeri test eder: 0 >= 1 yanlış, bu yüzden 0 row değiştirir. Uygulama '0 row' görür ve Mert'e ürünün tükendiğini söyler. Mağaza tam olarak 1 adet sattı."), "match", "match")
    return {"tables": [_table("p", "products", PRODUCTS, key=[0])],
            "out": {"name": T(lang, "two sessions in time order", "zaman sırasıyla iki session"), "cols": [T(lang, "time", "zaman"), "Ayşe", "Mert"]},
            "steps": steps}


# ---------------------------------------------------------------- 8. Aurora: one write, three Availability Zones
def aurora_write(lang):
    copies = {"a": [], "b": [], "c": []}
    cols = ["order_id", "customer_id", "total"]
    row = ["W1793...", "C00006", "9,441.33"]
    steps = []

    def snap(say, marks, out):
        steps.append({"say": say, "marks": marks, "rows": {k: deepcopy(v) for k, v in copies.items()}, "out": out, "count": {}})
    snap(T(lang, "Aurora cluster: one writer instance, one reader instance, and one cluster volume with a copy of the data in each of three Availability Zones (AZ). The writer gets INSERT INTO orders ... from the checkout.",
           "Aurora cluster: bir writer instance, bir reader instance ve üç Availability Zone'un (AZ) her birinde verinin bir kopyası olan tek bir cluster volume. Writer, checkout'tan INSERT INTO orders ... alır."),
         {}, [])
    for az in "abc":
        copies[az] = [row]
    snap(T(lang, "The writer sends the change to the storage layer. The storage writes it to the copies in all three AZs. The writer does not copy files to the reader.",
           "Writer değişikliği storage katmanına gönderir. Storage onu üç AZ'deki kopyaların hepsine yazar. Writer dosyaları reader'a kopyalamaz."),
         {"a": {0: "new"}, "b": {0: "new"}, "c": {0: "new"}}, [])
    snap(T(lang, "COMMIT returns to the app. A report on the reader instance now reads the new order from the same cluster volume.",
           "COMMIT uygulamaya döner. Reader instance üzerindeki bir rapor artık yeni siparişi aynı cluster volume'dan okur."),
         {"b": {0: "match"}}, [[T(lang, "reader instance", "reader instance"), "SELECT ... FROM orders WHERE order_id = 'W1793...'", "1 row"]])
    copies["a"] = []
    snap(T(lang, "Assume that AZ a fails, with its copy. The data still exists in AZ b and AZ c, so the cluster volume continues to serve reads and writes. If the writer instance was in the failed AZ, Aurora fails over to a replica.",
           "AZ a'nın kopyasıyla birlikte çöktüğünü varsay. Veri AZ b ve AZ c'de hâlâ var, bu yüzden cluster volume okuma ve yazmalara cevap vermeye devam eder. Writer instance çöken AZ'deyse, Aurora bir replica'ya failover yapar."),
         {"b": {0: "match"}, "c": {0: "match"}}, [])
    return {"tables": [{"id": az, "name": T(lang, f"cluster volume copy in AZ {az}", f"AZ {az}'deki cluster volume kopyası"), "cols": cols, "rows": [], "key": [0], "ref": []}
                       for az in "abc"],
            "out": {"name": T(lang, "reads", "okumalar"), "cols": ["instance", "statement", T(lang, "result", "sonuç")]}, "steps": steps}


# ---------------------------------------------------------------- 0a. Legacy elimination decisions (2/1/0 scale). Only the old English page
# (templates/e2e/aurora.html) still uses decide_checkout, decide_dashboard and decide_sessions. The Turkish page uses the five
# scorecard simulations built from the M2 cards (e2e_usecases.AURORA_USECASES) through usecase_scorecard: see _aurora().
CANDIDATES = ["Aurora PostgreSQL", "DynamoDB", "Redshift", "ElastiCache (Valkey)", "OpenSearch"]
REQS = {
    "acid": (("Several rows change as one all-or-nothing unit, many times each second (OLTP)",
              "Birçok row, saniyede birçok kez, ya-hep-ya-hiç tek bir birim olarak değişir (OLTP)"),
             {"Aurora PostgreSQL": (1, "BEGIN ... COMMIT, row locks", "BEGIN ... COMMIT, row lock'lar"),
              "DynamoDB": (1, "TransactWriteItems", "TransactWriteItems"),
              "Redshift": (0, "built for analytic scans, not many small writes", "küçük ve çok sayıda yazma için değil, analitik tarama için yapıldı"),
              "ElastiCache (Valkey)": (0, "MULTI has no rollback, data is in memory", "MULTI'de rollback yok, veri bellekte"),
              "OpenSearch": (0, "no multi-document transactions", "çok-dokümanlı transaction yok")}),
    "rules": (("The database itself refuses bad data: foreign keys, CHECK, NOT NULL",
               "Database kötü veriyi kendisi reddeder: foreign key, CHECK, NOT NULL"),
              {"Aurora PostgreSQL": (1, "constraints are enforced on every write", "constraint'ler her yazmada uygulanır"),
               "DynamoDB": (0, "no foreign keys, only conditions on one item", "foreign key yok, sadece tek item üzerinde koşul"),
               "Redshift": (0, "primary and foreign keys are informational only", "primary ve foreign key'ler sadece bilgi amaçlı"),
               "ElastiCache (Valkey)": (0, "no schema", "schema yok"),
               "OpenSearch": (0, "no relations between documents", "dokümanlar arasında ilişki yok")}),
    "adhoc": (("New questions with JOIN and filters on any column, without a redesign",
               "Yeniden tasarım yapmadan, JOIN ve her column üzerinde filtreyle yeni sorular"),
              {"Aurora PostgreSQL": (1, "SQL, indexes on any column", "SQL, her column'a index"),
               "DynamoDB": (0, "each question needs a key design", "her soru bir key tasarımı ister"),
               "Redshift": (1, "SQL", "SQL"),
               "ElastiCache (Valkey)": (0, "access by key only", "sadece key ile erişim"),
               "OpenSearch": (0, "no JOIN between indexes", "index'ler arasında JOIN yok")}),
    "scan": (("Scan billions of rows of history and read only a few columns",
              "Milyarlarca row'luk geçmişi tarayıp sadece birkaç column okumak"),
             {"Aurora PostgreSQL": (0, "row storage reads full rows, and the scan competes with checkout", "row storage tam row'ları okur ve tarama checkout ile yarışır"),
              "DynamoDB": (0, "a Scan reads and bills every item", "Scan her item'ı okur ve faturalar"),
              "Redshift": (1, "columnar storage, parallel scan", "columnar storage, paralel tarama"),
              "ElastiCache (Valkey)": (0, "data must fit in memory", "veri belleğe sığmalı"),
              "OpenSearch": (0, "aggregations, but no SQL joins over history", "aggregation var ama geçmiş üzerinde SQL join yok")}),
    "sql": (("Analysts write SQL with JOIN and GROUP BY",
             "Analistler JOIN ve GROUP BY ile SQL yazar"),
            {"Aurora PostgreSQL": (1, "SQL", "SQL"), "DynamoDB": (0, "no SQL joins", "SQL join yok"), "Redshift": (1, "SQL", "SQL"),
             "ElastiCache (Valkey)": (0, "no SQL", "SQL yok"), "OpenSearch": (0, "no JOIN", "JOIN yok")}),
    "submilli": (("Each read must take less than one millisecond, at very high read rates",
                  "Her okuma, çok yüksek okuma hızlarında bir milisaniyeden kısa sürmeli"),
                 {"Aurora PostgreSQL": (0, "disk-based engine, milliseconds", "disk tabanlı engine, milisaniyeler"),
                  "DynamoDB": (0, "single-digit milliseconds", "tek haneli milisaniyeler"),
                  "Redshift": (0, "analytic queries, not point reads", "analitik query'ler, tekil okuma değil"),
                  "ElastiCache (Valkey)": (1, "all data in memory", "bütün veri bellekte"),
                  "OpenSearch": (0, "search, not point reads", "arama, tekil okuma değil")}),
    "ttl": (("Each entry deletes itself after a time (TTL)",
             "Her kayıt bir süre sonra kendini siler (TTL)"),
            {"Aurora PostgreSQL": (0, "no row TTL, needs a cleanup job", "row TTL yok, temizlik işi gerekir"),
             "DynamoDB": (1, "TTL attribute", "TTL attribute"),
             "Redshift": (0, "no TTL", "TTL yok"),
             "ElastiCache (Valkey)": (1, "EXPIRE on each key", "her key'de EXPIRE"),
             "OpenSearch": (0, "no per-document TTL", "doküman başına TTL yok")}),
}
SCENARIOS = {
    "checkout": (("Checkout: lower the stock, write the order and its lines, take the payment", "Checkout: stoğu düşür, siparişi ve line'larını yaz, ödemeyi al"),
                 ["acid", "rules", "adhoc"]),
    "dashboard": (("Five years of sales, grouped by month, city and category, for analysts", "Analistler için ay, şehir ve kategoriye göre gruplanmış beş yıllık satışlar"),
                  ["scan", "sql"]),
    "sessions": (("Sessions of 200,000 visitors, read on each page, gone after 30 minutes", "200.000 ziyaretçinin session'ları; her sayfada okunur, 30 dakika sonra gider"),
                 ["submilli", "ttl"]),
}


def decide(lang, scenario):
    title, reqs = SCENARIOS[scenario]
    cols = [T(lang, "candidate", "aday")] + [f"R{i + 1}" for i in range(len(reqs))] + [T(lang, "status", "durum")]
    rows = [[c] + ["?"] * len(reqs) + [T(lang, "in the race", "yarışta")] for c in CANDIDATES]
    req_rows = [[f"R{i + 1}", T(lang, *REQS[r][0])] for i, r in enumerate(reqs)]
    alive = set(CANDIDATES)
    steps = [{"say": T(lang, f"Workload: {title[0]}. Five candidate engines start in the race. Each requirement (R1, R2, ...) removes the candidates that cannot meet it.",
                       f"İş yükü: {title[1]}. Beş aday engine yarışa başlar. Her gereksinim (R1, R2, ...), onu karşılayamayan adayları yarıştan çıkarır."),
              "marks": {}, "rows": {"cand": deepcopy(rows)}, "count": {T(lang, "candidates left", "kalan aday"): len(alive)}}]
    for i, r in enumerate(reqs):
        out = []
        for k, c in enumerate(CANDIDATES):
            ok, en, tr = REQS[r][1][c]
            rows[k][i + 1] = (T(lang, "yes", "evet") if ok else T(lang, "no", "hayır")) + ": " + T(lang, en, tr)
            if not ok and c in alive:
                alive.discard(c)
                rows[k][-1] = T(lang, f"out at R{i + 1}", f"R{i + 1}'de elendi")
                out.append(c)
        marks = {k: ("match" if c in alive else ("bad" if c in out else "skip")) for k, c in enumerate(CANDIDATES)}
        steps.append({"say": T(lang, f"R{i + 1}: {REQS[r][0][0]}. " + (f"Out: {', '.join(out)}." if out else "Nobody drops out here."),
                               f"R{i + 1}: {REQS[r][0][1]}. " + (f"Elenen: {', '.join(out)}." if out else "Burada kimse elenmez.")),
                      "marks": {"cand": marks, "req": {i: "read"}}, "rows": {"cand": deepcopy(rows)},
                      "count": {T(lang, "candidates left", "kalan aday"): len(alive)}})
    win = [c for c in CANDIDATES if c in alive]
    for k, c in enumerate(CANDIDATES):
        if c in alive:
            rows[k][-1] = T(lang, "chosen", "seçildi")
    steps.append({"say": T(lang, f"Result: {' and '.join(win)}. The decision comes from the requirements, not from habit. Write the requirements down, and you can explain the choice to anybody.",
                           f"Sonuç: {' ve '.join(win)}. Karar alışkanlıktan değil, gereksinimlerden gelir. Gereksinimleri yazarsan seçimi herkese açıklayabilirsin."),
                  "marks": {"cand": {k: ("new" if c in alive else "skip") for k, c in enumerate(CANDIDATES)}}, "rows": {"cand": deepcopy(rows)},
                  "count": {T(lang, "candidates left", "kalan aday"): len(alive)}})
    return {"tables": [{"id": "req", "name": T(lang, "requirements of the workload", "iş yükünün gereksinimleri"), "cols": ["id", T(lang, "requirement", "gereksinim")],
                        "rows": req_rows, "key": [0], "ref": []},
                       {"id": "cand", "name": T(lang, "candidate engines", "aday engine'ler"), "cols": cols, "rows": [[c] + ["?"] * len(reqs) + [T(lang, "in the race", "yarışta")] for c in CANDIDATES],
                        "key": [0], "ref": []}],
            "out": None, "steps": steps}


# ---------------------------------------------------------------- 0. Architecture decisions: five scorecard simulations built from the M2 cards
# (e2e_usecases.AURORA_USECASES). A score can never differ between a card and its simulation.


COUNT_TR = {"rows read": "okunan row", "rows returned": "dönen row", "index entries read": "okunan index entry",
            "table rows read": "okunan table row", "rows in result": "sonuçtaki row", "lines read": "okunan line",
            "lines in envelopes": "zarflardaki line", "writes refused": "reddedilen yazma"}


def _localize(spec, lang):
    if lang == "tr":
        for st in spec["steps"]:
            st["count"] = {COUNT_TR.get(k, k): v for k, v in st.get("count", {}).items()}
    return spec


def aurora(lang):
    return {k: _localize(v, lang) for k, v in _aurora(lang).items()}


def _aurora(lang):
    return {**{uc["sim"]: usecase_scorecard(lang, uc) for uc in _uc.AURORA_USECASES if uc["sim"]},
            "decide_checkout": decide(lang, "checkout"), "decide_dashboard": decide(lang, "dashboard"), "decide_sessions": decide(lang, "sessions"),   # old English page only
            "where": where_city(lang), "index": seq_vs_index(lang), "join": join_order(lang), "group": group_by_category(lang),
            "constraints": constraints(lang), "tx": tx_rollback(lang), "lost": last_piece(lang, False), "locked": last_piece(lang, True),
            "storage": aurora_write(lang)}


SIMS = {"aurora": aurora}


# ================================================================ Generic helpers for the other Engines (same as simkit.py of the skill)
def decide_generic(lang, workload, requirements, candidates, verdicts):
    """Architecture decision: each requirement removes the candidates that cannot meet it.
    verdicts: {requirement index: {candidate: (1 or 0, reason_en, reason_tr)}}"""
    yes, no = T(lang, "yes", "evet"), T(lang, "no", "hayır")
    left = T(lang, "candidates left", "kalan aday")
    cols = [T(lang, "candidate", "aday")] + [f"R{i + 1}" for i in range(len(requirements))] + [T(lang, "status", "durum")]
    start = [[c] + ["?"] * len(requirements) + [T(lang, "in the race", "yarışta")] for c in candidates]
    rows, alive = deepcopy(start), list(candidates)
    steps = [{"say": T(lang, f"Workload: {workload[0]}. {len(candidates)} candidates start. Each requirement removes the candidates that cannot meet it.",
                       f"İş yükü: {workload[1]}. {len(candidates)} aday başlar. Her gereksinim, onu karşılayamayan adayları eler."),
              "marks": {}, "rows": {"cand": deepcopy(rows)}, "count": {left: len(alive)}}]
    for i, req in enumerate(requirements):
        out = []
        for k, c in enumerate(candidates):
            ok, en, tr = verdicts[i][c]
            rows[k][i + 1] = f"{yes if ok else no}: {T(lang, en, tr)}"
            if not ok and c in alive:
                alive.remove(c)
                out.append(c)
                rows[k][-1] = T(lang, f"out at R{i + 1}", f"R{i + 1}'de elendi")
        marks = {k: ("match" if c in alive else ("bad" if c in out else "skip")) for k, c in enumerate(candidates)}
        steps.append({"say": T(lang, f"R{i + 1}: {req[0]}. " + (f"Out: {', '.join(out)}." if out else "Nobody drops out here."),
                               f"R{i + 1}: {req[1]}. " + (f"Elenen: {', '.join(out)}." if out else "Burada kimse elenmez.")),
                      "marks": {"cand": marks, "req": {i: "read"}}, "rows": {"cand": deepcopy(rows)}, "count": {left: len(alive)}})
    for k, c in enumerate(candidates):
        if c in alive:
            rows[k][-1] = T(lang, "chosen", "seçildi")
    steps.append({"say": T(lang, f"Result: {' and '.join(alive) or 'no candidate'}. The requirements made the decision, so you can explain it to anybody.",
                           f"Sonuç: {' ve '.join(alive) or 'hiçbir aday'}. Kararı gereksinimler verdi, bu yüzden onu herkese açıklayabilirsin."),
                  "marks": {"cand": {k: ("new" if c in alive else "skip") for k, c in enumerate(candidates)}}, "rows": {"cand": deepcopy(rows)},
                  "count": {left: len(alive)}})
    return {"tables": [{"id": "req", "name": T(lang, "requirements of the workload", "iş yükünün gereksinimleri"), "cols": ["id", T(lang, "requirement", "gereksinim")],
                        "rows": [[f"R{i + 1}", T(lang, *r)] for i, r in enumerate(requirements)], "key": [0], "ref": []},
                       {"id": "cand", "name": T(lang, "candidates", "adaylar"), "cols": cols, "rows": start, "key": [0], "ref": []}],
            "out": None, "steps": steps}


def decide_score(lang, d, scale=2):
    """Architecture decision as a scorecard. Each requirement is scored for EVERY candidate: yes = 2, partly = 1, no = 0.
    A "must" requirement with 0 disqualifies the candidate, but the candidate stays in the table until the end.
    d = {"workload": (en, tr), "cands": [...], "reqs": [{"must": bool, "axis": (en, tr), "text": (en, tr), "why": (en, tr),
         "cells": {cand: (score, en, tr)}}], "gap": (en, tr), "pivot": (en, tr) or None}"""
    cands, reqs = d["cands"], d["reqs"]
    if scale == 10:   # 0-10 points per requirement; 0 or 1 on a must requirement disqualifies
        sym = {i: (("✓ " if i >= 8 else "✗ " if i <= 1 else "") + str(i)) for i in range(11)}
        low = lambda x: x <= 1
    else:
        sym = {2: "✓ 2", 1: "~ 1", 0: "✗ 0"}
        low = lambda x: x == 0
    kind = lambda r: T(lang, "must", "zorunlu") if r["must"] else T(lang, "preferred", "tercihli")
    cols = [T(lang, "candidate", "aday")] + [f"R{i + 1}" for i in range(len(reqs))] + [T(lang, "points", "puan"), T(lang, "status", "durum")]
    rows = [[c] + [""] * len(reqs) + [0, T(lang, "in the race", "yarışta")] for c in cands]
    total, disq = {c: 0 for c in cands}, set()

    def marks():
        ok = [c for c in cands if c not in disq]
        best = max((total[c] for c in ok), default=-1)
        return {k: ("bad" if c in disq else ("match" if total[c] == best and best > 0 else "")) for k, c in enumerate(cands)}

    if scale == 10:
        rules = T(lang, "Rules: each requirement is scored for every candidate, from 0 to 10, with the reason for each point that is taken off. "
                        "A candidate with 0 or 1 on a must requirement is disqualified, but we keep scoring it, so you can see the full picture.",
                  "Kurallar: her gereksinim her aday için 0-10 arasında puanlanır ve kırılan her puanın nedeni yazılır. "
                        "Zorunlu bir gereksinimde 0 ya da 1 alan aday diskalifiye olur, ama tam resmi görebilmen için puanlamaya devam ederiz.")
    else:
        rules = T(lang, "Rules: each requirement is checked for every candidate. Yes = 2 points, partly = 1, no = 0. "
                        "A candidate with 0 on a must requirement is disqualified, but we keep checking it, so you can see the full picture.",
                  "Kurallar: her gereksinim her aday için kontrol edilir. Evet = 2 puan, kısmen = 1, hayır = 0. "
                  "Zorunlu bir gereksinimde 0 alan aday diskalifiye olur, ama tam resmi görebilmen için kontrol etmeye devam ederiz.")
    steps = [{"say": T(lang, "Workload. ", "İş yükü. ") + T(lang, *d["workload"]) + "\n" + rules,
              "marks": {}, "rows": {"board": deepcopy(rows)}, "out": [], "count": {T(lang, "requirements checked", "kontrol edilen gereksinim"): f"0 / {len(reqs)}"}}]
    for i, r in enumerate(reqs):
        detail = []
        for k, c in enumerate(cands):
            sc, en, tr = r["cells"][c]
            total[c] += sc
            rows[k][i + 1] = sym[sc]
            rows[k][-2] = total[c]
            if r["must"] and low(sc) and c not in disq:
                disq.add(c)
                rows[k][-1] = T(lang, f"disqualified at R{i + 1}", f"R{i + 1}'de diskalifiye")
            detail.append([c, sym[sc], T(lang, en, tr)])
        say = (f"R{i + 1} · {kind(r)} · {T(lang, *r['axis'])}\n{T(lang, *r['text'])}\n"
               + T(lang, "Why it matters: ", "Neden önemli: ") + T(lang, *r["why"]))
        steps.append({"say": say, "marks": {"board": marks(), "req": {i: "read"}}, "rows": {"board": deepcopy(rows)}, "out": detail,
                      "outmarks": {k: ("bad" if x[1].startswith("✗") else "match" if x[1].startswith("✓") else "") for k, x in enumerate(detail)},
                      "count": {T(lang, "requirements checked", "kontrol edilen gereksinim"): f"{i + 1} / {len(reqs)}",
                                T(lang, "disqualified", "diskalifiye"): len(disq)}})
    ok = sorted([c for c in cands if c not in disq], key=lambda c: -total[c])
    win = ok[0]
    second = [c for c in ok[1:] if total[c] == total[ok[1]]] if len(ok) > 1 else []
    order = sorted(cands, key=lambda c: (c in disq, -total[c]))
    place = {c: 1 + sum(1 for o in ok if total[o] > total[c]) for c in ok}

    def status(c):
        if c in disq:
            return T(lang, "disqualified", "diskalifiye")
        if c == win:
            return T(lang, "winner", "kazanan")
        if c in second:
            return T(lang, "second", "ikinci")
        return T(lang, f"place {place[c]}", f"{place[c]}. sıra")
    for k, c in enumerate(cands):
        rows[k][-1] = status(c)
    ranking = [[c, total[c], status(c)] for c in order]
    res = T(lang, f"Result. The winner is {win} with {total[win]} points.", f"Sonuç. Kazanan {total[win]} puanla {win}.")
    if second:
        res += T(lang, f" Second: {' and '.join(second)} with {total[second[0]]} points.", f" İkinci: {total[second[0]]} puanla {' ve '.join(second)}.")
    res += "\n" + T(lang, *d["gap"])
    if d.get("pivot"):
        res += "\n" + T(lang, "If one condition changed: ", "Bir koşul değişseydi: ") + T(lang, *d["pivot"])
    steps.append({"say": res, "marks": {"board": {k: ("bad" if c in disq else "new" if c == win else "match" if c in second else "") for k, c in enumerate(cands)}},
                  "rows": {"board": deepcopy(rows)}, "out": ranking,
                  "outmarks": {0: "new"}, "count": {T(lang, "requirements checked", "kontrol edilen gereksinim"): f"{len(reqs)} / {len(reqs)}",
                                                     T(lang, "disqualified", "diskalifiye"): len(disq)}})
    return {"kind": "score",
            "tables": [{"id": "req", "name": T(lang, "requirements", "gereksinimler"), "cols": ["id", T(lang, "type", "tür"), T(lang, "what is checked", "ne kontrol edilir")],
                        "rows": [[f"R{i + 1}", kind(r), T(lang, *r["axis"])] for i, r in enumerate(reqs)], "key": [0], "ref": []},
                       {"id": "board", "name": T(lang, "scorecard", "puan tablosu"), "cols": cols, "rows": deepcopy([[c] + [""] * len(reqs) + [0, T(lang, "in the race", "yarışta")] for c in cands]), "key": [0], "ref": []}],
            "out": {"name": T(lang, "this requirement for each candidate (at the end: the ranking)", "bu gereksinim her aday için (sonda: sıralama)"),
                    "cols": [T(lang, "candidate", "aday"), T(lang, "points", "puan"), T(lang, "reason (at the end: place)", "gerekçe (sonda: sıra)")]},
            "steps": steps}


def V(*cells):
    """Verdict row helper: V((1, en, tr), (0, en, tr), ...) in the order of the candidates."""
    return cells


def verdicts(candidates, table):
    return {i: dict(zip(candidates, row)) for i, row in enumerate(table)}


# ================================================================ DynamoDB
CART = {"cols": ["pk", "sk", "name", "qty", "unit_price", "expires_at"],
        "rows": [["CART#7f3a", "ITEM#P0001", "Alpen Kablosuz Kulaklık 1", 2, 3373.84, 1793433600],
                 ["CART#7f3a", "ITEM#P0044", "Kapadokya Bulut Mimarisi 44", 1, 2651.39, 1793433600],
                 ["CART#7f3a", "ITEM#P0142", "Ege Hava Temizleyici 142", 1, 2693.65, 1793433600],
                 ["CART#3c8d", "ITEM#P0179", "Toros Python ile Veri 179", 10, 767.49, 1793437200],
                 ["CART#3c8d", "ITEM#P0001", "Alpen Kablosuz Kulaklık 1", 5, 3373.84, 1793437200],
                 ["CART#a1f2", "ITEM#P0095", "Anadolu Yün Kazak 95", 1, 2721.65, 1793440800],
                 ["CART#a1f2", "ITEM#P0044", "Kapadokya Bulut Mimarisi 44", 2, 2651.39, 1793440800],
                 ["CART#d405", "ITEM#P0142", "Ege Hava Temizleyici 142", 3, 2693.65, 1793444400]]}


def _hash(pk, n=3):
    """A small teaching hash: the sum of the character codes, modulo the number of partitions. DynamoDB uses its own internal hash."""
    return sum(ord(ch) for ch in pk) % n


def ddb_hash(lang):
    rows = CART["rows"]
    parts = [[] for _ in range(3)]
    steps = [{"say": T(lang, "The table has three partitions. For each new item, DynamoDB calculates a hash of the partition key (pk). The hash selects the partition. This simulation uses a simple teaching hash: the sum of the character codes modulo 3.",
                       "Table'ın üç partition'ı var. Her yeni item için DynamoDB, partition key'in (pk) hash'ini hesaplar. Hash, partition'ı seçer. Bu simülasyon basit bir öğretim hash'i kullanır: karakter kodlarının toplamının 3'e göre modu."),
              "marks": {}, "rows": {f"p{k}": [] for k in range(3)}, "count": {"partitions touched": 0}}]
    for i, r in enumerate(rows):
        h = _hash(r[0])
        parts[h].append([r[0], r[1], r[3]])
        steps.append({"say": T(lang, f"Item {i + 1}: pk = {r[0]}. hash({r[0]}) mod 3 = {h}, so the item goes into partition {h}. Items with the same pk always land in the same partition, sorted by sk.",
                               f"Item {i + 1}: pk = {r[0]}. hash({r[0]}) mod 3 = {h}, bu yüzden item partition {h}'ye gider. Aynı pk'li item'lar her zaman aynı partition'a, sk'ye göre sıralı olarak düşer."),
                      "marks": {"items": {i: "read"}, f"p{h}": {len(parts[h]) - 1: "new"}},
                      "rows": {f"p{k}": sorted(deepcopy(parts[k])) for k in range(3)}, "count": {"partitions touched": 1}})
    target = "CART#3c8d"
    h = _hash(target)
    final = {f"p{k}": sorted(deepcopy(parts[k])) for k in range(3)}
    steps.append({"say": T(lang, f"Now a Query asks for pk = {target}. DynamoDB calculates the same hash: {h}. It reads only partition {h}, and only the item collection of {target}. The other partitions do no work, at any table size.",
                           f"Şimdi bir Query pk = {target} istiyor. DynamoDB aynı hash'i hesaplar: {h}. Sadece partition {h}'yi ve sadece {target} item collection'ını okur. Table ne kadar büyük olursa olsun diğer partition'lar iş yapmaz."),
                  "marks": {f"p{h}": {k: "match" for k, r in enumerate(final[f'p{h}']) if r[0] == target}}, "rows": final, "count": {"partitions touched": 1}})
    return {"tables": [{"id": "items", "name": T(lang, "items to write", "yazılacak item'lar"), "cols": ["pk", "sk", "qty"], "rows": [[r[0], r[1], r[3]] for r in rows], "key": [0, 1], "ref": []}]
            + [{"id": f"p{k}", "name": f"partition {k}", "cols": ["pk", "sk", "qty"], "rows": [], "key": [0, 1], "ref": []} for k in range(3)],
            "out": None, "steps": steps}


def ddb_query_scan(lang):
    rows = sorted(CART["rows"], key=lambda r: (r[0], r[1]))
    tbl = [[r[0], r[1], r[3]] for r in rows]
    steps = [{"say": T(lang, "Two questions on the same eight items. First: the cart CART#7f3a (Query). Second: every item with qty >= 2 in any cart (Scan with a filter). Each item here is smaller than 1 KB.",
                       "Aynı sekiz item üzerinde iki soru. Birincisi: CART#7f3a sepeti (Query). İkincisi: herhangi bir sepette qty >= 2 olan her item (filtreli Scan). Buradaki her item 1 KB'tan küçük."),
              "marks": {}, "out": [], "count": {"items read": 0, "items returned": 0}}]
    out, marks = [], {}
    for i, r in enumerate(tbl):
        if r[0] != "CART#7f3a":
            continue
        marks[i] = "match"
        out.append(["Query", r[0], r[1], r[2]])
        steps.append({"say": T(lang, f"Query: DynamoDB goes straight to the item collection of CART#7f3a and reads {r[1]}.",
                               f"Query: DynamoDB doğrudan CART#7f3a item collection'ına gider ve {r[1]}'i okur."),
                      "marks": {"t": dict(marks)}, "out": deepcopy(out), "outmarks": {len(out) - 1: "new"}, "count": {"items read": len(marks), "items returned": len(out)}})
    q_read = len(marks)
    steps.append({"say": T(lang, f"Query done: {q_read} items read, {q_read} returned. The total size is far below 4 KB, so a strongly consistent Query costs 1 read request unit.",
                           f"Query bitti: {q_read} item okundu, {q_read} döndü. Toplam boyut 4 KB'ın çok altında, bu yüzden strongly consistent bir Query 1 read request unit tutar."),
                  "marks": {"t": dict(marks)}, "out": deepcopy(out), "count": {"items read": q_read, "items returned": q_read}})
    s_out, smarks = [], {}
    for i, r in enumerate(tbl):
        hit = r[2] >= 2
        smarks = {**{k: ("match" if tbl[k][2] >= 2 else "skip") for k in smarks}, i: "match" if hit else "read"}
        if hit:
            s_out.append(["Scan", r[0], r[1], r[2]])
        steps.append({"say": T(lang, f"Scan, item {i + 1}: {r[0]} {r[1]}, qty = {r[2]}. " + ("The filter keeps it." if hit else "The filter drops it, but DynamoDB already read it, and you pay for the read."),
                               f"Scan, item {i + 1}: {r[0]} {r[1]}, qty = {r[2]}. " + ("Filtre onu tutar." if hit else "Filtre onu atar, ama DynamoDB onu zaten okudu ve okumanın parasını ödersin.")),
                      "marks": {"t": dict(smarks)}, "out": deepcopy(out + s_out), "outmarks": {len(out) + len(s_out) - 1: "new"} if hit else {},
                      "count": {"items read": i + 1, "items returned": len(s_out)}})
    steps.append({"say": T(lang, f"Scan done: {len(tbl)} items read, {len(s_out)} returned. On a table of 100 million items, the Scan reads 100 million items, and the Query still reads only the items of one cart.",
                           f"Scan bitti: {len(tbl)} item okundu, {len(s_out)} döndü. 100 milyon item'lık bir table'da Scan 100 milyon item okur, Query ise hâlâ sadece tek bir sepetin item'larını okur."),
                  "marks": {"t": {k: ("match" if tbl[k][2] >= 2 else "skip") for k in range(len(tbl))}}, "out": out + s_out, "count": {"items read": len(tbl), "items returned": len(s_out)}})
    return {"tables": [{"id": "t", "name": "dbws-cart", "cols": ["pk", "sk", "qty"], "rows": tbl, "key": [0, 1], "ref": []}],
            "out": {"name": T(lang, "results", "sonuçlar"), "cols": [T(lang, "operation", "işlem"), "pk", "sk", "qty"]}, "steps": steps}


def ddb_condition(lang):
    item = [["CART#7f3a", "ITEM#P0001", 2]]
    log, steps = [], []

    def snap(say, cls, extra="new"):
        steps.append({"say": say, "marks": {"t": {0: cls}}, "rows": {"t": deepcopy(item)}, "out": deepcopy(log), "outmarks": {len(log) - 1: extra} if log else {}, "count": {}})
    snap(T(lang, "The rule of the shop: at most 5 pieces of one product in a cart. The item has qty = 2. Two requests arrive.",
           "Mağazanın kuralı: bir sepette bir üründen en fazla 5 adet. Item'da qty = 2. İki istek geliyor."), "read")
    log.append(["ADD qty 4, condition qty <= 1", T(lang, "2 <= 1 is false: refused, ConditionalCheckFailedException", "2 <= 1 yanlış: reddedildi, ConditionalCheckFailedException")])
    snap(T(lang, "Request 1 wants to add 4. The condition is qty <= 5 - 4, so qty <= 1. The current qty is 2, so the condition is false. DynamoDB does not write. The item keeps qty 2.",
           "İstek 1, 4 eklemek istiyor. Koşul qty <= 5 - 4, yani qty <= 1. Güncel qty 2, bu yüzden koşul yanlış. DynamoDB yazmaz. Item qty 2'de kalır."), "bad", "bad")
    item[0][2] = 5
    log.append(["ADD qty 3, condition qty <= 2", T(lang, "2 <= 2 is true: written, qty is now 5", "2 <= 2 doğru: yazıldı, qty artık 5")])
    snap(T(lang, "Request 2 wants to add 3. The condition is qty <= 2. The current qty is 2, so the condition is true. DynamoDB tests and writes in one step: qty becomes 5.",
           "İstek 2, 3 eklemek istiyor. Koşul qty <= 2. Güncel qty 2, bu yüzden koşul doğru. DynamoDB tek adımda test eder ve yazar: qty 5 olur."), "match")
    return {"tables": [{"id": "t", "name": T(lang, "the cart item", "sepet item'ı"), "cols": ["pk", "sk", "qty"], "rows": deepcopy([["CART#7f3a", "ITEM#P0001", 2]]), "key": [0, 1], "ref": []}],
            "out": {"name": T(lang, "requests", "istekler"), "cols": ["UpdateItem", T(lang, "answer of DynamoDB", "DynamoDB'nin cevabı")]}, "steps": steps}


def ddb_gsi(lang):
    base = sorted(([r[0], r[1], r[3]] for r in CART["rows"]), key=lambda r: (r[0], r[1]))
    gsi = sorted(([r[1], r[0], r[2]] for r in base), key=lambda r: (r[0], r[1]))
    want = "ITEM#P0044"
    steps = [{"say": T(lang, f"Question: which carts contain {want}? The base table is keyed by cart (pk), so the question has no partition key there. A global secondary index (GSI) keeps a copy keyed by product.",
                       f"Soru: hangi sepetlerde {want} var? Ana table sepete göre (pk) key'lenmiş, bu yüzden orada sorunun bir partition key'i yok. Bir global secondary index (GSI), ürüne göre key'lenmiş bir kopya tutar."),
              "marks": {}, "count": {"items read on the base table": 0, "items read on the GSI": 0}}]
    m = {}
    for i, r in enumerate(base):
        m = {**{k: ("match" if base[k][1] == want else "skip") for k in m}, i: "match" if r[1] == want else "read"}
        steps.append({"say": T(lang, f"Without the GSI, only a Scan helps: item {i + 1} ({r[0]}, {r[1]}).", f"GSI olmadan sadece bir Scan yardım eder: item {i + 1} ({r[0]}, {r[1]})."),
                      "marks": {"b": dict(m)}, "count": {"items read on the base table": i + 1, "items read on the GSI": 0}})
    hits = {k: "match" for k, r in enumerate(gsi) if r[0] == want}
    steps.append({"say": T(lang, f"With the GSI: Query the index with partition key {want}. DynamoDB reads only the {len(hits)} entries of that product. DynamoDB keeps the index up to date at each write of the base table, and these index writes also cost write units.",
                           f"GSI ile: index'i {want} partition key'iyle sorgula. DynamoDB sadece o ürünün {len(hits)} entry'sini okur. DynamoDB ana table'a her yazmada index'i günceller ve bu index yazmaları da write unit tüketir."),
                  "marks": {"b": {k: ("match" if r[1] == want else "skip") for k, r in enumerate(base)}, "g": hits},
                  "count": {"items read on the base table": len(base), "items read on the GSI": len(hits)}})
    return {"tables": [{"id": "b", "name": T(lang, "base table (pk = cart)", "ana table (pk = sepet)"), "cols": ["pk", "sk", "qty"], "rows": base, "key": [0, 1], "ref": []},
                       {"id": "g", "name": T(lang, "GSI by product (pk = sk of the base table)", "ürüne göre GSI (pk = ana table'ın sk'si)"), "cols": ["gsi pk", "gsi sk", "qty"], "rows": gsi, "key": [0, 1], "ref": []}],
            "out": None, "steps": steps}


DDB_CANDS = ["DynamoDB", "Aurora PostgreSQL", "ElastiCache (Valkey)", "Redshift", "Keyspaces"]


# ---------------------------------------------------------------- DynamoDB: architecture decisions as scorecards
def R(must, axis, text, why, **cells):
    """One requirement. axis/text/why: (en, tr). cells: candidate key -> (score, en, tr)."""
    return {"must": must, "axis": axis, "text": text, "why": why, "cells": cells}


def _cells(r, names):
    r = dict(r)
    r["cells"] = {names[k]: v for k, v in r["cells"].items()}
    return r


DDB_NAMES = {"ddb": "DynamoDB", "aur": "Aurora PostgreSQL", "ec": "ElastiCache (Valkey)", "doc": "DocumentDB", "ks": "Keyspaces",
             "rs": "Redshift", "os": "OpenSearch"}

DDB_DECISIONS = {
    # 1. A clear win
    "decide_win": {
        "cands": ["ddb", "ks", "aur", "ec", "doc"],
        "workload": ("A parcel company builds the \"Where is my order?\" screen of its mobile app. Each customer opens the app, sees the status of one order, and scrolls the list of their last 20 orders. "
                     "On a normal day the screen gets 2,000 reads per second. On the night of a national sale, it gets 60,000 reads per second for three hours. The team has three developers and no database administrator.",
                     "Bir kargo şirketi mobil uygulamasının \"Siparişim nerede?\" ekranını yapıyor. Her müşteri uygulamayı açar, bir siparişin durumunu görür ve son 20 siparişinin listesini kaydırır. "
                     "Normal bir günde ekran saniyede 2.000 okuma alır. Ulusal bir indirim gecesinde üç saat boyunca saniyede 60.000 okuma alır. Ekipte üç geliştirici var, veritabanı yöneticisi yok."),
        "reqs": [
            R(True, ("Access pattern", "Erişim deseni"),
              ("The app reads one order by its order id, and it lists the last 20 orders of one customer, newest first. When the courier scans the parcel, the status must change only if the current status is \"shipped\". So an old scan cannot overwrite a newer one.",
               "Uygulama bir siparişi order id ile okur ve bir müşterinin son 20 siparişini en yeni önce listeler. Kurye paketi okuttuğunda durum, sadece mevcut durum \"shipped\" ise değişmeli; böylece eski bir okutma daha yenisinin üstüne yazamaz."),
              ("Every database can store orders. The question is whether these two reads and this one conditional write are cheap, direct operations, or work that the application must build itself.",
               "Her database sipariş saklayabilir. Soru, bu iki okumanın ve bu tek koşullu yazmanın ucuz ve doğrudan işlemler mi, yoksa uygulamanın kendisinin kurması gereken işler mi olduğudur."),
              ddb=(2, "GetItem by order id. Query on the customer as partition key, sorted by date, newest first. UpdateItem with a ConditionExpression on the status.", "Order id ile GetItem. Müşteri partition key, tarihe göre sıralı, en yeni önce Query. Status üzerinde ConditionExpression ile UpdateItem."),
              ks=(1, "Both reads are direct. The conditional status change needs a lightweight transaction (IF status = 'shipped'), which costs more and is slower than a normal write.", "İki okuma da doğrudan. Koşullu durum değişikliği bir lightweight transaction (IF status = 'shipped') ister; bu normal bir yazmadan daha pahalı ve yavaştır."),
              aur=(2, "An index on order id and an index on (customer, date). UPDATE ... WHERE status = 'shipped' does the condition.", "Order id ve (müşteri, tarih) üzerinde index. UPDATE ... WHERE status = 'shipped' koşulu yapar."),
              ec=(1, "One key per order is direct. The list of the last 20 needs a sorted set that the application keeps up to date, and the condition needs a Lua script.", "Sipariş başına bir key doğrudan. Son 20'nin listesi, uygulamanın güncel tuttuğu bir sorted set ister; koşul da bir Lua script'i ister."),
              doc=(2, "find by _id, an index on (customer, date), and updateOne with a filter on the status.", "_id ile find, (müşteri, tarih) üzerinde index ve status filtreli updateOne.")),
            R(True, ("Scale and traffic shape", "Ölçek ve trafik şekli"),
              ("Traffic goes from 2,000 to 60,000 reads per second in about ten minutes when the sale starts, and back down after three hours. During the peak, each read must still answer in less than 20 milliseconds, and nobody may have to change the database by hand.",
               "İndirim başladığında trafik yaklaşık on dakikada saniyede 2.000 okumadan 60.000 okumaya çıkar ve üç saat sonra geri iner. Tepe anında da her okuma 20 milisaniyeden kısa sürede cevap vermeli ve kimse database'i elle değiştirmek zorunda kalmamalı."),
              ("A screen that is slow on the busiest night of the year costs the most money. The database must follow the traffic by itself, not after a person sees an alarm.",
               "Yılın en yoğun gecesinde yavaşlayan bir ekran en çok parayı kaybettirir. Database trafiği kendisi takip etmeli, birisi bir alarm gördükten sonra değil."),
              ddb=(2, "On-demand mode serves new peaks with no capacity setting. Reads by key take single-digit milliseconds at any size.", "On-demand mod yeni tepeleri kapasite ayarı olmadan karşılar. Key ile okumalar her boyutta tek haneli milisaniye sürer."),
              ks=(2, "On-demand capacity mode follows the traffic. Reads by partition key take single-digit milliseconds.", "On-demand kapasite modu trafiği takip eder. Partition key ile okumalar tek haneli milisaniye sürer."),
              aur=(1, "Up to 15 readers can share the reads, but you add them or size Serverless v2 in advance. Thirty times more connections is a planning task.", "15'e kadar reader okumaları paylaşabilir, ama onları önceden eklersin ya da Serverless v2'yi önceden boyutlandırırsın. Otuz kat daha fazla bağlantı bir planlama işidir."),
              ec=(2, "ElastiCache Serverless scales by itself and answers in less than a millisecond.", "ElastiCache Serverless kendi kendine ölçeklenir ve bir milisaniyenin altında cevap verir."),
              doc=(1, "Read replicas help, but they are instances that you add and size before the sale.", "Read replica'lar yardım eder, ama onlar indirimden önce eklediğin ve boyutlandırdığın instance'lardır.")),
            R(False, ("Durability", "Dayanıklılık"),
              ("The order status is official information. Customer service uses it to answer complaints. After the database confirms a status change, the change must not be lost, also if a whole data center (Availability Zone) fails.",
               "Sipariş durumu resmi bir bilgidir. Müşteri hizmetleri şikâyetleri onunla cevaplar. Database bir durum değişikliğini onayladıktan sonra, bütün bir veri merkezi (Availability Zone) arızalansa bile değişiklik kaybolmamalı."),
              ("A fast store that can forget confirmed writes is a cache, not the place for a record that people rely on.",
               "Onaylanmış yazmaları unutabilen hızlı bir depo bir cache'tir; insanların güvendiği bir kaydın yeri değildir."),
              ddb=(2, "Each write is stored in several Availability Zones before DynamoDB confirms it.", "DynamoDB onaylamadan önce her yazma birkaç Availability Zone'da saklanır."),
              ks=(2, "Data is stored three times across Availability Zones.", "Veri Availability Zone'lara dağıtılarak üç kez saklanır."),
              aur=(2, "Six copies in three Availability Zones. COMMIT waits for four of them.", "Üç Availability Zone'da altı kopya. COMMIT dördünü bekler."),
              ec=(1, "Serverless keeps replicas in several Availability Zones, but it has no durable write log, so a failure can lose the newest writes.", "Serverless birkaç Availability Zone'da replica tutar, ama dayanıklı bir yazma log'u yoktur; bu yüzden bir arıza en yeni yazmaları kaybettirebilir."),
              doc=(2, "Six copies in three Availability Zones, like Aurora.", "Aurora gibi üç Availability Zone'da altı kopya.")),
            R(False, ("Operations and team skills", "Operasyon ve ekip becerisi"),
              ("Three developers own the whole service. They write Python with the AWS SDK. They do not want to patch servers, plan version upgrades, size instances or learn a new query language before the sale.",
               "Servisin tamamı üç geliştiricinin sorumluluğunda. AWS SDK ile Python yazıyorlar. İndirimden önce sunucu patch'lemek, versiyon yükseltmesi planlamak, instance boyutlandırmak ya da yeni bir query dili öğrenmek istemiyorlar."),
              ("Every hour that the team spends on the database is an hour that it does not spend on the app. Small teams pay the most for operational work.",
               "Ekibin database'e harcadığı her saat, uygulamaya harcamadığı bir saattir. Operasyon işinin bedelini en çok küçük ekipler öder."),
              ddb=(2, "Serverless, no versions, the same AWS SDK that the team uses.", "Serverless, versiyon yok, ekibin kullandığı AWS SDK'nın aynısı."),
              ks=(1, "Serverless, but the team must learn CQL, a Cassandra driver and table design per query.", "Serverless, ama ekip CQL'i, bir Cassandra driver'ını ve query başına table tasarımını öğrenmeli."),
              aur=(1, "Managed, but there are instances, engine versions, connection pools and SQL schema changes.", "Yönetilen bir servis, ama instance'lar, engine versiyonları, bağlantı havuzları ve SQL schema değişiklikleri var."),
              ec=(2, "Serverless, with no nodes to size.", "Serverless, boyutlandırılacak node yok."),
              doc=(1, "Managed, but you select and size instances and plan engine upgrades.", "Yönetilen bir servis, ama instance seçer, boyutlandırır ve engine yükseltmelerini planlarsın.")),
            R(False, ("Cost model", "Maliyet modeli"),
              ("For about 20 hours of each day the screen is almost idle. The company wants to pay for the reads and writes that customers really make, not for servers that wait all night.",
               "Her günün yaklaşık 20 saatinde ekran neredeyse boştur. Şirket, bütün gece bekleyen sunuculara değil, müşterilerin gerçekten yaptığı okuma ve yazmalara ödeme yapmak istiyor."),
              ("A peak that is 30 times the normal load makes fixed capacity very expensive: you pay all year for one night.",
               "Normal yükün 30 katı olan bir tepe, sabit kapasiteyi çok pahalı yapar: bir gece için bütün yıl ödersin."),
              ddb=(2, "On-demand: you pay per request and per GB stored.", "On-demand: istek başına ve saklanan GB başına ödersin."),
              ks=(2, "On-demand: you pay per read and write request.", "On-demand: okuma ve yazma isteği başına ödersin."),
              aur=(1, "Serverless v2 follows the load, but you pay capacity per hour, and readers for the peak cost while they run.", "Serverless v2 yükü takip eder, ama kapasiteyi saat başına ödersin ve tepe için reader'lar çalıştıkları sürece ücretlidir."),
              ec=(1, "You pay for the data that is stored and for the requests. The data is in memory, which costs more per GB.", "Saklanan veri ve istekler için ödersin. Veri bellektedir; GB başına daha pahalıdır."),
              doc=(0, "Instances run and cost money every hour, also at night.", "Instance'lar her saat çalışır ve ücretlidir, gece de.")),
        ],
        "gap": ("DynamoDB meets every requirement fully. Keyspaces is close on scale and cost, but the conditional status change and a new query language cost it two points. The others lose on scale or on operations, not on the access pattern.",
                "DynamoDB her gereksinimi tam karşılar. Keyspaces ölçekte ve maliyette yakındır, ama koşullu durum değişikliği ve yeni bir query dili ona iki puan kaybettirir. Diğerleri erişim deseninde değil, ölçekte ya da operasyonda kaybeder."),
        "pivot": ("Suppose that the company already runs Cassandra, with CQL code and a team that knows it. Then Keyspaces would score ✓ on operations, and the two would be equal.",
                  "Şirket zaten CQL koduyla ve onu bilen bir ekiple Cassandra çalıştırıyor olsaydı Keyspaces operasyonda ✓ alırdı ve ikisi eşit olurdu."),
    },
    # 2. A clear loss
    "decide_lose": {
        "cands": ["ddb", "rs", "aur", "os", "doc"],
        "workload": ("The finance team of an online shop wants a report every morning. It shows the revenue for each product category and each customer city, month by month, for the last 24 months. "
                     "The orders are in an Aurora database, about 300 million order lines in total. The analysts also want to change the question during the meeting and see the new answer in seconds.",
                     "Bir online mağazanın finans ekibi her sabah bir rapor istiyor: son 24 ay için, ay ay, her ürün kategorisi ve her müşteri şehri için gelir. "
                     "Siparişler bir Aurora database'inde, toplam yaklaşık 300 milyon sipariş satırı. Analistler ayrıca toplantı sırasında soruyu değiştirmek ve yeni cevabı saniyeler içinde görmek istiyor."),
        "reqs": [
            R(True, ("Kind of question", "Sorunun türü"),
              ("The report joins order lines with products (for the category) and with customers (for the city). Then it groups them by month, category and city, and adds up the amounts. Next week the question will be different, for example \"only first orders\" or \"by payment method\".",
               "Rapor sipariş satırlarını ürünlerle (kategori için) ve müşterilerle (şehir için) join'ler, ay, kategori ve şehre göre gruplar ve tutarları toplar. Gelecek hafta soru farklı olacak, örneğin \"sadece ilk siparişler\" ya da \"ödeme yöntemine göre\"."),
              ("A report is not a lookup by key. It reads most of the data and combines several tables. Each new question must be a new query, not a new database design.",
               "Bir rapor key ile okuma değildir. Verinin çoğunu okur ve birkaç table'ı birleştirir. Her yeni soru yeni bir database tasarımı değil, yeni bir query olmalıdır."),
              ddb=(0, "No JOIN and no GROUP BY. The application must Scan every item and add up the numbers itself, and each new question needs a new key design.", "JOIN ve GROUP BY yok. Uygulama her item'ı Scan etmeli ve sayıları kendisi toplamalı; her yeni soru yeni bir key tasarımı ister."),
              rs=(2, "SQL with JOIN, GROUP BY and window functions over any columns.", "Her column üzerinde JOIN, GROUP BY ve window function'lı SQL."),
              aur=(2, "Full SQL. The same query language as the shop.", "Tam SQL. Mağazayla aynı query dili."),
              os=(1, "Aggregations can group and add up, but there is no JOIN between indexes, so the data must be copied into one flat index first.", "Aggregation'lar gruplayıp toplayabilir, ama index'ler arasında JOIN yoktur; bu yüzden veri önce düz bir index'e kopyalanmalıdır."),
              doc=(1, "The aggregation pipeline can group, and $lookup can join, but $lookup over hundreds of millions of documents is slow.", "Aggregation pipeline gruplayabilir ve $lookup join'leyebilir, ama yüz milyonlarca document üzerinde $lookup yavaştır.")),
            R(True, ("Speed of a large scan", "Büyük taramanın hızı"),
              ("Each run reads about 300 million order lines but only four of their twenty columns. The answer must come back in less than 10 seconds, so the analysts can change the question in the meeting.",
               "Her çalıştırma yaklaşık 300 milyon sipariş satırı okur ama yirmi column'un sadece dördünü. Cevap 10 saniyeden kısa sürede gelmeli, böylece analistler soruyu toplantıda değiştirebilir."),
              ("For a report, the cost is the number of bytes that the database must read. A design that reads complete rows reads five times more than this report needs.",
               "Bir rapor için maliyet, database'in okuması gereken byte sayısıdır. Tam row'ları okuyan bir tasarım bu raporun ihtiyacından beş kat fazlasını okur."),
              ddb=(0, "A Scan reads every item completely and is charged per 4 KB. It takes minutes to hours.", "Bir Scan her item'ı tamamen okur ve 4 KB başına ücretlendirilir. Dakikalar ile saatler sürer."),
              rs=(2, "Column storage reads only the four columns, and many slices scan in parallel.", "Kolon bazlı saklama sadece dört kolonu okur ve birçok slice paralel tarar."),
              aur=(0, "A row store reads complete rows. A scan of 300 million rows takes minutes, not seconds.", "Bir row store tam row'ları okur. 300 milyon row'un taranması saniyeler değil dakikalar sürer."),
              os=(1, "Aggregations are fast on one flat index, if the data was copied and flattened before.", "Veri önceden kopyalanıp düzleştirildiyse, aggregation'lar tek bir düz index'te hızlıdır."),
              doc=(0, "A collection scan with $lookup over this volume takes minutes.", "Bu hacimde $lookup'lı bir collection scan dakikalar sürer.")),
            R(False, ("Effect on the shop", "Mağazaya etkisi"),
              ("The checkout writes to Aurora all day. The report must not make the checkout slower, not even for one minute, also when an analyst runs a very large query by mistake.",
               "Checkout bütün gün Aurora'ya yazar. Rapor checkout'u yavaşlatmamalı, bir dakika bile; bir analist yanlışlıkla çok büyük bir query çalıştırdığında bile."),
              ("When the report and the shop share one database, every heavy report is a risk for revenue.",
               "Rapor ve mağaza aynı database'i paylaştığında her ağır rapor gelir için bir risktir."),
              ddb=(1, "A separate table, but the data must be copied there first, and a Scan uses capacity of that table.", "Ayrı bir table, ama veri önce oraya kopyalanmalı ve bir Scan o table'ın kapasitesini kullanır."),
              rs=(2, "A separate warehouse. A zero-ETL integration copies the orders from Aurora.", "Ayrı bir warehouse. Bir zero-ETL entegrasyonu siparişleri Aurora'dan kopyalar."),
              aur=(1, "Possible on a separate reader instance, but it is still the same cluster.", "Ayrı bir reader instance'ta mümkün, ama yine aynı cluster'dır."),
              os=(2, "A separate copy of the data.", "Verinin ayrı bir kopyası."),
              doc=(2, "A separate copy of the data.", "Verinin ayrı bir kopyası.")),
            R(False, ("Tools of the analysts", "Analistlerin araçları"),
              ("The analysts use a BI tool that connects with JDBC and sends SQL. They know SQL well and do not write code.",
               "Analistler JDBC ile bağlanan ve SQL gönderen bir BI aracı kullanıyor. SQL'i iyi biliyorlar ve kod yazmıyorlar."),
              ("A database that the analysts cannot query themselves makes every new question a ticket for the developers.",
               "Analistlerin kendilerinin sorgulayamadığı bir database, her yeni soruyu geliştiriciler için bir iş talebine çevirir."),
              ddb=(0, "PartiQL has no JOIN and no GROUP BY. BI tools cannot use it for this report.", "PartiQL'de JOIN ve GROUP BY yok. BI araçları bu rapor için onu kullanamaz."),
              rs=(2, "SQL, JDBC and ODBC drivers.", "SQL, JDBC ve ODBC driver'ları."),
              aur=(2, "SQL and JDBC.", "SQL ve JDBC."),
              os=(1, "A SQL plugin exists, with limits.", "Sınırlı bir SQL plugin'i var."),
              doc=(1, "A JDBC driver exists, but the queries are MongoDB queries.", "Bir JDBC driver'ı var, ama query'ler MongoDB query'leridir.")),
            R(False, ("Freshness without pipeline code", "Pipeline kodu olmadan güncellik"),
              ("The report must include the orders of the last few minutes. The team does not want to write or run an ETL job for it.",
               "Rapor son birkaç dakikanın siparişlerini içermeli ve ekip bunun için bir ETL job'u yazmak ya da çalıştırmak istemiyor."),
              ("Every pipeline that you write is code that can break at night. A managed copy does this work for you.",
               "Yazdığın her pipeline gece bozulabilecek bir koddur. Yönetilen bir kopya bu işi ortadan kaldırır."),
              ddb=(0, "The orders are in Aurora. A pipeline must copy them to DynamoDB.", "Siparişler Aurora'da. Bir pipeline onları DynamoDB'ye kopyalamalı."),
              rs=(2, "Zero-ETL from Aurora: new orders arrive within seconds, with no code.", "Aurora'dan zero-ETL: yeni siparişler kod olmadan saniyeler içinde gelir."),
              aur=(2, "It is the source itself.", "Kaynağın kendisidir."),
              os=(1, "An ingestion pipeline must copy and flatten the orders.", "Bir ingestion pipeline'ı siparişleri kopyalayıp düzleştirmeli."),
              doc=(0, "A pipeline must copy the orders.", "Bir pipeline siparişleri kopyalamalı.")),
        ],
        "gap": ("Redshift meets every requirement. OpenSearch is second only because it can aggregate a flattened copy. DynamoDB is out at the first requirement: a key-value store answers \"give me this item\", not \"add up everything\".",
                "Redshift her gereksinimi karşılar. OpenSearch sadece düzleştirilmiş bir kopyayı aggregate edebildiği için ikincidir. DynamoDB ilk gereksinimde elenir: bir key-value store \"bana bu item'ı ver\" sorusunu cevaplar, \"her şeyi topla\" sorusunu değil."),
        "pivot": None,
    },
    # 3. Close race: sessions
    "race_session": {
        "cands": ["ec", "ddb", "ks", "aur", "doc"],
        "workload": ("An online shop keeps the login session of each visitor: the user id, the last page, the language and a few flags. Every API call of the web site reads the session, and every page view writes the time of the last activity. "
                     "At peak there are 40,000 calls per second. A session ends 30 minutes after the last activity. The shopping cart is stored in a different database, so a lost session only means that the visitor must log in again.",
                     "Bir online mağaza her ziyaretçinin login oturumunu tutuyor: kullanıcı id'si, son sayfa, dil ve birkaç bayrak. Web sitesinin her API çağrısı oturumu okur ve her sayfa görüntülemesi son aktivitenin zamanını yazar. "
                     "Tepe anında saniyede 40.000 çağrı var. Bir oturum son aktiviteden 30 dakika sonra biter. Sepet başka bir database'te saklanıyor; bu yüzden kaybolan bir oturum sadece ziyaretçinin yeniden login olması demektir."),
        "reqs": [
            R(True, ("Access pattern", "Erişim deseni"),
              ("The application reads and writes one session by its session id, which is in the browser cookie. It never searches sessions by any other field.",
               "Uygulama bir oturumu, tarayıcı cookie'sindeki session id ile okur ve yazar. Oturumları hiçbir zaman başka bir alana göre aramaz."),
              ("This is the purest key-value access: one key, one value. Every candidate can do it, so this requirement does not separate them. It only shows that they are all in the race.",
               "Bu en saf key-value erişimidir: bir key, bir değer. Her aday bunu yapabilir; bu yüzden bu gereksinim onları ayırmaz. Sadece hepsinin yarışta olduğunu doğrular."),
              ec=(2, "GET and SET, or a hash per session.", "GET ve SET ya da oturum başına bir hash."),
              ddb=(2, "GetItem and PutItem by the session id.", "Session id ile GetItem ve PutItem."),
              ks=(2, "SELECT and UPDATE by the partition key.", "Partition key ile SELECT ve UPDATE."),
              aur=(2, "A primary key lookup.", "Bir primary key araması."),
              doc=(2, "find by _id.", "_id ile find.")),
            R(True, ("Scale and latency", "Ölçek ve gecikme"),
              ("At peak, 40,000 calls per second each read the session, and about 10,000 per second also write it. The session read is in the path of every call, so it must add less than 10 milliseconds.",
               "Tepe anında saniyede 40.000 çağrının her biri oturumu okur ve saniyede yaklaşık 10.000'i onu yazar da. Oturum okuması her çağrının yolundadır; bu yüzden 10 milisaniyeden az eklemelidir."),
              ("A slow session store makes the whole site slow, because every page waits for it.",
               "Yavaş bir oturum deposu bütün siteyi yavaşlatır, çünkü her sayfa onu bekler."),
              ec=(2, "Less than one millisecond from memory, and Serverless scales by itself.", "Bellekten bir milisaniyenin altında; Serverless kendi kendine ölçeklenir."),
              ddb=(2, "Single-digit milliseconds, and on-demand mode follows the traffic.", "Tek haneli milisaniye; on-demand mod trafiği takip eder."),
              ks=(2, "Single-digit milliseconds, on-demand capacity.", "Tek haneli milisaniye, on-demand kapasite."),
              aur=(1, "Reads are fast, but 10,000 writes per second on one writer instance, with connection pools, needs a large instance and care.", "Okumalar hızlı, ama tek bir writer instance'ta bağlantı havuzlarıyla saniyede 10.000 yazma büyük bir instance ve özen ister."),
              doc=(1, "Possible with a large primary instance, sized in advance.", "Önceden boyutlandırılmış büyük bir primary instance ile mümkün.")),
            R(False, ("Durability", "Dayanıklılık"),
              ("If the session store fails, the visitor must log in again. The cart is safe in another database. The business says that this is acceptable on a rare failure, but not every day.",
               "Oturum deposu arızalanırsa ziyaretçi yeniden login olmalıdır. Sepet başka bir database'te güvende. İşletme bunun nadir bir arızada kabul edilebilir olduğunu, ama her gün olamayacağını söylüyor."),
              ("This is the requirement that decides this race. A session is not money, so a store with partial durability is allowed here.",
               "Bu yarışı belirleyen gereksinim budur. Bir oturum para değildir; bu yüzden burada kısmi dayanıklılığı olan bir depoya izin vardır."),
              ec=(1, "Serverless keeps replicas in several Availability Zones, but it has no durable write log: a failure can lose recent sessions.", "Serverless birkaç Availability Zone'da replica tutar, ama dayanıklı bir yazma log'u yoktur: bir arıza son oturumları kaybettirebilir."),
              ddb=(2, "Each write is stored in several Availability Zones before DynamoDB confirms it.", "DynamoDB onaylamadan önce her yazma birkaç Availability Zone'da saklanır."),
              ks=(2, "Three copies across Availability Zones.", "Availability Zone'lara dağıtılmış üç kopya."),
              aur=(2, "Six copies in three Availability Zones.", "Üç Availability Zone'da altı kopya."),
              doc=(2, "Six copies in three Availability Zones.", "Üç Availability Zone'da altı kopya.")),
            R(False, ("Expiry", "Süre sonu"),
              ("A session must end exactly 30 minutes after the last activity. Each page view moves the end time forward. An expired session must never be accepted, also not for one minute.",
               "Bir oturum son aktiviteden tam 30 dakika sonra bitmeli. Her sayfa görüntülemesi bitiş zamanını ileri alır. Süresi dolmuş bir oturum, bir dakika bile, asla kabul edilmemeli."),
              ("Some databases delete expired data late. Then the application must compare the time on every read, and this is easy to forget.",
               "Süresi dolan veriyi geç silen bir database, uygulamayı her okumada zamanı kontrol etmeye zorlar; bunu unutmak kolaydır."),
              ec=(2, "EXPIRE renews the time on each page, and the key is gone exactly at the end.", "EXPIRE her sayfada süreyi yeniler ve key tam sonunda yok olur."),
              ddb=(1, "TTL deletes expired items typically within a few days, so the application must also compare the expiry time on each read.", "TTL süresi dolan item'ları genellikle birkaç gün içinde siler; bu yüzden uygulama her okumada süre sonunu da karşılaştırmalıdır."),
              ks=(1, "TTL works per row, but each renewal must rewrite the row with a new TTL.", "TTL row başına çalışır, ama her yenileme row'u yeni bir TTL ile yeniden yazmalıdır."),
              aur=(0, "No TTL: a scheduled DELETE job that you write and run.", "TTL yok: senin yazıp çalıştırdığın zamanlanmış bir DELETE job'u."),
              doc=(1, "A TTL index deletes expired documents in a background task, not at the exact second.", "Bir TTL index süresi dolan document'ları tam saniyesinde değil, bir arka plan görevinde siler.")),
            R(False, ("Added latency", "Eklenen gecikme"),
              ("The team measures the time of every page. They want the session step to be as close to zero as possible, because it is in front of every other call.",
               "Ekip her sayfanın süresini ölçüyor. Oturum adımının mümkün olduğunca sıfıra yakın olmasını istiyorlar, çünkü diğer her çağrının önünde duruyor."),
              ("Single-digit milliseconds is good. Less than one millisecond is better when the step runs on every call.",
               "Tek haneli milisaniye iyidir. Adım her çağrıda çalıştığında bir milisaniyenin altı daha iyidir."),
              ec=(2, "Microseconds to less than a millisecond from memory.", "Bellekten mikrosaniyelerden bir milisaniyenin altına."),
              ddb=(1, "Single-digit milliseconds.", "Tek haneli milisaniye."),
              ks=(1, "Single-digit milliseconds.", "Tek haneli milisaniye."),
              aur=(1, "Milliseconds, with a connection pool.", "Bağlantı havuzuyla milisaniyeler."),
              doc=(1, "Milliseconds.", "Milisaniyeler.")),
        ],
        "gap": ("ElastiCache wins by one point. DynamoDB is better on durability, but ElastiCache is better on exact expiry and on latency. Because a lost session is acceptable here, durability counts less than speed.",
                "ElastiCache bir puan farkla kazanır. DynamoDB dayanıklılıkta daha iyidir, ama ElastiCache tam süre sonunda ve gecikmede daha iyidir. Burada kaybolan bir oturum kabul edilebilir olduğu için dayanıklılık hızdan daha az sayılır."),
        "pivot": ("Suppose that the session also held payment state that must never be lost. Then durability would be a must, ElastiCache Serverless would score ✗ on it, and DynamoDB would win.",
                  "Oturum asla kaybolmaması gereken ödeme bilgisi de tutsaydı dayanıklılık zorunlu olurdu, ElastiCache Serverless onda ✗ alırdı ve DynamoDB kazanırdı."),
    },
    # 4. Close race: activity history
    "race_activity": {
        "cands": ["ddb", "ks", "aur", "doc", "ix"],
        "workload": ("A shop records every view, search and add-to-cart of every visitor as an event. The events show \"recently viewed\" and feed a fraud test. There are 25,000 new events per second at peak, and the history grows by about 1 TB each month. "
                     "Events older than 90 days have no value. A new team builds the service. It writes Python and JavaScript with the AWS SDK, and there is no existing Cassandra code.",
                     "Bir mağaza, \"son baktıkların\"ı göstermek ve bir dolandırıcılık kontrolünü beslemek için her ziyaretçinin her görüntülemesini, aramasını ve sepete eklemesini bir event olarak kaydediyor. Tepe anında saniyede 25.000 yeni event var ve geçmiş her ay yaklaşık 1 TB büyüyor. "
                     "90 günden eski event'lerin değeri yok. Servisi yeni bir ekip yapıyor. AWS SDK ile Python ve JavaScript yazıyorlar ve var olan bir Cassandra kodu yok."),
        "reqs": [
            R(True, ("Access pattern", "Erişim deseni"),
              ("The service appends one event for each click. The \"recently viewed\" box reads the last 50 events of one visitor, newest first. Nobody reads events of all visitors together.",
               "Servis her tıklama için bir event ekler. \"Son baktıkların\" kutusu bir ziyaretçinin son 50 event'ini en yeni önce okur. Kimse bütün ziyaretçilerin event'lerini birlikte okumaz."),
              ("This is the classic shape of a wide-column or key-value design: one partition per visitor, sorted by time. A design where the visitor id becomes an index tag explodes.",
               "Bu bir wide-column ya da key-value tasarımının klasik şeklidir: ziyaretçi başına bir partition, zamana göre sıralı. Ziyaretçi id'sinin bir index tag'ine dönüştüğü bir tasarım patlar."),
              ddb=(2, "Partition key = visitor, sort key = time. Query with ScanIndexForward = false and Limit = 50.", "Partition key = ziyaretçi, sort key = zaman. ScanIndexForward = false ve Limit = 50 ile Query."),
              ks=(2, "PRIMARY KEY ((visitor), time) with CLUSTERING ORDER BY time DESC, then LIMIT 50.", "CLUSTERING ORDER BY time DESC ile PRIMARY KEY ((visitor), time), sonra LIMIT 50."),
              aur=(2, "An index on (visitor, time) and ORDER BY time DESC LIMIT 50.", "(ziyaretçi, zaman) üzerinde index ve ORDER BY time DESC LIMIT 50."),
              doc=(2, "An index on (visitor, time) and sort with limit.", "(ziyaretçi, zaman) üzerinde index ve limit'li sort."),
              ix=(0, "A visitor id as a tag makes millions of series. The cardinality becomes too high.", "Tag olarak bir ziyaretçi id'si milyonlarca series oluşturur. Cardinality çok yükselir.")),
            R(True, ("Write scale and growth", "Yazma ölçeği ve büyüme"),
              ("At peak, 25,000 small writes per second arrive, spread over millions of visitors. Each month adds 1 TB of data, and there must be no downtime to add storage or capacity.",
               "Tepe anında milyonlarca ziyaretçiye dağılmış saniyede 25.000 küçük yazma ve her ay 1 TB daha fazla veri; storage ya da kapasite eklemek için kesinti olmadan."),
              ("Append-heavy workloads break databases with one writer. The write load must spread over many partitions.",
               "Ekleme ağırlıklı iş yükleri tek yazıcılı database'leri zorlar. Yazma yükü birçok partition'a dağılmalıdır."),
              ddb=(2, "Writes spread over partitions by the visitor id. On-demand mode follows the load.", "Yazmalar ziyaretçi id'sine göre partition'lara dağılır. On-demand mod yükü takip eder."),
              ks=(2, "Writes spread over partitions. Serverless capacity follows the load.", "Yazmalar partition'lara dağılır. Serverless kapasite yükü takip eder."),
              aur=(1, "All writes go to one writer instance. 25,000 inserts per second needs a large instance and table partitioning.", "Bütün yazmalar tek bir writer instance'a gider. Saniyede 25.000 insert büyük bir instance ve table partitioning ister."),
              doc=(1, "All writes go to one primary instance, unless you use elastic clusters.", "Elastic cluster kullanmazsan bütün yazmalar tek bir primary instance'a gider."),
              ix=(1, "Fast writes, but the series problem stays.", "Hızlı yazmalar, ama series sorunu kalır.")),
            R(False, ("Expiry of old data", "Eski verinin süresi"),
              ("Events must disappear 90 days after they were written, with no job to write, run or watch, and without paying for the deletes.",
               "Event'ler yazıldıktan 90 gün sonra kaybolmalı; yazılacak, çalıştırılacak ya da izlenecek bir job olmadan ve silmeler için ödeme yapmadan."),
              ("At 1 TB per month, a forgotten cleanup job means a database that grows forever.",
               "Ayda 1 TB ile unutulmuş bir temizlik job'u, sonsuza kadar büyüyen bir database demektir."),
              ddb=(2, "TTL deletes expired items without consuming write capacity.", "TTL süresi dolan item'ları yazma kapasitesi harcamadan siler."),
              ks=(2, "A default TTL on the table expires each row automatically.", "Table üzerindeki varsayılan bir TTL her row'u otomatik olarak sona erdirir."),
              aur=(1, "Possible with monthly table partitions that a job drops.", "Bir job'un düşürdüğü aylık table partition'larıyla mümkün."),
              doc=(1, "A TTL index deletes documents, but the deletes use I/O of the cluster.", "Bir TTL index document'ları siler, ama silmeler cluster'ın I/O'sunu kullanır."),
              ix=(2, "The retention period of the bucket.", "Bucket'ın retention period'u.")),
            R(False, ("Team skills", "Ekip becerisi"),
              ("The new team knows the AWS SDK for Python and JavaScript. It has no Cassandra experience and no CQL code to reuse, and it must deliver in six weeks.",
               "Yeni ekip Python ve JavaScript için AWS SDK'yı biliyor. Cassandra deneyimi ve yeniden kullanılacak CQL kodu yok; altı haftada teslim etmeli."),
              ("This is the requirement that decides this race. Two technically equal options are not equal for a team that knows only one of them.",
               "Bu yarışı belirleyen gereksinim budur. Teknik olarak eşit iki seçenek, sadece birini bilen bir ekip için eşit değildir."),
              ddb=(2, "The AWS SDK that the team already uses.", "Ekibin zaten kullandığı AWS SDK."),
              ks=(1, "The team must learn CQL, a Cassandra driver and query-first table design.", "Ekip CQL'i, bir Cassandra driver'ını ve query öncelikli table tasarımını öğrenmeli."),
              aur=(2, "SQL is common knowledge.", "SQL yaygın bir bilgidir."),
              doc=(1, "The MongoDB API is new for this team.", "MongoDB API'si bu ekip için yeni."),
              ix=(1, "Line protocol and Flux are new for this team.", "Line protocol ve Flux bu ekip için yeni.")),
            R(False, ("Feed the fraud test", "Dolandırıcılık kontrolünü besleme"),
              ("Each new event must reach a fraud-test function within seconds, without a second write from the application.",
               "Her yeni event, uygulamadan ikinci bir yazma olmadan saniyeler içinde bir dolandırıcılık kontrol fonksiyonuna ulaşmalı."),
              ("With a change stream from the database, the application cannot write the event and then forget to send it.",
               "Database'den gelen bir değişiklik akışı, uygulamanın event'i yazıp göndermeyi unutması riskini ortadan kaldırır."),
              ddb=(2, "DynamoDB Streams starts a Lambda function for each change.", "DynamoDB Streams her değişiklik için bir Lambda fonksiyonu başlatır."),
              ks=(2, "Keyspaces CDC streams record each row change in time order.", "Keyspaces CDC stream'leri her row değişikliğini zaman sırasıyla kaydeder."),
              aur=(1, "Possible with logical replication or a CDC tool that you run.", "Mantıksal replikasyonla ya da senin çalıştırdığın bir CDC aracıyla mümkün."),
              doc=(2, "Change streams.", "Change stream'ler."),
              ix=(0, "No change stream.", "Değişiklik akışı yok.")),
        ],
        "gap": ("DynamoDB wins by one point. On data model, scale, expiry and change streams, DynamoDB and Keyspaces are equal. The only difference is that this team already knows the AWS SDK and has no Cassandra code.",
                "DynamoDB bir puan farkla kazanır. Veri modeli, ölçek, süre sonu ve değişiklik akışında DynamoDB ve Keyspaces eşittir. Tek fark, bu ekibin AWS SDK'yı zaten bilmesi ve Cassandra kodunun olmamasıdır."),
        "pivot": ("Suppose that the company moved an existing Cassandra application, with years of CQL code and a team that knows it. Then Keyspaces would score ✓ on team skills and DynamoDB ~ (a rewrite), and Keyspaces would win.",
                  "Şirket yıllarca CQL kodu olan var olan bir Cassandra uygulamasını, onu bilen bir ekiple taşısaydı Keyspaces ekip becerisinde ✓, DynamoDB ~ (yeniden yazma) alırdı ve Keyspaces kazanırdı."),
    },
    # 5. Close race: shopping cart
    "race_cart": {
        "cands": ["ddb", "aur", "doc", "ec", "ks"],
        "workload": ("An online shop stores the shopping cart of each visitor. Visitors add and change products many times before they buy, and many carts are never bought. "
                     "Normal traffic is 500 cart writes per second, and on campaign evenings it is 5,000 per second for two hours. The orders and the stock are already in Aurora PostgreSQL.",
                     "Bir online mağaza her ziyaretçinin sepetini saklıyor. Ziyaretçiler satın almadan önce ürünleri birçok kez ekler ve değiştirir; birçok sepet hiç satın alınmaz. "
                     "Normal trafik saniyede 500 sepet yazması, kampanya akşamlarında ise iki saat boyunca saniyede 5.000. Siparişler ve stok zaten Aurora PostgreSQL'de."),
        "reqs": [
            R(True, ("Access pattern and rules", "Erişim deseni ve kurallar"),
              ("The cart page reads all lines of one visitor's cart. Each \"add\" increases the quantity of one line by one. The database must refuse a quantity above 5 for one product, also when two browser tabs add at the same time.",
               "Sepet sayfası bir ziyaretçinin sepetinin bütün satırlarını okur. Her \"ekle\" bir satırın miktarını bir artırır ve database bir ürün için 5'in üstündeki miktarı, iki tarayıcı sekmesi aynı anda eklediğinde bile, reddetmelidir."),
              ("The rule must live in the database write itself. A test in the application, followed by a write, loses the race when two tabs click together.",
               "Kural database yazmasının içinde yaşamalı. Uygulamada yapılan bir kontrol ve ardından gelen bir yazma, iki sekme birlikte tıkladığında yarışı kaybeder."),
              ddb=(2, "Query by the cart key. UpdateItem with ADD qty and the condition qty < 5.", "Sepet key'i ile Query. ADD qty ve qty < 5 koşulu ile UpdateItem."),
              aur=(2, "SELECT by an index. UPDATE ... SET qty = qty + 1 WHERE qty < 5.", "Index ile SELECT. UPDATE ... SET qty = qty + 1 WHERE qty < 5."),
              doc=(2, "updateOne with $inc and a filter qty < 5.", "$inc ve qty < 5 filtresiyle updateOne."),
              ec=(1, "HINCRBY increases atomically, but the limit of 5 needs a Lua script.", "HINCRBY atomik artırır, ama 5 sınırı bir Lua script'i ister."),
              ks=(1, "The condition needs a lightweight transaction (IF), which is slower and costs more.", "Koşul bir lightweight transaction (IF) ister; bu daha yavaş ve daha pahalıdır.")),
            R(True, ("Scale on campaign evenings", "Kampanya akşamlarında ölçek"),
              ("When the campaign email goes out, the load goes from 500 to 5,000 cart writes per second within minutes, and back down after two hours. Each write must get an answer in less than 20 milliseconds.",
               "Kampanya e-postası gittiğinde dakikalar içinde saniyede 500'den 5.000 sepet yazmasına, iki saat sonra geri; her yazma 20 milisaniyeden kısa sürede cevaplanmalı."),
              ("5,000 small writes per second is within reach of one large relational writer. So this requirement does not separate the leaders. It shows that the gap is elsewhere.",
               "Saniyede 5.000 küçük yazma tek bir büyük ilişkisel yazıcının ulaşabileceği bir yüktür. Bu yüzden bu gereksinim liderleri ayırmaz. Farkın başka yerde olduğunu gösterir."),
              ddb=(2, "On-demand mode follows the jump.", "On-demand mod sıçramayı takip eder."),
              aur=(2, "One writer handles 5,000 small writes per second, and Serverless v2 adds capacity within its range.", "Tek bir writer saniyede 5.000 küçük yazmayı karşılar ve Serverless v2 kendi aralığı içinde kapasite ekler."),
              doc=(1, "One primary instance that you size before the campaign.", "Kampanyadan önce boyutlandırdığın tek bir primary instance."),
              ec=(2, "Serverless follows the load.", "Serverless yükü takip eder."),
              ks=(2, "On-demand capacity follows the load.", "On-demand kapasite yükü takip eder.")),
            R(False, ("Abandoned carts", "Terk edilen sepetler"),
              ("About 70 percent of carts are never bought. A cart must disappear 24 hours after the last change, with no cleanup job.",
               "Sepetlerin yaklaşık yüzde 70'i hiç satın alınmaz. Bir sepet son değişiklikten 24 saat sonra, temizlik job'u olmadan kaybolmalı."),
              ("A cleanup job is small code, but it is code that someone must run and watch every day.",
               "Bir temizlik job'u küçük bir koddur, ama birinin her gün çalıştırması ve izlemesi gereken bir koddur."),
              ddb=(2, "TTL attribute, deletes without write capacity.", "TTL attribute'u, yazma kapasitesi olmadan siler."),
              aur=(1, "A scheduled DELETE job that you write, run and watch.", "Senin yazdığın, çalıştırdığın ve izlediğin zamanlanmış bir DELETE job'u."),
              doc=(2, "A TTL index.", "Bir TTL index."),
              ec=(2, "EXPIRE.", "EXPIRE."),
              ks=(2, "TTL on the table.", "Table üzerinde TTL.")),
            R(False, ("Checkout consistency", "Checkout tutarlılığı"),
              ("At checkout, the order and the stock change in one transaction in Aurora. The cart is read before and deleted after. If the cart lived in Aurora too, the cart, the stock and the order could change in one transaction.",
               "Checkout'ta sipariş ve stok Aurora'da tek bir transaction'da değişir. Sepet önce okunur ve sonra silinir. Sepet de Aurora'da olsaydı sepet, stok ve sipariş tek bir transaction'da değişebilirdi."),
              ("A cart in a second database means two steps at checkout. A failure between them leaves an old cart behind, which is harmless, but it is one more case to think about.",
               "İkinci bir database'teki sepet, checkout'ta iki adım demektir. Aralarındaki bir arıza geride eski bir sepet bırakır; bu zararsızdır, ama düşünülmesi gereken bir durum daha.")
              ,
              ddb=(1, "Read the cart, commit in Aurora, then delete the cart. An old cart can stay after a failure.", "Sepeti oku, Aurora'da commit et, sonra sepeti sil. Bir arızadan sonra eski bir sepet kalabilir."),
              aur=(2, "Cart, stock and order in one ACID transaction.", "Sepet, stok ve sipariş tek bir ACID transaction'da."),
              doc=(1, "Two steps, like DynamoDB.", "DynamoDB gibi iki adım."),
              ec=(0, "Two steps, and the cart can disappear before checkout.", "İki adım ve sepet checkout'tan önce kaybolabilir."),
              ks=(1, "Two steps, like DynamoDB.", "DynamoDB gibi iki adım.")),
            R(False, ("Operations", "Operasyon"),
              ("The team that owns the cart also owns the search page. It does not want to size instances, run upgrades or tune connection pools for the cart.",
               "Sepetin sahibi olan ekip arama sayfasının da sahibi. Sepet için instance boyutlandırmak, yükseltme yapmak ya da bağlantı havuzlarını ayarlamak istemiyor."),
              ("This is the requirement that decides this race. Aurora is already there, but more load on it is more work for the team that runs it.",
               "Bu yarışı belirleyen gereksinim budur. Aurora zaten orada, ama onun üstüne daha fazla yük, onu çalıştıran ekip için daha fazla iş demektir."),
              ddb=(2, "Serverless, nothing to size.", "Serverless, boyutlandırılacak bir şey yok."),
              aur=(1, "The cart adds load and connections to the order database, which someone must size for the campaign.", "Sepet, sipariş database'ine yük ve bağlantı ekler; birinin onu kampanya için boyutlandırması gerekir."),
              doc=(1, "Instances to size and upgrade.", "Boyutlandırılacak ve yükseltilecek instance'lar."),
              ec=(2, "Serverless.", "Serverless."),
              ks=(2, "Serverless.", "Serverless.")),
        ],
        "gap": ("DynamoDB wins by one point over Aurora. Aurora is better at checkout, because one transaction covers the cart, the stock and the order. DynamoDB is better at abandoned carts and operations, and these count more for a cart that changes often and is often not bought. Keyspaces also has 8 points, but each \"add\" needs a lightweight transaction.",
                "DynamoDB, Aurora'yı bir puan farkla geçer. Aurora checkout'ta daha iyidir, çünkü tek bir transaction sepeti, stoğu ve siparişi kapsar. DynamoDB terk edilen sepetlerde ve operasyonda daha iyidir; sık değişen ve çoğu zaman satın alınmayan bir sepet için bunlar daha çok sayılır. Keyspaces da 8 puan alır, ama her \"ekle\" bir lightweight transaction ister."),
        "pivot": ("Suppose that the team that owns the cart also runs Aurora for the orders, and wants one database less to operate. Then operations would give Aurora ✓ and DynamoDB ~, and Aurora would win.",
                  "Sepetin sahibi olan ekip siparişler için Aurora'yı da çalıştırsaydı ve işletilecek bir database eksik isteseydi operasyon Aurora'ya ✓, DynamoDB'ye ~ verirdi ve Aurora kazanırdı."),
    },
}
DDB_NAMES["ix"] = "Timestream for InfluxDB"


SVC = {"ddb": "DynamoDB", "aur": "Aurora PostgreSQL", "ec": "ElastiCache (Valkey)", "doc": "DocumentDB", "ks": "Keyspaces",
       "rs": "Redshift", "os": "OpenSearch", "ix": "Timestream for InfluxDB", "np": "Neptune", "s3": "S3", "rds": "RDS for PostgreSQL",
       "mdb": "MemoryDB", "ath": "Athena", "efs": "EFS", "dsql": "Aurora DSQL"}
SVC["cas"] = "Apache Cassandra"   # self-managed, on EC2 (Keyspaces card 10)


def scorecard(lang, d):
    """A decision from a spec with service short names (see SVC)."""
    return decide_score(lang, {"workload": d["workload"], "cands": [SVC[c] for c in d["cands"]],
                               "reqs": [_cells(r, SVC) for r in d["reqs"]], "gap": d["gap"], "pivot": d.get("pivot")})


def ddb_decision(lang, key):
    return scorecard(lang, DDB_DECISIONS[key])


from . import e2e_usecases as _uc


def usecase_scorecard(lang, uc):
    """The M7 simulation of a use case card: the same requirements, candidates, scores and reasons as the card."""
    names = [SVC[c] for c in uc["cands"]]
    reqs = []
    for i, r in enumerate(uc["reqs"]):
        cells = {SVC[c]: (uc["scores"][c][i][0],) + tuple(uc["scores"][c][i][1]) for c in uc["cands"]}
        reqs.append({"must": r["must"], "axis": _uc.R_AXES[i], "text": r["want"], "why": r["why"], "cells": cells})
    return decide_score(lang, {"workload": uc["story"], "cands": names, "reqs": reqs, "gap": uc["verdict"], "pivot": None}, scale=10)


def usecases(eid, lang):
    """The M2 cards of a page, localized: the same data as the simulations."""
    out = []
    for uc in _uc.USECASES.get(eid, []):
        L = lambda t: T(lang, *t)  # noqa: E731
        cands = []
        for c in uc["cands"]:
            cells = [{"pts": p, "why": L(w)} for p, w in uc["scores"][c]]
            cands.append({"key": c, "name": SVC[c], "cat": L(_uc.CATEGORY[c]), "link": _uc.LINK[c], "cells": cells,
                          "total": sum(x["pts"] for x in cells), "h2h": L(uc["h2h"][c]) if c in uc["h2h"] else None,
                          "disq": any(r["must"] and x["pts"] <= 1 for r, x in zip(uc["reqs"], cells))})
        out.append({"id": uc["id"], "no": uc["no"], "sim": uc["sim"], "kind": uc["kind"], "title": L(uc["title"]), "key": L(uc["key"]),
                    "story": L(uc["story"]), "axes": [L(a) for a in _uc.R_AXES],
                    "reqs": [{"must": r["must"], "axis": L(_uc.R_AXES[i]), "want": L(r["want"]), "why": L(r["why"])} for i, r in enumerate(uc["reqs"])],
                    "cands": cands, "verdict": L(uc["verdict"])})
    return out


def dynamodb(lang):
    w1 = verdicts(DDB_CANDS, [
        V((1, "on-demand mode scales per request", "on-demand mod istek başına ölçeklenir"), (1, "Serverless v2 scales capacity", "Serverless v2 kapasiteyi ölçekler"),
          (1, "Serverless scales by itself", "Serverless kendi kendine ölçeklenir"), (0, "built for analytic scans", "analitik tarama için yapıldı"),
          (1, "on-demand mode", "on-demand mod")),
        V((1, "each write is stored in several AZs", "her yazma birkaç AZ'de saklanır"), (1, "six copies in three AZs", "üç AZ'de altı kopya"),
          (0, "memory first, not a durable record", "önce bellek, kalıcı kayıt değil"), (1, "durable storage", "kalıcı storage"), (1, "three replicas", "üç replica")),
        V((1, "pay per request, no instance", "istek başına ödeme, instance yok"), (0, "you pay capacity per hour (ACU-hours)", "kapasiteyi saat başına ödersin (ACU-saat)"),
          (1, "pay for data and requests", "veri ve istek başına ödeme"), (0, "compute per hour", "saat başına compute"), (1, "pay per request", "istek başına ödeme")),
        V((1, "only the key is required", "sadece key zorunlu"), (1, "JSONB column", "JSONB column"), (1, "hash fields", "hash alanları"),
          (1, "SUPER type", "SUPER type"), (0, "each column must be in the schema", "her column schema'da olmalı")),
    ])
    w2 = verdicts(DDB_CANDS, [
        V((0, "no JOIN, each question needs a key design", "JOIN yok, her soru bir key tasarımı ister"), (1, "SQL on any column", "her column'da SQL"),
          (0, "access by key only", "sadece key ile erişim"), (1, "SQL", "SQL"), (0, "no JOIN", "JOIN yok")),
        V((1, "many small writes", "çok sayıda küçük yazma"), (1, "OLTP transactions", "OLTP transaction'ları"), (1, "fast writes", "hızlı yazmalar"),
          (0, "not for many small writes", "çok sayıda küçük yazma için değil"), (1, "fast writes", "hızlı yazmalar")),
    ])
    w3 = verdicts(DDB_CANDS, [
        V((1, "TTL attribute", "TTL attribute"), (0, "a cleanup job is necessary", "bir temizlik işi gerekir"), (1, "EXPIRE", "EXPIRE"), (0, "no TTL", "TTL yok"), (1, "TTL on the table or row", "table ya da row TTL'i")),
        V((1, "each write is stored in several AZs", "her yazma birkaç AZ'de saklanır"), (1, "durable", "kalıcı"), (0, "memory first", "önce bellek"), (1, "durable", "kalıcı"), (1, "durable", "kalıcı")),
        V((1, "conditional write on one item", "tek item'da koşullu yazma"), (1, "UNIQUE and transactions", "UNIQUE ve transaction'lar"), (0, "removed earlier", "daha önce elendi"),
          (0, "no enforced keys", "uygulanan key yok"), (1, "lightweight transactions (IF NOT EXISTS)", "lightweight transaction'lar (IF NOT EXISTS)")),
        V((1, "items can have any attributes", "item'lar her attribute'a sahip olabilir"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"),
          (0, "removed earlier", "daha önce elendi"), (0, "each column must be in the schema", "her column schema'da olmalı")),
    ])
    spec = {
        **{k: ddb_decision(lang, k) for k in DDB_DECISIONS},
        **{uc["sim"]: usecase_scorecard(lang, uc) for uc in _uc.DDB_USECASES if uc["sim"]},
        "hash": ddb_hash(lang), "queryscan": ddb_query_scan(lang), "condition": ddb_condition(lang), "gsi": ddb_gsi(lang),
    }
    for v in spec.values():          # key color language: pk yellow, sk blue
        for t in v.get("tables", []):
            if t["cols"][:2] in (["pk", "sk"], ["gsi pk", "gsi sk"]):
                t["pk"], t["sk"] = [0], [1]
    return {k: _localize(v, lang) for k, v in spec.items()}


COUNT_TR.update({"partitions touched": "dokunulan partition", "items read": "okunan item", "items returned": "dönen item",
                 "items read on the base table": "ana table'da okunan item", "items read on the GSI": "GSI'da okunan item", "candidates left": "kalan aday"})
SIMS["dynamodb"] = dynamodb

EXTRA_TABLES["cart"] = CART


# ================================================================ DocumentDB
DOCS = [  # real product documents of Lale Market (subset of fields)
    {"_id": "P0001", "name": "Alpen Kablosuz Kulaklık 1", "category": "Elektronik", "price": 3373.84, "rating": 4.8, "attributes": {"renk": "siyah", "garanti_ay": 12}, "tags": ["hızlı kargo", "çevreci"]},
    {"_id": "P0005", "name": "Toros Güneş Gözlüğü 5", "category": "Moda", "price": 3884.10, "rating": 3.9, "attributes": {"renk": "lacivert", "garanti_ay": 12}, "tags": ["yeni", "çok satan"]},
    {"_id": "P0026", "name": "Bosphorus Mekanik Klavye 26", "category": "Elektronik", "price": 84.61, "rating": 3.0, "attributes": {"renk": "yeşil", "garanti_ay": 24}, "tags": ["yeni", "indirim"]},
    {"_id": "P0044", "name": "Kapadokya Bulut Mimarisi 44", "category": "Kitap", "price": 2651.39, "rating": 3.7, "attributes": {"renk": "siyah", "garanti_ay": 36}, "tags": ["çok satan", "çevreci"]},
    {"_id": "P0095", "name": "Anadolu Yün Kazak 95", "category": "Moda", "price": 2721.65, "rating": 3.3, "attributes": {"renk": "lacivert", "garanti_ay": 36}, "tags": ["yeni", "çevreci"]},
    {"_id": "P0142", "name": "Ege Hava Temizleyici 142", "category": "Ev & Yaşam", "price": 2693.65, "rating": 3.9, "attributes": {"renk": "gri", "garanti_ay": 24}, "tags": ["yeni", "çok satan"]},
    {"_id": "P0179", "name": "Toros Python ile Veri 179", "category": "Kitap", "price": 767.49, "rating": 3.6, "attributes": {"renk": "lacivert", "garanti_ay": 24}, "tags": ["çevreci", "sınırlı"]},
]
DOC_COLS = ["_id", "name", "category", "price", "rating", "attributes.renk", "tags"]


def _flat(d):
    return [d["_id"], d["name"], d["category"], d["price"], d["rating"], d["attributes"]["renk"], ", ".join(d["tags"])]


EXTRA_TABLES["products_docs"] = {"cols": DOC_COLS, "rows": [_flat(d) for d in DOCS]}


def doc_scan(lang):
    rows = [_flat(d) for d in DOCS]
    flt = lambda d: d["category"] == "Elektronik" and d["attributes"]["renk"] == "siyah"
    steps = [{"say": T(lang, "Filter: { category: 'Elektronik', 'attributes.renk': 'siyah' }. With no usable index, DocumentDB examines each document of the collection and tests both conditions.",
                       "Filtre: { category: 'Elektronik', 'attributes.renk': 'siyah' }. Kullanılabilir bir index yoksa DocumentDB collection'daki her document'ı inceler ve iki koşulu da test eder."),
              "marks": {}, "out": [], "count": {"docs examined": 0, "docs returned": 0}}]
    out, m = [], {}
    for i, d in enumerate(DOCS):
        hit = flt(d)
        m = {**{k: ("match" if flt(DOCS[k]) else "skip") for k in m}, i: "match" if hit else "read"}
        if hit:
            out.append([d["_id"], d["name"], d["price"], d["attributes"]["renk"]])
        why = (T(lang, "Both conditions are true, so the document goes to the result.", "İki koşul da doğru, bu yüzden document sonuca gider.") if hit else
               T(lang, "category is '" + d["category"] + "' and attributes.renk is '" + d["attributes"]["renk"] + "'. At least one condition is false.",
                 "category '" + d["category"] + "', attributes.renk '" + d["attributes"]["renk"] + "'. En az bir koşul yanlış."))
        steps.append({"say": T(lang, f"Document {d['_id']}: ", f"Document {d['_id']}: ") + why, "marks": {"d": dict(m)}, "out": deepcopy(out),
                      "outmarks": {len(out) - 1: "new"} if hit else {}, "count": {"docs examined": i + 1, "docs returned": len(out)}})
    steps.append({"say": T(lang, f"COLLSCAN done: {len(DOCS)} documents examined, {len(out)} returned. The projection {{ name: 1, price: 1, 'attributes.renk': 1 }} then sends only these fields.",
                           f"COLLSCAN bitti: {len(DOCS)} document incelendi, {len(out)} döndü. Sonra {{ name: 1, price: 1, 'attributes.renk': 1 }} projection'ı sadece bu alanları gönderir."),
                  "marks": {"d": {k: ("match" if flt(d) else "skip") for k, d in enumerate(DOCS)}}, "out": out, "count": {"docs examined": len(DOCS), "docs returned": len(out)}})
    return {"tables": [{"id": "d", "name": "products (collection)", "cols": DOC_COLS, "rows": rows, "key": [0], "ref": []}],
            "out": {"name": T(lang, "result (after the projection)", "sonuç (projection'dan sonra)"), "cols": ["_id", "name", "price", "attributes.renk"]}, "steps": steps}


def doc_index(lang):
    entries = sorted(((d["category"], -d["rating"], d["_id"]) for d in DOCS))
    idx = [[c, -r, pid] for c, r, pid in entries]
    want = "Kitap"
    steps = [{"say": T(lang, "The compound index { category: 1, rating: -1 } keeps one entry per document: first sorted by category, then by rating from high to low. Each entry points to its document. Query: category 'Kitap', sorted by rating.",
                       "{ category: 1, rating: -1 } compound index'i document başına bir entry tutar: önce category'ye göre, sonra rating'e göre yüksekten düşüğe sıralı. Her entry kendi document'ını gösterir. Query: category 'Kitap', rating'e göre sıralı."),
              "marks": {}, "out": [], "count": {"index entries read": 0, "docs examined": 0}}]
    first = next(i for i, e in enumerate(idx) if e[0] == want)
    steps.append({"say": T(lang, f"IXSCAN: the B-tree goes straight to the first entry with category 'Kitap' (entry {first + 1}). The entries before it are never read.",
                           f"IXSCAN: B-tree doğrudan category değeri 'Kitap' olan ilk entry'ye gider ({first + 1}. entry). Ondan önceki entry'ler hiç okunmaz."),
                  "marks": {"i": {first: "read"}}, "out": [], "count": {"index entries read": 1, "docs examined": 0}})
    out, m, reads = [], {}, 0
    for i in range(first, len(idx)):
        reads += 1
        if idx[i][0] != want:
            m[i] = "skip"
            steps.append({"say": T(lang, f"The next entry has category '{idx[i][0]}'. The range of 'Kitap' is over, so the scan stops.",
                                   f"Sonraki entry'nin category değeri '{idx[i][0]}'. 'Kitap' aralığı bitti, bu yüzden tarama durur."),
                          "marks": {"i": dict(m)}, "out": deepcopy(out), "count": {"index entries read": reads, "docs examined": len(out)}})
            break
        m[i] = "match"
        d = next(x for x in DOCS if x["_id"] == idx[i][2])
        out.append([d["_id"], d["name"], d["rating"]])
        steps.append({"say": T(lang, f"Entry {i + 1}: Kitap, rating {idx[i][1]}, points to {idx[i][2]}. FETCH reads that one document. The order is already right, so no SORT stage is necessary.",
                               f"Entry {i + 1}: Kitap, rating {idx[i][1]}, {idx[i][2]}'yi gösterir. FETCH sadece o document'ı okur. Sıra zaten doğru, bu yüzden SORT aşamasına gerek yok."),
                      "marks": {"i": dict(m), "d": {DOCS.index(d): "match"}}, "out": deepcopy(out), "outmarks": {len(out) - 1: "new"},
                      "count": {"index entries read": reads, "docs examined": len(out)}})
    steps.append({"say": T(lang, f"Done: {len(out)} documents examined for {len(out)} results. A COLLSCAN would examine all {len(DOCS)} documents and then sort the matches in memory.",
                           f"Bitti: {len(out)} sonuç için {len(out)} document incelendi. Bir COLLSCAN {len(DOCS)} document'ın hepsini inceler ve sonra eşleşenleri bellekte sıralardı."),
                  "marks": {"i": dict(m)}, "out": out, "count": {"index entries read": reads, "docs examined": len(out)}})
    return {"tables": [{"id": "i", "name": "index category_1_rating_-1", "cols": ["category", "rating", T(lang, "points to", "gösterdiği")], "rows": idx, "key": [0, 1], "ref": [2]},
                       {"id": "d", "name": "products", "cols": ["_id", "name", "category", "rating"], "rows": [[d["_id"], d["name"], d["category"], d["rating"]] for d in DOCS], "key": [0], "ref": []}],
            "out": {"name": T(lang, "result", "sonuç"), "cols": ["_id", "name", "rating"]}, "steps": steps}


def doc_pipeline(lang):
    unwound, groups, steps = [], {}, []
    steps.append({"say": T(lang, "Pipeline: $unwind '$tags', then $group by tag with a count and an average price. Stage 1 turns each document with two tags into two documents.",
                           "Pipeline: $unwind '$tags', sonra tag'e göre bir sayı ve ortalama fiyatla $group. Aşama 1, iki tag'li her document'ı iki document'a çevirir."),
                  "marks": {}, "rows": {"u": []}, "out": [], "count": {"documents in": 0, "documents after $unwind": 0}})
    for i, d in enumerate(DOCS):
        for t in d["tags"]:
            unwound.append([d["_id"], t, d["price"]])
        steps.append({"say": T(lang, f"$unwind {d['_id']}: tags {d['tags']} becomes {len(d['tags'])} documents, one for each tag.",
                               f"$unwind {d['_id']}: {d['tags']} tag'leri, her tag için bir tane olmak üzere {len(d['tags'])} document olur."),
                      "marks": {"d": {i: "read"}, "u": {len(unwound) - 1: "new", len(unwound) - 2: "new"}}, "rows": {"u": deepcopy(unwound)}, "out": [],
                      "count": {"documents in": i + 1, "documents after $unwind": len(unwound)}})
    for k, (pid, t, price) in enumerate(unwound):
        g = groups.setdefault(t, [0, 0.0])
        g[0] += 1
        g[1] += price
    out = sorted(([t, n, round(s / n, 2)] for t, (n, s) in groups.items()), key=lambda r: (-r[1], r[0]))
    steps.append({"say": T(lang, f"$group: the {len(unwound)} documents go into one group per tag. Each group gives one result: the count and the average price. $sort puts the most common tag first.",
                           f"$group: {len(unwound)} document, tag başına bir gruba girer. Her grup bir sonuç verir: sayı ve ortalama fiyat. $sort en yaygın tag'i öne koyar."),
                  "marks": {}, "rows": {"u": deepcopy(unwound)}, "out": out, "outmarks": {0: "match"},
                  "count": {"documents in": len(DOCS), "documents after $unwind": len(unwound)}})
    return {"tables": [{"id": "d", "name": "products", "cols": ["_id", "tags", "price"], "rows": [[d["_id"], ", ".join(d["tags"]), d["price"]] for d in DOCS], "key": [0], "ref": []},
                       {"id": "u", "name": T(lang, "after $unwind", "$unwind'dan sonra"), "cols": ["_id", "tags", "price"], "rows": [], "key": [], "ref": [0]}],
            "out": {"name": T(lang, "after $group and $sort", "$group ve $sort'tan sonra"), "cols": ["_id (tag)", "products", "avg_price"]}, "steps": steps}


DOC_CANDS = ["DocumentDB", "Aurora PostgreSQL", "DynamoDB", "OpenSearch", "ElastiCache (Valkey)"]


def docdb(lang):
    w1 = verdicts(DOC_CANDS, [
        V((1, "each document has its own fields", "her document'ın kendi alanları var"), (1, "JSONB column, or many tables", "JSONB column ya da birçok table"), (1, "items have free attributes", "item'ların serbest attribute'ları var"),
          (1, "documents with free fields", "serbest alanlı document'lar"), (1, "hash fields", "hash alanları")),
        V((1, "find on any field, also nested", "her alanda find, iç içe olanlar da"), (1, "SQL and JSONB operators", "SQL ve JSONB operatörleri"), (0, "a new question needs a new index design", "yeni soru yeni bir index tasarımı ister"),
          (1, "queries on any field", "her alanda query"), (0, "access by key only", "sadece key ile erişim")),
        V((1, "durable cluster volume", "kalıcı cluster volume"), (1, "durable", "kalıcı"), (0, "removed earlier", "daha önce elendi"),
          (0, "a search index, best as a copy of a source of truth", "bir arama index'i, en iyi bir kaynak verinin kopyası olarak"), (0, "removed earlier", "daha önce elendi")),
        V((1, "the MongoDB API and drivers", "MongoDB API'si ve driver'ları"), (0, "a different API (SQL)", "farklı bir API (SQL)"), (0, "removed earlier", "daha önce elendi"),
          (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
    ])
    w2 = verdicts(DOC_CANDS, [
        V((1, "multi-document transactions", "çok-document'lı transaction'lar"), (1, "transactions", "transaction'lar"), (1, "TransactWriteItems", "TransactWriteItems"),
          (0, "no multi-document transactions", "çok-document'lı transaction yok"), (0, "no rollback", "rollback yok")),
        V((0, "no foreign keys or CHECK across collections", "collection'lar arası foreign key ya da CHECK yok"), (1, "foreign keys, CHECK", "foreign key'ler, CHECK"),
          (0, "no foreign keys", "foreign key yok"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
    ])
    w3 = verdicts(DOC_CANDS, [
        V((0, "one writer instance per cluster (elastic clusters can shard)", "cluster başına tek writer instance (elastic cluster'lar shard'layabilir)"), (0, "one writer instance", "tek writer instance"),
          (1, "partitions spread the writes", "partition'lar yazmaları dağıtır"), (0, "indexing at this rate is expensive", "bu hızda index'leme pahalı"), (1, "fast writes in memory", "bellekte hızlı yazmalar")),
        V((0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (1, "durable in several AZs", "birkaç AZ'de kalıcı"), (0, "removed earlier", "daha önce elendi"),
          (0, "memory first, not a durable record", "önce bellek, kalıcı kayıt değil")),
    ])
    spec = {
        "decide_catalog": decide_generic(lang, ("A product catalog: 200,000 products, each type with different attributes, read and filtered on many fields", "Bir ürün kataloğu: her türün farklı attribute'ları olan 200.000 ürün, birçok alanda okunur ve filtrelenir"),
                                         [("Each item can have its own set of fields", "Her öğenin kendi alan kümesi olabilir"),
                                          ("Filters on any field, also on nested fields, without a new design", "Yeni bir tasarım olmadan her alanda, iç içe alanlarda da filtreler"),
                                          ("It is the source of truth for the catalog", "Kataloğun kaynak verisidir (source of truth)"),
                                          ("The team already writes code for the MongoDB API", "Ekip zaten MongoDB API'si için kod yazıyor")], DOC_CANDS, w1),
        "decide_checkout": decide_generic(lang, ("Checkout: stock, order and order lines change together, with rules between them", "Checkout: stok, sipariş ve order line'lar birlikte değişir, aralarında kurallar var"),
                                          [("Several records change as one all-or-nothing unit", "Birkaç kayıt ya-hep-ya-hiç tek bir birim olarak değişir"),
                                           ("The database enforces rules between collections or tables", "Database collection'lar ya da table'lar arası kuralları uygular")], DOC_CANDS, w2),
        "decide_devices": decide_generic(lang, ("The last state of 5 million IoT devices, one write per device every second", "5 milyon IoT cihazının son durumu, her cihazdan her saniye bir yazma"),
                                         [("About 5 million writes per second, each to its own key", "Saniyede yaklaşık 5 milyon yazma, her biri kendi key'ine"),
                                          ("Each write is durable", "Her yazma kalıcıdır")], DOC_CANDS, w3),
        "scan": doc_scan(lang), "index": doc_index(lang), "pipeline": doc_pipeline(lang),
        "update": doc_update(lang),
        # the Turkish page (templates/e2e/docdb.tr.html): five scorecard simulations built from the M2 cards (e2e_usecases.DOCDB_USECASES)
        **{uc["sim"]: usecase_scorecard(lang, uc) for uc in _uc.DOCDB_USECASES if uc["sim"]},
    }
    return {k: _localize(v, lang) for k, v in spec.items()}


def doc_update(lang):
    """Two devices change the same shopping list document. The filter carries the version (optimistic locking) and
    arrayFilters selects the array element by its value, not by its position."""
    items = [["i1", "süt", False], ["i2", "ekmek", False], ["i3", "elma", False]]
    doc = {"version": 7}
    rows = lambda: [[it[0], it[1], "true" if it[2] else "false", doc["version"]] for it in items]  # noqa: E731
    log = []
    steps = [{"say": T(lang, "The list L1 has three items and version 7. Phone A and tablet B both read version 7. A wants to mark 'ekmek' done, and B wants to mark 'elma' done. Each request sends: filter { _id: 'L1', version: 7 }, update { $set: { 'items.$[i].done': true }, $inc: { version: 1 } }, arrayFilters [ { 'i.name': ... } ].",
                       "L1 listesinin üç öğesi ve version 7 değeri var. Telefon A ve tablet B ikisi de version 7'yi okudu. A 'ekmek' öğesini, B 'elma' öğesini işaretlemek istiyor. Her istek şunu gönderir: filtre { _id: 'L1', version: 7 }, güncelleme { $set: { 'items.$[i].done': true }, $inc: { version: 1 } }, arrayFilters [ { 'i.name': ... } ]."),
              "marks": {}, "out": [], "count": {"writes applied": 0, "writes refused": 0}}]
    # A arrives first
    steps.append({"say": T(lang, "Request A arrives first. The filter tests the document: _id is L1 and version is 7. Both are true, so the document matches.",
                           "Önce A'nın isteği gelir. Filtre document'ı test eder: _id L1 ve version 7. İkisi de doğru, document eşleşti."),
                  "marks": {"l": {0: "read", 1: "read", 2: "read"}}, "rows": {"l": rows()}, "out": [], "count": {"writes applied": 0, "writes refused": 0}})
    items[1][2] = True
    doc["version"] = 8
    log.append(["A", "ekmek", T(lang, "applied, version 7 → 8", "uygulandı, version önce 7, şimdi 8")])
    steps.append({"say": T(lang, "arrayFilters finds the element whose name is 'ekmek' (position 2), without the client knowing the position. $set marks it done and $inc makes the version 8. Both changes are one atomic write of one document.",
                           "arrayFilters adı 'ekmek' olan elemanı bulur (2. sıra); istemci sırayı bilmez. $set onu işaretler, $inc version'ı 8 yapar. İki değişiklik tek document'ın tek atomik yazmasıdır."),
                  "marks": {"l": {1: "new"}}, "rows": {"l": rows()}, "out": deepcopy(log), "outmarks": {0: "new"}, "count": {"writes applied": 1, "writes refused": 0}})
    steps.append({"say": T(lang, "Request B arrives. Its filter still says version: 7. The document now has version 8, so the filter matches no document. matchedCount is 0 and nothing is written.",
                           "B'nin isteği gelir. Filtresi hâlâ version: 7 diyor. Document'ın version değeri artık 8, bu yüzden filtre hiçbir document ile eşleşmez. matchedCount 0 döner ve hiçbir şey yazılmaz."),
                  "marks": {"l": {0: "skip", 1: "skip", 2: "skip"}}, "rows": {"l": rows()},
                  "out": deepcopy(log) + [["B", "elma", T(lang, "refused: matchedCount 0", "reddedildi: matchedCount 0")]], "outmarks": {1: "bad"},
                  "count": {"writes applied": 1, "writes refused": 1}})
    log.append(["B", "elma", T(lang, "refused: matchedCount 0", "reddedildi: matchedCount 0")])
    items[2][2] = True
    doc["version"] = 9
    log.append(["B", "elma", T(lang, "re-read version 8, applied, version 8 → 9", "version 8'i yeniden okudu, uygulandı, version önce 8, şimdi 9")])
    steps.append({"say": T(lang, "Tablet B reads the list again (version 8, 'ekmek' already done), and sends the same change with version: 8. Now it matches, and 'elma' is marked. No change was lost, and no lock was held between the read and the write.",
                           "Tablet B listeyi yeniden okur (version 8, 'ekmek' zaten işaretli) ve aynı değişikliği version: 8 ile gönderir. Şimdi eşleşir ve 'elma' işaretlenir. Hiçbir değişiklik kaybolmadı ve okuma ile yazma arasında kilit tutulmadı."),
                  "marks": {"l": {1: "match", 2: "new"}}, "rows": {"l": rows()}, "out": deepcopy(log), "outmarks": {2: "new"}, "count": {"writes applied": 2, "writes refused": 1}})
    return {"tables": [{"id": "l", "name": T(lang, "lists: document L1, array items", "lists: L1 document'ı, items array'i"), "cols": ["items[].id", "items[].name", "items[].done", "version"],
                        "rows": [[it[0], it[1], "false", 7] for it in [["i1", "süt"], ["i2", "ekmek"], ["i3", "elma"]]], "key": [0], "ref": []}],
            "out": {"name": T(lang, "requests", "istekler"), "cols": [T(lang, "device", "cihaz"), T(lang, "item", "öğe"), T(lang, "result", "sonuç")]}, "steps": steps}


COUNT_TR.update({"docs examined": "incelenen document", "docs returned": "dönen document", "documents in": "giren document", "documents after $unwind": "$unwind sonrası document"})
COUNT_TR.update({"writes applied": "uygulanan yazma"})
SIMS["docdb"] = docdb


# ================================================================ ElastiCache (Valkey)
VKEYS = {"cols": ["key", "type", "value", "TTL (s)"],
         "rows": [["lm:deal", "hash", "product_id=P0001, name=Alpen Kablosuz Kulaklık 1, price=2024.30", "-1"],
                  ["lm:deal:stock", "string", "10", "-1"],
                  ["lm:session:7f3a", "hash", "persona=C00001, last_page=/cart", "1800"],
                  ["lm:leaderboard", "sorted set", "C00002=98210.10, C00004=45120.00, C00001=36708.47", "-1"],
                  ["lm:orders:today", "string", "42", "-1"]]}
EXTRA_TABLES["valkey_keys"] = VKEYS


def vk_race(lang, atomic):
    """Two buyers, 1 piece left. Each step is one command in the single line of Valkey."""
    stock = 1
    rows = lambda: [["lm:deal:stock", stock]]
    log, steps, sold = [], [], 0

    def snap(say, cls, extra="new"):
        steps.append({"say": say, "marks": {"k": {0: cls}}, "rows": {"k": rows()}, "out": deepcopy(log), "outmarks": {len(log) - 1: extra} if log else {},
                      "count": {"pieces sold": sold}})
    snap(T(lang, "One piece is left. Buyer A and buyer B press Buy in the same millisecond. Valkey runs the commands of all clients one after the other, in one line.",
           "Bir adet kaldı. A alıcısı ve B alıcısı aynı milisaniyede Satın al'a basıyor. Valkey bütün istemcilerin komutlarını tek bir sırada, birbiri ardına çalıştırır."), "read")
    if not atomic:
        log.append(["1", "A", "GET lm:deal:stock", "1"]); snap(T(lang, "Command 1: A reads the stock. Valkey answers 1. A decides in its own program that it can sell.", "Komut 1: A stoğu okur. Valkey 1 cevabını verir. A kendi programında satabileceğine karar verir."), "read")
        log.append(["2", "B", "GET lm:deal:stock", "1"]); snap(T(lang, "Command 2: B reads the stock before A writes. Valkey answers 1 again.", "Komut 2: B, A yazmadan önce stoğu okur. Valkey yine 1 cevabını verir."), "read")
        stock = 0; sold += 1
        log.append(["3", "A", "SET lm:deal:stock 0", "OK"]); snap(T(lang, "Command 3: A writes 1 - 1 = 0 and sells the piece.", "Komut 3: A, 1 - 1 = 0 yazar ve adedi satar."), "done")
        sold += 1
        log.append(["4", "B", "SET lm:deal:stock 0", "OK"]); snap(T(lang, "Command 4: B also writes 1 - 1 = 0 and sells. Two pieces left the shop, but it had one. Each command was correct alone. The error is the gap between GET and SET.",
                                                                  "Komut 4: B de 1 - 1 = 0 yazar ve satar. Mağazadan iki adet çıktı ama bir adedi vardı. Her komut tek başına doğruydu. Hata, GET ile SET arasındaki boşluktadır."), "bad", "bad")
    else:
        stock = 0; sold += 1
        log.append(["1", "A", "DECR lm:deal:stock", "0"]); snap(T(lang, "Command 1: A sends DECR. Valkey reads, lowers and stores the value in one command and returns 0. 0 is not below zero, so A sells.",
                                                                  "Komut 1: A, DECR gönderir. Valkey değeri tek komutta okur, düşürür, saklar ve 0 döndürür. 0 sıfırın altında değil, bu yüzden A satar."), "done")
        stock = -1
        log.append(["2", "B", "DECR lm:deal:stock", "-1"]); snap(T(lang, "Command 2: B sends DECR. The value is now -1. B's program sees a value below zero, so it does not sell.",
                                                                   "Komut 2: B, DECR gönderir. Değer artık -1. B'nin programı sıfırın altında bir değer görür, bu yüzden satmaz."), "lock")
        stock = 0
        log.append(["3", "B", "INCR lm:deal:stock", "0"]); snap(T(lang, "Command 3: B gives the piece back with INCR. The stock is 0 again. The shop sold exactly one piece, with no lock.",
                                                                   "Komut 3: B, INCR ile adedi geri verir. Stok yine 0. Mağaza tam olarak bir adet sattı, hiç lock olmadan."), "match", "match")
    return {"tables": [{"id": "k", "name": T(lang, "the key in memory", "bellekteki key"), "cols": ["key", "value"], "rows": [["lm:deal:stock", 1]], "key": [0], "ref": []}],
            "out": {"name": T(lang, "the single line of commands", "komutların tek sırası"), "cols": ["#", T(lang, "client", "istemci"), T(lang, "command", "komut"), T(lang, "reply", "cevap")]},
            "steps": steps}


def vk_zset(lang):
    members = [["C00002", 98210.10], ["C00004", 45120.00], ["C00001", 36708.47], ["C00005", 27300.55], ["C00003", 1599.41]]
    order = lambda: sorted(deepcopy(members), key=lambda r: -r[1])
    steps = [{"say": T(lang, "A teaching copy of the leaderboard (key lm:tut:board, not the real lm:leaderboard) is a sorted set: members (customer ids) with scores (revenue). Valkey keeps the members in score order at each write.",
                       "Liderlik tablosunun öğretici kopyası (key lm:tut:board; gerçek lm:leaderboard'a dokunulmaz) bir sorted set'tir: score'lu (gelir) member'lar (müşteri id'leri). Valkey her yazmada member'ları score sırasıyla tutar."),
              "marks": {}, "rows": {"z": order()}, "out": [], "count": {}}]
    members[4][1] += 20000
    z = order(); pos = next(i for i, r in enumerate(z) if r[0] == "C00003")
    steps.append({"say": T(lang, f"ZINCRBY lm:tut:board 20000 C00003: Elif places an order of 20,000. Her score becomes 21,599.41. Valkey moves her to her new place at once. The cost is O(log N).",
                           f"ZINCRBY lm:tut:board 20000 C00003: Elif 20.000'lik bir sipariş verir. Skoru 21.599,41 olur. Valkey onu hemen yeni yerine taşır. Maliyet O(log N)'dir."),
                  "marks": {"z": {pos: "new"}}, "rows": {"z": z}, "out": [], "count": {}})
    members[3][1] += 30000
    z = order(); pos = next(i for i, r in enumerate(z) if r[0] == "C00005")
    steps.append({"say": T(lang, "ZINCRBY lm:tut:board 30000 C00005: Zeynep jumps from fourth place to second place.", "ZINCRBY lm:tut:board 30000 C00005: Zeynep dördüncü sıradan ikinci sıraya atlar."),
                  "marks": {"z": {pos: "new"}}, "rows": {"z": z}, "out": [], "count": {}})
    steps.append({"say": T(lang, "ZREVRANGE lm:tut:board 0 2 WITHSCORES: the top three are ready. Valkey reads the first three members. It does not sort anything at read time.",
                           "ZREVRANGE lm:tut:board 0 2 WITHSCORES: ilk üç hazır. Valkey ilk üç üyeyi okur. Okuma anında hiçbir şey sıralamaz."),
                  "marks": {"z": {0: "match", 1: "match", 2: "match"}}, "rows": {"z": z}, "out": [[i + 1, r[0], round(r[1], 2)] for i, r in enumerate(z[:3])], "count": {}})
    return {"tables": [{"id": "z", "name": "lm:tut:board (sorted set)", "cols": ["member", "score"], "rows": order(), "key": [0], "ref": []}],
            "out": {"name": "ZREVRANGE 0 2", "cols": ["rank", "member", "score"]}, "steps": steps}


def vk_cache_aside(lang):
    db = [["P0001", "Alpen Kablosuz Kulaklık 1", 3373.84], ["P0044", "Kapadokya Bulut Mimarisi 44", 2651.39], ["P0095", "Anadolu Yün Kazak 95", 2721.65]]
    cache, steps, hits, misses = [], [], 0, 0
    reqs = ["P0001", "P0044", "P0001", "P0001", "P0095", "P0044"]
    steps.append({"say": T(lang, "Cache-aside: the app asks the cache first. On a miss, it reads the database and writes the answer into the cache with a TTL. Six product page views arrive.",
                           "Cache-aside: uygulama önce cache'e sorar. Bir miss'te database'i okur ve cevabı bir TTL ile cache'e yazar. Altı ürün sayfası görüntülemesi geliyor."),
                  "marks": {}, "rows": {"c": []}, "count": {"cache hits": 0, "database reads": 0}})
    for n, pid in enumerate(reqs, start=1):
        ci = next((i for i, r in enumerate(cache) if r[0] == f"product:{pid}"), None)
        if ci is not None:
            hits += 1
            steps.append({"say": T(lang, f"View {n}: GET product:{pid} finds the key in memory (a hit). The database does no work.", f"Görüntüleme {n}: GET product:{pid} key'i bellekte bulur (hit). Database hiç iş yapmaz."),
                          "marks": {"c": {ci: "match"}}, "rows": {"c": deepcopy(cache)}, "count": {"cache hits": hits, "database reads": misses}})
        else:
            misses += 1
            di = next(i for i, r in enumerate(db) if r[0] == pid)
            cache.append([f"product:{pid}", db[di][1], 300])
            steps.append({"say": T(lang, f"View {n}: GET product:{pid} finds nothing (a miss). The app reads the database, then SET product:{pid} ... EX 300 stores a copy for 5 minutes.",
                                   f"Görüntüleme {n}: GET product:{pid} hiçbir şey bulmaz (miss). Uygulama database'i okur, sonra SET product:{pid} ... EX 300 bir kopyayı 5 dakika saklar."),
                          "marks": {"d": {di: "read"}, "c": {len(cache) - 1: "new"}}, "rows": {"c": deepcopy(cache)}, "count": {"cache hits": hits, "database reads": misses}})
    steps.append({"say": T(lang, f"Result: {hits} of {len(reqs)} views came from memory. The database answered only {misses} times. The price: for up to 5 minutes, a changed price can still show the old value.",
                           f"Sonuç: {len(reqs)} görüntülemenin {hits} tanesi bellekten geldi. Database sadece {misses} kez cevap verdi. Bedeli: 5 dakikaya kadar, değişmiş bir fiyat hâlâ eski değeri gösterebilir."),
                  "marks": {}, "rows": {"c": deepcopy(cache)}, "count": {"cache hits": hits, "database reads": misses}})
    return {"tables": [{"id": "d", "name": T(lang, "database (slow, durable)", "database (yavaş, kalıcı)"), "cols": ["product_id", "name", "price"], "rows": db, "key": [0], "ref": []},
                       {"id": "c", "name": T(lang, "cache in memory (fast)", "bellekteki cache (hızlı)"), "cols": ["key", "name", "TTL (s)"], "rows": [], "key": [0], "ref": []}],
            "out": None, "steps": steps}


VK_CANDS = ["ElastiCache (Valkey)", "DynamoDB", "Aurora PostgreSQL", "Redshift", "OpenSearch"]


def _ec_legacy(lang):
    """The three 2/1/0 decisions of the old English page (templates/e2e/elasticache.html) only."""
    w1 = verdicts(VK_CANDS, [
        V((1, "data in memory, microseconds", "veri bellekte, mikrosaniyeler"), (0, "single-digit milliseconds", "tek haneli milisaniyeler"), (0, "milliseconds, disk-based", "milisaniyeler, disk tabanlı"),
          (0, "analytic queries", "analitik query'ler"), (0, "search queries", "arama query'leri")),
        V((1, "sorted set, ZINCRBY", "sorted set, ZINCRBY"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
        V((1, "Seed rebuilds it from the orders", "Seed onu siparişlerden yeniden kurar"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"),
          (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
    ])
    w2 = verdicts(VK_CANDS, [
        V((0, "memory first, not the system of record", "önce bellek, system of record değil"), (1, "durable in several AZs", "birkaç AZ'de kalıcı"), (1, "durable, six copies", "kalıcı, altı kopya"),
          (1, "durable", "kalıcı"), (0, "a copy for search", "arama için bir kopya")),
        V((0, "removed earlier", "daha önce elendi"), (0, "conditions on items, no foreign keys", "item'larda koşullar, foreign key yok"), (1, "transactions and constraints", "transaction'lar ve constraint'ler"),
          (0, "not for many small transactions", "çok sayıda küçük transaction için değil"), (0, "removed earlier", "daha önce elendi")),
    ])
    w3 = verdicts(VK_CANDS, [
        V((1, "INCR with EXPIRE per window", "pencere başına EXPIRE ile INCR"), (1, "atomic ADD with TTL", "TTL ile atomik ADD"), (0, "a row update on each request is heavy", "her istekte bir row güncellemesi ağır"),
          (0, "not for many small writes", "çok sayıda küçük yazma için değil"), (0, "not for counters", "sayaçlar için değil")),
        V((1, "sub-millisecond", "milisaniyenin altında"), (0, "single-digit milliseconds", "tek haneli milisaniyeler"), (0, "removed earlier", "daha önce elendi"),
          (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
    ])
    spec = {
        "decide_board": decide_generic(lang, ("A live leaderboard of the top customers, read every 5 seconds by many screens", "Birçok ekranın her 5 saniyede okuduğu, en iyi müşterilerin canlı leaderboard'u"),
                                       [("Each read in less than one millisecond", "Her okuma bir milisaniyeden kısa"),
                                        ("The top N is ready at every write, with no sort at read time", "İlk N, her yazmada hazır; okuma anında sıralama yok"),
                                        ("The data can be rebuilt from another source", "Veri başka bir kaynaktan yeniden kurulabilir")], VK_CANDS, w1),
        "decide_orders": decide_generic(lang, ("The committed orders of the shop", "Mağazanın commit edilmiş siparişleri"),
                                        [("A confirmed write must never be lost", "Onaylanan bir yazma asla kaybolmamalı"),
                                         ("Rules between orders, lines and stock", "Siparişler, satırlar ve stok arasında kurallar")], VK_CANDS, w2),
        "decide_ratelimit": decide_generic(lang, ("An API rate limit: at most 100 calls per user per minute, checked on every call", "Bir API hız sınırı: kullanıcı başına dakikada en fazla 100 çağrı, her çağrıda kontrol edilir"),
                                           [("An atomic counter per user that resets itself every minute", "Kullanıcı başına, her dakika kendini sıfırlayan atomik bir sayaç"),
                                            ("The check adds less than one millisecond to each call", "Kontrol her çağrıya bir milisaniyeden az ekler")], VK_CANDS, w3),
    }
    return spec




def _slot(key):
    """The real Valkey cluster hash slot: CRC16 (XMODEM) of the key, or of the text inside the first {...}, mod 16384."""
    import binascii
    k = key
    a = key.find("{")
    if a != -1:
        b = key.find("}", a + 1)
        if b > a + 1:
            k = key[a + 1:b]
    return binascii.crc_hqx(k.encode(), 0) % 16384


EC_SHARDS = [(0, 5460), (5461, 10922), (10923, 16383)]   # an even split of the 16,384 slots over three shards


def _shard(slot):
    return next(i for i, (lo, hi) in enumerate(EC_SHARDS) if lo <= slot <= hi)


EC_SLOT_KEYS = ["lm:deal", "lm:deal:stock", "lm:session:7f3a", "lm:session:3c8d", "lm:leaderboard", "lm:orders:today"]
EXTRA_TABLES["valkey_slots"] = {"cols": ["key", "hash slot", "shard"],
                                "rows": [[k, _slot(k), _shard(_slot(k)) + 1] for k in EC_SLOT_KEYS]}


def vk_slots(lang):
    """Six real Lale Market keys go to their hash slots and shards. Then a two-key command fails across slots, and works with a hash tag."""
    rows, steps = [], []
    shards = lambda: [[f"shard {i + 1}", f"{lo}–{hi}", ", ".join(r[0] for r in rows if r[2] == i + 1) or "–"] for i, (lo, hi) in enumerate(EC_SHARDS)]
    steps.append({"say": T(lang, "Cluster mode splits the key space into 16,384 hash slots. Here three shards own one third each. The client calculates CRC16(key) mod 16384 for each key.",
                           "Cluster mode key uzayını 16.384 hash slot'a böler. Burada üç shard her biri üçte birin sahibidir. İstemci her key için CRC16(key) mod 16384 hesaplar."),
                  "marks": {}, "rows": {"k": [], "s": shards()}, "out": [], "count": {"keys placed": 0}})
    for k in EC_SLOT_KEYS:
        sl = _slot(k); sh = _shard(sl) + 1
        rows.append([k, sl, sh])
        steps.append({"say": T(lang, f"{k}: CRC16 mod 16384 = {sl}. Slot {sl} belongs to shard {sh}. Every command on this key goes to shard {sh}.",
                               f"{k}: CRC16 mod 16384 = {sl}. Slot {sl} shard {sh}'in payıdır. Bu key'e giden her komut shard {sh}'e gider."),
                      "marks": {"k": {len(rows) - 1: "new"}, "s": {sh - 1: "read"}}, "rows": {"k": deepcopy(rows), "s": shards()}, "out": [], "count": {"keys placed": len(rows)}})
    a, b = _slot("lm:deal"), _slot("lm:deal:stock")
    steps.append({"say": T(lang, f"MGET lm:deal lm:deal:stock asks for two keys in one command. Their slots are {a} and {b}, so the cluster refuses it with a CROSSSLOT error. Neighbour names are not neighbour slots.",
                           f"MGET lm:deal lm:deal:stock tek komutta iki key ister. Slot'ları {a} ve {b}'dir, bu yüzden cluster komutu CROSSSLOT hatasıyla reddeder. Adları komşu olan key'lerin slot'ları komşu değildir."),
                  "marks": {"k": {0: "bad", 1: "bad"}}, "rows": {"k": deepcopy(rows), "s": shards()},
                  "out": [["MGET lm:deal lm:deal:stock", f"{a}, {b}", "CROSSSLOT"]], "outmarks": {0: "bad"}, "count": {"keys placed": len(rows)}})
    t1, t2 = "{lm:deal}:info", "{lm:deal}:stock"
    s1, s2 = _slot(t1), _slot(t2)
    rows2 = deepcopy(rows) + [[t1, s1, _shard(s1) + 1], [t2, s2, _shard(s2) + 1]]
    steps.append({"say": T(lang, f"With a hash tag, only the text inside the braces is hashed. {t1} and {t2} both hash lm:deal, so both are in slot {s1}, and MGET works. The price: all keys with this tag sit on one shard.",
                           f"Hash tag ile sadece süslü parantezin içindeki metin hash'lenir. {t1} ve {t2} ikisi de lm:deal'i hash'ler, ikisi de slot {s1}'dedir ve MGET çalışır. Bedeli: bu tag'i taşıyan bütün key'ler tek bir shard'da durur."),
                  "marks": {"k": {len(rows2) - 2: "match", len(rows2) - 1: "match"}}, "rows": {"k": rows2, "s": shards()},
                  "out": [["MGET lm:deal lm:deal:stock", f"{a}, {b}", "CROSSSLOT"], [f"MGET {t1} {t2}", f"{s1}, {s2}", "OK"]], "outmarks": {0: "bad", 1: "match"},
                  "count": {"keys placed": len(rows2)}})
    return {"tables": [{"id": "k", "name": T(lang, "keys and their slots", "key'ler ve slot'ları"), "cols": ["key", "hash slot", "shard"], "rows": [], "key": [0], "ref": [], "pk": [0]},
                       {"id": "s", "name": T(lang, "three shards", "üç shard"), "cols": ["shard", "slots", T(lang, "keys", "key'ler")], "rows": shards(), "key": [0], "ref": []}],
            "out": {"name": T(lang, "multi-key commands", "çok key'li komutlar"), "cols": [T(lang, "command", "komut"), "slots", T(lang, "reply", "cevap")]},
            "steps": steps}


def vk_failover(lang):
    """Asynchronous replication: the lock of worker A reaches the primary, A gets OK, the primary fails before the replica has the key."""
    prim = [["lm:deal:stock", "46"], ["lm:orders:today", "42"]]
    repl = deepcopy(prim)
    log, steps = [], []

    def snap(say, pm=None, rm=None, om="new"):
        steps.append({"say": say, "marks": {"p": pm or {}, "r": rm or {}}, "rows": {"p": deepcopy(prim), "r": deepcopy(repl)},
                      "out": deepcopy(log), "outmarks": {len(log) - 1: om} if log else {}, "count": {"lock holders": sum(1 for x in log if x[3] == "OK" and x[2].startswith("SET lock"))}})
    snap(T(lang, "A primary in AZ a and its replica in AZ b. The replica copies the writes of the primary asynchronously: the primary answers OK first and copies later.",
           "AZ a'da bir primary ve AZ b'de onun replica'sı. Replica, primary'nin yazmalarını asenkron kopyalar: primary önce OK der, sonra kopyalar."))
    prim.append(["lock:payout:2026-10-28", "worker-A"])
    log.append(["1", "A", "SET lock:payout:2026-10-28 worker-A NX PX 900000", "OK"])
    snap(T(lang, "Worker A takes the lock of tonight's payout run. The primary writes the key and answers OK at once. A starts to pay the sellers.",
           "Worker A bu gecenin ödeme kilidini alır. Primary key'i yazar ve hemen OK der. A satıcılara ödemeye başlar."), {2: "new"}, None, "match")
    snap(T(lang, "The primary fails before the copy reaches the replica. The replica has the first two keys, but not the lock.",
           "Primary, kopya replica'ya ulaşmadan çöker. Replica'da ilk iki key var, ama kilit yok."), {0: "bad", 1: "bad", 2: "bad"}, None, "match")
    snap(T(lang, "Failover: the service promotes the replica to the new primary within seconds. Clients connect again to the same endpoint. Nobody sees an error.",
           "Failover: servis replica'yı saniyeler içinde yeni primary yapar. İstemciler aynı endpoint'e yeniden bağlanır. Kimse bir hata görmez."), None, {0: "match", 1: "match"}, "match")
    repl.append(["lock:payout:2026-10-28", "worker-B"])
    log.append(["2", "B", "SET lock:payout:2026-10-28 worker-B NX PX 900000", "OK"])
    snap(T(lang, "Worker B tries the lock. On the new primary the key does not exist, so NX succeeds. Two workers now hold the same lock and pay the same sellers twice. Each command was correct. The loss is in the replication gap.",
           "Worker B kilidi dener. Yeni primary'de key yoktur, bu yüzden NX başarılı olur. Artık iki worker aynı kilidi tutar ve aynı satıcılara iki kez ödeme yapar. Her komut doğruydu. Kayıp, kopyalama aralığındadır."),
         None, {2: "bad"}, "bad")
    return {"tables": [{"id": "p", "name": T(lang, "primary (AZ a)", "primary (AZ a)"), "cols": ["key", "value"], "rows": deepcopy(prim[:2]), "key": [0], "ref": []},
                       {"id": "r", "name": T(lang, "replica (AZ b), then the new primary", "replica (AZ b), sonra yeni primary"), "cols": ["key", "value"], "rows": deepcopy(prim[:2]), "key": [0], "ref": []}],
            "out": {"name": T(lang, "commands and replies", "komutlar ve cevaplar"), "cols": ["#", "worker", T(lang, "command", "komut"), T(lang, "reply", "cevap")]},
            "steps": steps}


def elasticache(lang):
    spec = {**{uc["sim"]: usecase_scorecard(lang, uc) for uc in _uc.EC_USECASES if uc["sim"]},
            **_ec_legacy(lang),   # old English page only
            "race_naive": vk_race(lang, False), "race_atomic": vk_race(lang, True), "zset": vk_zset(lang), "cache": vk_cache_aside(lang),
            "slots": vk_slots(lang), "failover": vk_failover(lang)}
    return {k: _localize(v, lang) for k, v in spec.items()}


COUNT_TR.update({"pieces sold": "satılan adet", "cache hits": "cache hit", "database reads": "database okuması",
                 "keys placed": "yerleşen key", "lock holders": "kilidi tutan worker"})
SIMS["elasticache"] = elasticache


# ================================================================ Keyspaces (Apache Cassandra)
ACT = {"cols": ["user_id", "event_time", "event_type", "product_id"],
       "rows": [["C00005", "2026-10-26 16:37", "wishlist", "P0130"], ["C00005", "2026-10-26 16:18", "wishlist", "P0161"],
                ["C00005", "2026-10-26 15:02", "view", "P0095"], ["C00005", "2026-10-25 21:40", "purchase", "P0005"],
                ["C00001", "2026-10-26 12:10", "view", "P0001"], ["C00001", "2026-10-25 09:55", "add_to_cart", "P0044"],
                ["C00006", "2026-10-26 08:30", "view", "P0179"], ["C00006", "2026-10-24 19:05", "purchase", "P0044"]]}
EXTRA_TABLES["activity"] = ACT


def _token(uid, n=3):
    """A small teaching token: the customer number modulo 3. Keyspaces uses its own partitioner (Murmur3 by default)."""
    return int(uid[1:]) % n


def ks_partition(lang):
    nodes = {k: [] for k in range(3)}
    for r in ACT["rows"]:
        nodes[_token(r[0])].append(r[:3])
    for k in nodes:
        nodes[k].sort(key=lambda r: (r[0], r[1]), reverse=False)
        # inside one partition the clustering order is event_time DESC
        by = {}
        for r in nodes[k]:
            by.setdefault(r[0], []).append(r)
        nodes[k] = [r for u in sorted(by) for r in sorted(by[u], key=lambda x: x[1], reverse=True)]
    rows = lambda: {f"n{k}": deepcopy(nodes[k]) for k in range(3)}
    steps = [{"say": T(lang, "The rows are stored by partition. The partition key user_id decides the place: a hash of it (the token) selects the storage. Inside each partition, the rows are already sorted by event_time, newest first.",
                       "Row'lar partition'a göre saklanır. Partition key user_id yeri belirler: onun bir hash'i (token) storage'ı seçer. Her partition'ın içinde row'lar zaten event_time'a göre, en yeni önce sıralıdır."),
              "marks": {}, "rows": rows(), "out": [], "count": {"partitions read": 0, "rows read": 0}}]
    uid = "C00005"
    k = _token(uid)
    part = [i for i, r in enumerate(nodes[k]) if r[0] == uid]
    steps.append({"say": T(lang, f"SELECT ... WHERE user_id = '{uid}' LIMIT 3. The token of {uid} points to storage unit {k}. Keyspaces reads only this partition.",
                           f"SELECT ... WHERE user_id = '{uid}' LIMIT 3. {uid}'in token'ı {k} numaralı storage birimini gösterir. Keyspaces sadece bu partition'ı okur."),
                  "marks": {f"n{k}": {i: "read" for i in part}}, "rows": rows(), "out": [], "count": {"partitions read": 1, "rows read": 0}})
    out = []
    for n, i in enumerate(part[:3], start=1):
        out.append(nodes[k][i])
        steps.append({"say": T(lang, f"Row {n}: {nodes[k][i][1]} {nodes[k][i][2]}. The rows are already newest first, so Keyspaces needs no sort.",
                               f"Row {n}: {nodes[k][i][1]} {nodes[k][i][2]}. Row'lar zaten en yeni önce sıralı, bu yüzden Keyspaces sıralama yapmaz."),
                      "marks": {f"n{k}": {**{j: "match" for j in part[:n]}}}, "rows": rows(), "out": deepcopy(out), "outmarks": {n - 1: "new"},
                      "count": {"partitions read": 1, "rows read": n}})
    steps.append({"say": T(lang, "LIMIT 3 is reached, so the read stops. Two storage units did no work at all. This is the same cost with 1,000 users or 100 million users.",
                           "LIMIT 3'e ulaşıldı, bu yüzden okuma durur. İki storage birimi hiç iş yapmadı. Maliyet 1.000 kullanıcıda da 100 milyon kullanıcıda da aynıdır."),
                  "marks": {f"n{k}": {j: "match" for j in part[:3]}}, "rows": rows(), "out": out, "count": {"partitions read": 1, "rows read": 3}})
    return {"tables": [{"id": f"n{k}", "name": T(lang, f"storage unit {k}", f"storage birimi {k}"), "cols": ["user_id", "event_time ↓", "event_type"], "rows": [], "key": [0, 1], "ref": []} for k in range(3)],
            "out": {"name": T(lang, "result", "sonuç"), "cols": ["user_id", "event_time", "event_type"]}, "steps": steps}


def ks_nokey(lang):
    rows = [r[:3] for r in ACT["rows"]]
    steps = [{"say": T(lang, "SELECT ... WHERE event_type = 'purchase'. This filter does not name a partition key. To answer, the database must look at every partition.",
                       "SELECT ... WHERE event_type = 'purchase'. Bu filtre bir partition key adlandırmaz. Cevaplamak için database'in her partition'a bakması gerekir."),
              "marks": {}, "out": [], "count": {"rows read": 0, "rows returned": 0}}]
    out, m = [], {}
    for i, r in enumerate(rows):
        hit = r[2] == "purchase"
        m = {**{k: ("match" if rows[k][2] == "purchase" else "skip") for k in m}, i: "match" if hit else "read"}
        if hit:
            out.append(r)
        steps.append({"say": T(lang, f"Row {i + 1} of partition {r[0]}: event_type = {r[2]}. " + ("It matches." if hit else "Read and dropped."),
                               f"{r[0]} partition'ının {i + 1}. row'u: event_type = {r[2]}. " + ("Eşleşir." if hit else "Okundu ve atıldı.")),
                      "marks": {"a": dict(m)}, "out": deepcopy(out), "outmarks": {len(out) - 1: "new"} if hit else {}, "count": {"rows read": i + 1, "rows returned": len(out)}})
    steps.append({"say": T(lang, f"{len(rows)} rows read for {len(out)} results. With billions of rows, this read never ends in time. Apache Cassandra refuses such a query unless you add ALLOW FILTERING. The Cassandra way is a second table keyed by event_type.",
                           f"{len(out)} sonuç için {len(rows)} row okundu. Milyarlarca row'da bu okuma zamanında hiç bitmez. Apache Cassandra, ALLOW FILTERING eklemezsen böyle bir query'yi reddeder. Cassandra yolu, event_type ile key'lenmiş ikinci bir table'dır."),
                  "marks": {"a": {k: ("match" if r[2] == "purchase" else "skip") for k, r in enumerate(rows)}}, "out": out, "count": {"rows read": len(rows), "rows returned": len(out)}})
    return {"tables": [{"id": "a", "name": "activity_by_user", "cols": ["user_id", "event_time", "event_type"], "rows": rows, "key": [0, 1], "ref": []}],
            "out": {"name": T(lang, "result", "sonuç"), "cols": ["user_id", "event_time", "event_type"]}, "steps": steps}


def ks_consistency(lang):
    rep = lambda v: [["replica 1 (AZ a)", v[0]], ["replica 2 (AZ b)", v[1]], ["replica 3 (AZ c)", v[2]]]
    vals = ["view P0095", "view P0095", "view P0095"]
    steps = [{"say": T(lang, "The newest event of C00005 is \"view P0095\" in all three replicas. Now a write adds \"purchase P0005\".",
                       "C00005'in en yeni event'i üç replica'nın hepsinde \"view P0095\". Şimdi bir yazma \"purchase P0005\" ekliyor."),
              "marks": {}, "rows": {"r": rep(vals)}, "out": [], "count": {}}]
    vals = ["purchase P0005", "purchase P0005", "view P0095"]
    steps.append({"say": T(lang, "The write uses LOCAL_QUORUM: Keyspaces confirms it when two of the three replicas have it. For a short moment, replica 3 still has the old newest event.",
                           "Yazma LOCAL_QUORUM kullanır: Keyspaces onu üç replica'dan ikisinde olduğunda onaylar. Kısa bir an için replica 3'te hâlâ eski en yeni event vardır."),
                  "marks": {"r": {0: "new", 1: "new", 2: "lock"}}, "rows": {"r": rep(vals)}, "out": [], "count": {}})
    steps.append({"say": T(lang, "A LOCAL_QUORUM read asks two replicas. At least one of any two has the new write, so the read returns \"purchase P0005\". Cost: 1 read unit per 4 KB.",
                           "LOCAL_QUORUM bir okuma iki replica'ya sorar. Herhangi iki replica'dan en az birinde yeni yazma vardır, bu yüzden okuma \"purchase P0005\" döndürür. Maliyet: 4 KB başına 1 read unit."),
                  "marks": {"r": {1: "match", 2: "read"}}, "rows": {"r": rep(vals)}, "out": [["LOCAL_QUORUM", "purchase P0005", "1 RRU"]], "count": {}})
    steps.append({"say": T(lang, "A LOCAL_ONE read asks one replica. If it asks replica 3 in this moment, it returns the old event. The read costs half. The answer can be one moment old.",
                           "LOCAL_ONE bir okuma tek bir replica'ya sorar. Bu anda replica 3'e sorarsa eski event'i döndürür. Okuma yarı maliyetlidir. Cevap bir an eski olabilir."),
                  "marks": {"r": {2: "bad"}}, "rows": {"r": rep(vals)}, "out": [["LOCAL_QUORUM", "purchase P0005", "1 RRU"], ["LOCAL_ONE", "view P0095", "0.5 RRU"]], "outmarks": {1: "bad"}, "count": {}})
    vals = ["purchase P0005"] * 3
    steps.append({"say": T(lang, "A moment later, replica 3 also has the write. All reads return the same answer again.", "Bir an sonra replica 3'te de yazma var. Bütün okumalar yine aynı cevabı döndürür."),
                  "marks": {"r": {2: "match"}}, "rows": {"r": rep(vals)}, "out": [["LOCAL_QUORUM", "purchase P0005", "1 RRU"], ["LOCAL_ONE", "view P0095", "0.5 RRU"]], "count": {}})
    return {"tables": [{"id": "r", "name": T(lang, "the newest event of C00005 in each replica", "her replica'da C00005'in en yeni event'i"), "cols": ["replica", T(lang, "newest event", "en yeni event")], "rows": rep(["view P0095"] * 3), "key": [0], "ref": []}],
            "out": {"name": T(lang, "reads", "okumalar"), "cols": ["consistency", T(lang, "answer", "cevap"), T(lang, "cost per 4 KB", "4 KB başına maliyet")]}, "steps": steps}



def ks_lwt(lang):
    """A lightweight transaction (IF condition) on one cart row: two browser tabs read qty = 2 and race. The rule "at most 5" is checked by the
    application; the IF condition makes sure that the value it checked is still the value in the row."""
    row = [["CART-7f3a", "P0001", 2]]
    log, steps = [], []

    def snap(say, cls, mark="new"):
        steps.append({"say": say, "marks": {"t": {0: cls}}, "rows": {"t": deepcopy(row)}, "out": deepcopy(log),
                      "outmarks": {len(log) - 1: mark} if log else {}, "count": {}})
    snap(T(lang, "The rule: at most 5 pieces of one product in a cart. Two browser tabs read the row at the same moment: both see qty = 2. Tab A wants to add 2, tab B wants to add 3. Each tab checks the rule with the value it read: 2 + 2 = 4 and 2 + 3 = 5, both are allowed.",
           "Kural: bir sepette bir üründen en fazla 5 adet. İki tarayıcı sekmesi row'u aynı anda okur: ikisi de qty = 2 görür. Sekme A 2 eklemek, sekme B 3 eklemek istiyor. Her sekme kuralı okuduğu değerle test eder: 2 + 2 = 4 ve 2 + 3 = 5, ikisi de izinli görünür."), "read")
    row[0][2] = 4
    log.append(["A: UPDATE ... SET qty = 4 IF qty = 2", T(lang, "[applied] = True, qty = 4", "[applied] = True, qty = 4")])
    snap(T(lang, "Tab A sends UPDATE ... SET qty = 4 IF qty = 2. The row still has qty = 2, so the condition is true. Keyspaces tests and writes in one step: qty becomes 4.",
           "Sekme A UPDATE ... SET qty = 4 IF qty = 2 gönderir. Row'da hâlâ qty = 2 var, koşul doğru. Keyspaces tek adımda test eder ve yazar: qty 4 olur."), "match")
    log.append(["B: UPDATE ... SET qty = 5 IF qty = 2", T(lang, "[applied] = False, qty = 4 (no write, 1 WRU)", "[applied] = False, qty = 4 (yazılmadı, 1 WRU)")])
    snap(T(lang, "Tab B sends UPDATE ... SET qty = 5 IF qty = 2. Now qty is 4, so the condition is false. Keyspaces does not write and answers [applied] = False with the current value 4. The refusal still uses a write unit. Without IF, tab B would write 5 and tab A's 2 pieces would be lost.",
           "Sekme B UPDATE ... SET qty = 5 IF qty = 2 gönderir. Artık qty 4, koşul yanlış. Keyspaces yazmaz ve güncel değer 4 ile [applied] = False döndürür. Bu ret de bir yazma birimi harcar. IF olmasaydı sekme B 5 yazardı ve sekme A'nın 2 adedi kaybolurdu."), "bad", "bad")
    snap(T(lang, "Tab B uses the value from the answer: 4 + 3 = 7 is more than 5. The application tells the user \"at most 1 more piece\" and sends nothing. The rule held without a lock in the application.",
           "Sekme B cevaptaki değeri kullanır: 4 + 3 = 7, yani 5'ten fazla. Uygulama kullanıcıya \"en fazla 1 adet daha\" der ve hiçbir şey göndermez. Kural uygulamada bir kilit olmadan korundu."), "match", "bad")
    steps.append({"say": T(lang, "Result: one tab won, the other saw the new value. In Apache Cassandra the same IF runs a Paxos round with extra round trips. Amazon Keyspaces states no extra charge and no performance penalty for LWTs.",
                           "Sonuç: bir sekme kazandı, diğeri yeni değeri gördü. Apache Cassandra'da aynı IF ek gidiş dönüşlü bir Paxos turu çalıştırır; Amazon Keyspaces LWT için ek ücret ve performans cezası olmadığını söyler."),
                  "marks": {"t": {0: "done"}}, "rows": {"t": deepcopy(row)}, "out": deepcopy(log), "count": {}})
    return {"tables": [{"id": "t", "name": T(lang, "the cart row", "sepet row'u"), "cols": ["cart_id", "product_id", "qty"],
                        "rows": [["CART-7f3a", "P0001", 2]], "key": [0, 1], "ref": [], "pk": [0], "sk": [1]}],
            "out": {"name": T(lang, "requests", "istekler"), "cols": ["CQL", T(lang, "answer of Keyspaces", "Keyspaces'in cevabı")]}, "steps": steps}


KS_CANDS = ["Keyspaces", "DynamoDB", "Aurora PostgreSQL", "Timestream for InfluxDB", "ElastiCache (Valkey)"]


def keyspaces(lang):
    w1 = verdicts(KS_CANDS, [
        V((1, "one partition per user, rows sorted by time", "kullanıcı başına bir partition, zamana göre sıralı row'lar"), (1, "partition key + sort key", "partition key + sort key"),
          (1, "index on (user, time)", "(user, time) üzerinde index"), (0, "series of numbers, not event records", "sayı serileri, event kaydı değil"), (1, "sorted set per user", "kullanıcı başına sorted set")),
        V((1, "serverless, writes spread over partitions", "serverless, yazmalar partition'lara dağılır"), (1, "partitions spread the writes", "partition'lar yazmaları dağıtır"),
          (0, "one writer instance", "tek writer instance"), (0, "removed earlier", "daha önce elendi"), (0, "memory is expensive for months of events", "aylarca event için bellek pahalı")),
        V((1, "CQL and Cassandra drivers", "CQL ve Cassandra driver'ları"), (0, "a different API", "farklı bir API"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
    ])
    w2 = verdicts(KS_CANDS, [
        V((0, "no aggregate functions, no JOIN", "aggregate fonksiyon yok, JOIN yok"), (0, "no GROUP BY", "GROUP BY yok"), (1, "SQL with GROUP BY", "GROUP BY'lı SQL"),
          (1, "aggregation by time", "zamana göre aggregation"), (0, "no general queries", "genel query yok")),
        V((0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (1, "JOIN with customers", "customers ile JOIN"), (0, "no JOIN", "JOIN yok"), (0, "removed earlier", "daha önce elendi")),
    ])
    spec = {
        "decide_feed": decide_generic(lang, ("The activity feed of each user: billions of events, \"newest 20 of this user\" on each page", "Her kullanıcının activity feed'i: milyarlarca event, her sayfada \"bu kullanıcının en yeni 20'si\""),
                                      [("Read the newest N events of one user, in time order", "Bir kullanıcının en yeni N event'ini zaman sırasıyla oku"),
                                       ("Millions of writes per hour, growing with the users", "Saatte milyonlarca yazma, kullanıcılarla birlikte büyür"),
                                       ("The team moves an existing Apache Cassandra application", "Ekip mevcut bir Apache Cassandra uygulamasını taşıyor")], KS_CANDS, w1),
        "decide_report": decide_generic(lang, ("A monthly report: purchases per segment and city, from all users", "Aylık bir rapor: bütün kullanıcılardan segment ve şehre göre satın almalar"),
                                        [("GROUP BY over all partitions", "Bütün partition'lar üzerinde GROUP BY"),
                                         ("JOIN with the customer data", "Müşteri verisiyle JOIN")], KS_CANDS, w2),
        "partition": ks_partition(lang), "nokey": ks_nokey(lang), "consistency": ks_consistency(lang), "lwt": ks_lwt(lang),
        # the Turkish page: five scorecard simulations built from the M2 cards (e2e_usecases.KS_USECASES); decide_feed and decide_report
        # above are the legacy 2/1/0 decisions of the old English page only
        **{uc["sim"]: usecase_scorecard(lang, uc) for uc in _uc.KS_USECASES if uc["sim"]},
    }
    for v in spec.values():          # color language of the page: partition key yellow, clustering column blue
        for t in v.get("tables", []):
            if t["cols"][:1] == ["user_id"]:
                t["pk"], t["sk"] = [0], [1]
    return {k: _localize(v, lang) for k, v in spec.items()}


COUNT_TR.update({"partitions read": "okunan partition"})
SIMS["keyspaces"] = keyspaces


# ================================================================ OpenSearch
OS_DOCS = [["P0001", "Alpen Kablosuz Kulaklık 1"], ["P0031", "Alpen Kablosuz Kulaklık 31"], ["P0081", "Kapadokya Kablosuz Kulaklık 81"],
           ["P0016", "Nordwind Powerbank 16"], ["P0044", "Kapadokya Bulut Mimarisi 44"], ["P0175", "Toros Bluetooth Hoparlör 175"]]
EXTRA_TABLES["os_docs"] = {"cols": ["_id", "name"], "rows": OS_DOCS}
_FOLD = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iisSgGuUoOcC")


def _tokens(text, folded):
    out = []
    for w in text.split():
        w = w.lower() if not folded else w.replace("I", "ı").replace("İ", "i").lower().translate(_FOLD)
        out.append(w)
    return out


def os_analyze(lang):
    text = "Alpen Kablosuz Kulaklık 1"
    steps = [{"say": T(lang, f"The text \"{text}\" goes through two analyzers. An analyzer splits the text into words (tokens) and changes each token, for example to lowercase.",
                       f"\"{text}\" metni iki analyzer'dan geçer. Bir analyzer metni kelimelere (token) böler ve her token'ı değiştirir, örneğin küçük harfe çevirir."),
              "marks": {}, "out": [], "count": {}}]
    out = []
    std, fold = _tokens(text, False), _tokens(text, True)
    for i, (a, b) in enumerate(zip(std, fold)):
        out.append([text.split()[i], a, b])
        steps.append({"say": T(lang, f"Word {i + 1}: \"{text.split()[i]}\". The standard analyzer makes \"{a}\". tr_folded makes \"{b}\"" + (". Here the two differ: tr_folded changed ı to i." if a != b else ". Here both are the same."),
                               f"Kelime {i + 1}: \"{text.split()[i]}\". standard analyzer \"{a}\" yapar. tr_folded \"{b}\" yapar" + (". Burada ikisi farklı: tr_folded ı'yı i yaptı." if a != b else ". Burada ikisi aynı.")),
                      "marks": {}, "out": deepcopy(out), "outmarks": {i: "bad" if a != b else "new"}, "count": {}})
    steps.append({"say": T(lang, "Result: the query word \"kulaklik\" (typed without Turkish letters) equals the tr_folded token \"kulaklik\", but not the standard token \"kulaklık\". The analyzer, not the search, decides this.",
                           "Sonuç: Türkçe harfsiz yazılan \"kulaklik\" sorgu kelimesi tr_folded token'ı \"kulaklik\"e eşittir, ama standard token \"kulaklık\"a eşit değildir. Buna arama değil, analyzer karar verir."),
                  "marks": {}, "out": out, "outmarks": {2: "match"}, "count": {}})
    return {"tables": [], "out": {"name": T(lang, "tokens", "token'lar"), "cols": [T(lang, "word", "kelime"), "standard", "tr_folded"]}, "steps": steps}


def os_inverted(lang):
    index = {}
    for pid, name in OS_DOCS:
        for t in _tokens(name, True):
            if not t.isdigit():
                index.setdefault(t, []).append(pid)
    rows = [[t, ", ".join(ids)] for t, ids in sorted(index.items())]
    steps = [{"say": T(lang, "At index time, OpenSearch turned the six product names into tokens. The inverted index lists, for each token, the documents that contain it (the posting list).",
                       "Index zamanında OpenSearch altı ürün adını token'lara çevirdi. Inverted index, her token için onu içeren dokümanları listeler (posting list)."),
              "marks": {}, "out": [], "count": {"tokens looked up": 0, "documents read": 0}}]
    q = ["kablosuz", "kulaklik"]
    score = {}
    for n, t in enumerate(q, start=1):
        ri = next(i for i, r in enumerate(rows) if r[0] == t)
        for pid in index[t]:
            score[pid] = score.get(pid, 0) + 1
        out = sorted(([pid, sc] for pid, sc in score.items()), key=lambda r: (-r[1], r[0]))
        steps.append({"say": T(lang, f"The query \"kablosuz kulaklik\" goes through the same analyzer: token {n} is \"{t}\". OpenSearch looks it up in the sorted index and gets its posting list: {', '.join(index[t])}. It reads no product name.",
                               f"\"kablosuz kulaklik\" sorgusu aynı analyzer'dan geçer: {n}. token \"{t}\". OpenSearch onu sıralı index'te arar ve posting list'ini alır: {', '.join(index[t])}. Hiçbir ürün adı okumaz."),
                      "marks": {"inv": {ri: "match"}}, "out": out, "count": {"tokens looked up": n, "documents read": 0}})
    out = sorted(([pid, sc] for pid, sc in score.items()), key=lambda r: (-r[1], r[0]))
    steps.append({"say": T(lang, f"The documents that contain both tokens get a higher score. The real score is BM25: rare tokens and short fields count more. OpenSearch read {len(q)} index entries, not {len(OS_DOCS)} documents. With 10 million products, it still reads 2 entries.",
                           f"İki token'ı da içeren dokümanlar daha yüksek skor alır. Gerçek skor BM25'tir: nadir token'lar ve kısa alanlar daha çok sayılır. OpenSearch {len(OS_DOCS)} doküman değil, {len(q)} index entry'si okudu. 10 milyon üründe de hâlâ 2 entry okur."),
                  "marks": {"inv": {i: "match" for i, r in enumerate(rows) if r[0] in q}}, "out": out, "outmarks": {0: "new", 1: "new", 2: "new"}, "count": {"tokens looked up": 2, "documents read": 0}})
    return {"tables": [{"id": "inv", "name": T(lang, "inverted index of the field name (tr_folded)", "name alanının inverted index'i (tr_folded)"), "cols": ["token", "posting list"], "rows": rows, "key": [0], "ref": [1]}],
            "out": {"name": T(lang, "matching documents", "eşleşen dokümanlar"), "cols": ["_id", T(lang, "matched tokens", "eşleşen token")]}, "steps": steps}


def _edits(a, b):
    d = [[i + j if i * j == 0 else 0 for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
    return d[-1][-1]


def os_fuzzy(lang):
    q = "kulaklk"
    terms = sorted({t for _, n in OS_DOCS for t in _tokens(n, True) if not t.isdigit()})
    allowed = 2 if len(q) > 5 else (1 if len(q) > 2 else 0)
    steps = [{"say": T(lang, f"The shopper types \"{q}\" (one letter is missing). With fuzziness AUTO, a term of {len(q)} characters may differ by up to {allowed} edits. An edit is one added, removed or changed letter.",
                       f"Alışverişçi \"{q}\" yazıyor (bir harf eksik). Fuzziness AUTO ile {len(q)} karakterlik bir terim en fazla {allowed} edit farklı olabilir. Bir edit, eklenen, silinen ya da değiştirilen tek bir harftir."),
              "marks": {}, "out": [], "count": {"terms compared": 0, "terms accepted": 0}}]
    out, m = [], {}
    for i, t in enumerate(terms):
        e = _edits(q, t)
        ok = e <= allowed
        m = {**{k: ("match" if _edits(q, terms[k]) <= allowed else "skip") for k in m}, i: "match" if ok else "read"}
        if ok:
            out.append([t, e])
        steps.append({"say": T(lang, f"\"{t}\" is {e} edit(s) away from \"{q}\". " + ("This is within the limit, so the term counts as a match." if ok else "This is over the limit."),
                               f"\"{t}\", \"{q}\"dan {e} edit uzaklıkta. " + ("Bu sınırın içinde, bu yüzden terim eşleşme sayılır." if ok else "Bu sınırın dışında.")),
                      "marks": {"t": dict(m)}, "out": deepcopy(out), "outmarks": {len(out) - 1: "new"} if ok else {}, "count": {"terms compared": i + 1, "terms accepted": len(out)}})
    steps.append({"say": T(lang, "Only \"kulaklik\" is close enough. Its posting list gives the three headphones. Without fuzziness, \"kulaklk\" is not in the index, and the search finds nothing. OpenSearch uses an automaton over the index, so it does not compare each term one by one like this simulation.",
                           "Sadece \"kulaklik\" yeterince yakın. Onun posting list'i üç kulaklığı verir. Fuzziness olmadan \"kulaklk\" index'te yoktur ve arama hiçbir şey bulmaz. OpenSearch index üzerinde bir otomat kullanır, bu yüzden bu simülasyon gibi her terimi tek tek karşılaştırmaz."),
                  "marks": {"t": {k: ("match" if _edits(q, x) <= allowed else "skip") for k, x in enumerate(terms)}}, "out": out, "count": {"terms compared": len(terms), "terms accepted": len(out)}})
    return {"tables": [{"id": "t", "name": T(lang, "terms in the index", "index'teki terimler"), "cols": ["term"], "rows": [[t] for t in terms], "key": [0], "ref": []}],
            "out": {"name": T(lang, "accepted terms", "kabul edilen terimler"), "cols": ["term", "edits"]}, "steps": steps}


STORES = [["S001", "İstanbul Mağaza 1", 41.0457, 29.0283], ["S010", "İstanbul Mağaza 2", 41.0612, 28.9341], ["S019", "İstanbul Mağaza 3", 40.9911, 29.1102],
          ["S002", "Ankara Mağaza 1", 39.9334, 32.8597], ["S003", "İzmir Mağaza 1", 38.4237, 27.1428], ["S004", "Bursa Mağaza 1", 40.1885, 29.0610]]


def _km(a, b, c, d):
    import math
    r = 6371.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(h)), 1)


def os_geo(lang):
    here = (41.0082, 28.9784)
    km = 25
    steps = [{"say": T(lang, f"The shopper stands at 41.0082, 28.9784 (central İstanbul). Query: geo_distance {km} km on the field location (type geo_point), sorted by distance.",
                       f"Alışverişçi 41.0082, 28.9784 noktasında (İstanbul merkezi). Query: location alanında (type geo_point) {km} km geo_distance, mesafeye göre sıralı."),
              "marks": {}, "out": [], "count": {"stores in the circle": 0}}]
    out, m = [], {}
    for i, s in enumerate(STORES):
        d = _km(here[0], here[1], s[2], s[3])
        ok = d <= km
        m[i] = "match" if ok else "skip"
        if ok:
            out.append([s[0], s[1], d])
            out.sort(key=lambda r: r[2])
        steps.append({"say": T(lang, f"{s[1]}: {d} km. " + ("Inside the circle." if ok else "Outside the circle."), f"{s[1]}: {d} km. " + ("Dairenin içinde." if ok else "Dairenin dışında.")),
                      "marks": {"s": dict(m)}, "out": deepcopy(out), "count": {"stores in the circle": len(out)}})
    steps.append({"say": T(lang, "The sort by _geo_distance puts the nearest store first. OpenSearch uses a spatial index on the geo_point field, so it does not calculate the distance to every store in a large index.",
                           "_geo_distance'a göre sıralama en yakın mağazayı öne koyar. OpenSearch geo_point alanında bir spatial index kullanır, bu yüzden büyük bir index'te her mağazaya olan mesafeyi hesaplamaz."),
                  "marks": {"s": m}, "out": out, "outmarks": {0: "match"}, "count": {"stores in the circle": len(out)}})
    return {"tables": [{"id": "s", "name": "stores (location: geo_point)", "cols": ["_id", "name", "lat", "lon"], "rows": STORES, "key": [0], "ref": []}],
            "out": {"name": T(lang, "result, nearest first", "sonuç, en yakın önce"), "cols": ["_id", "name", "km"]}, "steps": steps}


OS_CANDS = ["OpenSearch", "Aurora PostgreSQL", "DocumentDB", "DynamoDB", "Redshift"]


def opensearch(lang):
    w1 = verdicts(OS_CANDS, [
        V((1, "analyzers, fuzziness", "analyzer'lar, fuzziness"), (0, "basic text search, no typo tolerance by default", "temel metin araması, varsayılan olarak yazım hatası toleransı yok"),
          (0, "exact filters and basic text index", "kesin filtreler ve temel metin index'i"), (0, "exact key match only", "sadece kesin key eşleşmesi"), (0, "not built for search", "arama için yapılmadı")),
        V((1, "BM25 score", "BM25 skoru"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
        V((1, "aggregations in the same request", "aynı istekte aggregation'lar"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
    ])
    w2 = verdicts(OS_CANDS, [
        V((0, "a search index, best as a copy", "bir arama index'i, en iyi bir kopya olarak"), (1, "durable, ACID", "kalıcı, ACID"), (1, "durable", "kalıcı"), (1, "durable", "kalıcı"), (1, "durable", "kalıcı")),
        V((0, "removed earlier", "daha önce elendi"), (1, "transactions, constraints", "transaction'lar, constraint'ler"), (1, "multi-document transactions", "çok-dokümanlı transaction'lar"),
          (1, "TransactWriteItems", "TransactWriteItems"), (0, "not for many small transactions", "çok sayıda küçük transaction için değil")),
        V((0, "removed earlier", "daha önce elendi"), (1, "foreign keys, CHECK", "foreign key'ler, CHECK"), (0, "no rules between collections", "koleksiyonlar arası kural yok"), (0, "no foreign keys", "foreign key yok"), (0, "removed earlier", "daha önce elendi")),
    ])
    spec = {
        "decide_search": decide_generic(lang, ("The search box of a shop: 200,000 products, typos, Turkish letters, filters by category and price", "Bir mağazanın arama kutusu: 200.000 ürün, yazım hataları, Türkçe harfler, kategori ve fiyat filtreleri"),
                                        [("Match words with typos and without Turkish letters", "Yazım hatalı ve Türkçe harfsiz kelimeleri eşleştir"),
                                         ("Sort the hits by relevance", "Sonuçları relevance'a göre sırala"),
                                         ("Counts per category and price range in the same answer", "Aynı cevapta kategori ve fiyat aralığı başına sayılar")], OS_CANDS, w1),
        "decide_orders": decide_generic(lang, ("The orders of the shop", "Mağazanın siparişleri"),
                                        [("The database is the source of truth", "Database kaynak veridir (source of truth)"),
                                         ("Several records change as one unit", "Birkaç kayıt tek bir birim olarak değişir"),
                                         ("Rules between tables are enforced", "Table'lar arası kurallar uygulanır")], OS_CANDS, w2),
        "analyze": os_analyze(lang), "inverted": os_inverted(lang), "fuzzy": os_fuzzy(lang), "geo": os_geo(lang),
    }
    return {k: _localize(v, lang) for k, v in spec.items()}


COUNT_TR.update({"tokens looked up": "aranan token", "documents read": "okunan doküman", "terms compared": "karşılaştırılan terim", "terms accepted": "kabul edilen terim", "stores in the circle": "dairedeki mağaza"})
SIMS["opensearch"] = opensearch


# ================================================================ Neptune (property graph)
G_CUST = [["C00001", "Ayşe Yılmaz"], ["C00002", "Mert Doğan"], ["C00003", "Elif Kaya"], ["C00005", "Zeynep Şahin"]]
G_PROD = [["P0001", "Alpen Kablosuz Kulaklık 1"], ["P0016", "Nordwind Powerbank 16"], ["P0175", "Toros Bluetooth Hoparlör 175"],
          ["P0044", "Kapadokya Bulut Mimarisi 44"], ["P0179", "Toros Python ile Veri 179"]]
G_EDGES = [["e1", "C00001", "P0001"], ["e2", "C00001", "P0016"], ["e3", "C00002", "P0001"], ["e4", "C00002", "P0016"], ["e5", "C00002", "P0175"],
           ["e6", "C00003", "P0001"], ["e7", "C00003", "P0175"], ["e8", "C00003", "P0044"], ["e9", "C00005", "P0044"], ["e10", "C00005", "P0179"]]
EXTRA_TABLES["g_customers"] = {"cols": ["~id", "name"], "rows": G_CUST}
EXTRA_TABLES["g_products"] = {"cols": ["~id", "name"], "rows": G_PROD}
EXTRA_TABLES["g_bought"] = {"cols": ["~id", "~from", "~to", "~label"], "rows": [e + ["BOUGHT"] for e in G_EDGES]}
G_NAME = dict(G_CUST + G_PROD)


def _gtable(lang):
    return {"id": "e", "name": T(lang, "BOUGHT edges", "BOUGHT edge'leri"), "cols": ["~id", "~from (Customer)", "~to (Product)"], "rows": G_EDGES, "key": [0], "ref": [1, 2]}


def _ein(v):
    return [i for i, e in enumerate(G_EDGES) if e[2] == v]


def _eout(v):
    return [i for i, e in enumerate(G_EDGES) if e[1] == v]


def _ranked(score):
    return [[p, G_NAME[p], len(s)] for p, s in sorted(score.items(), key=lambda kv: (-len(kv[1]), kv[0]))]


def np_hop2(lang):
    start = "P0001"
    m, read = {}, 0
    steps = [{"say": T(lang, f"Question: which products do the buyers of {start} ({G_NAME[start]}) also buy? The graph has 9 vertices and {len(G_EDGES)} BOUGHT edges. Each edge goes from a Customer to a Product.",
                       f"Soru: {start} ({G_NAME[start]}) alıcıları başka hangi ürünleri de alıyor? Graph'ta 9 vertex ve {len(G_EDGES)} BOUGHT edge'i var. Her edge bir Customer'dan bir Product'a gider."),
              "marks": {}, "out": [], "count": {"edges read": 0, "vertices reached": 1}}]
    buyers = []
    for i in _ein(start):
        m[i] = "read"
        buyers.append(G_EDGES[i][1])
    read += len(buyers)
    steps.append({"say": T(lang, f"Hop 1. Neptune starts at the vertex {start} and reads only its incoming BOUGHT edges: {', '.join(G_EDGES[i][0] for i in _ein(start))}. They lead to the customers {', '.join(buyers)}.",
                           f"Hop 1. Neptune {start} vertex'inden başlar ve sadece onun gelen BOUGHT edge'lerini okur: {', '.join(G_EDGES[i][0] for i in _ein(start))}. Bunlar {', '.join(buyers)} müşterilerine götürür."),
                  "marks": {"e": dict(m)}, "out": [], "count": {"edges read": read, "vertices reached": 1 + len(buyers)}})
    score = {}
    for c in buyers:
        new = []
        for i in _eout(c):
            read += 1
            p = G_EDGES[i][2]
            if p == start:
                m[i] = "skip"
            else:
                m[i] = "match"
                score.setdefault(p, set()).add(c)
                new.append(p)
        steps.append({"say": T(lang, f"Hop 2 from {c} ({G_NAME[c]}). Neptune reads the outgoing edges of this customer only. The products other than {start} are {', '.join(new)}. Each of them gets one point for this customer." if len(new) > 1 else f"Hop 2 from {c} ({G_NAME[c]}). Neptune reads the outgoing edges of this customer only. The product other than {start} is {new[0]}. It gets one point for this customer.",
                               f"{c} ({G_NAME[c]}) üzerinden hop 2. Neptune sadece bu müşterinin giden edge'lerini okur. {start} dışındaki ürünler: {', '.join(new)}. Her biri bu müşteri için bir puan alır." if len(new) > 1 else f"{c} ({G_NAME[c]}) üzerinden hop 2. Neptune sadece bu müşterinin giden edge'lerini okur. {start} dışındaki ürün: {new[0]}. Bu müşteri için bir puan alır."),
                      "marks": {"e": dict(m)}, "out": _ranked(score), "count": {"edges read": read, "vertices reached": 1 + len(buyers) + len(score)}})
    steps.append({"say": T(lang, f"Result, ordered by score: the products that the most buyers share come first. Neptune read {read} edges. The edges e9 and e10 of Zeynep Şahin were never read, because no path from {start} reaches her. With 10 million customers, the work still depends only on the neighbours of {start}.",
                           f"Sonuç, score'a göre sıralı: en çok alıcının paylaştığı ürünler önce gelir. Neptune {read} edge okudu. Zeynep Şahin'in e9 ve e10 edge'leri hiç okunmadı, çünkü {start}'den hiçbir yol ona ulaşmaz. 10 milyon müşteride de iş sadece {start}'in komşularına bağlıdır."),
                  "marks": {"e": m}, "out": _ranked(score), "outmarks": {0: "new", 1: "new"}, "count": {"edges read": read, "vertices reached": 1 + len(buyers) + len(score)}})
    return {"tables": [_gtable(lang)], "out": {"name": T(lang, "recommendations", "öneriler"), "cols": ["product_id", "name", "score"]}, "steps": steps}


def np_hop3(lang):
    me = "C00001"
    m, read = {}, 0
    mine = [G_EDGES[i][2] for i in _eout(me)]
    for i in _eout(me):
        m[i] = "read"
    read += len(mine)
    steps = [{"say": T(lang, f"Question: what should {G_NAME[me]} ({me}) buy next? Hop 1 reads her outgoing BOUGHT edges. She bought {', '.join(mine)}.",
                       f"Soru: {G_NAME[me]} ({me}) sırada ne almalı? Hop 1 onun giden BOUGHT edge'lerini okur. {', '.join(mine)} ürünlerini almış."),
              "marks": {"e": dict(m)}, "out": [], "count": {"edges read": read, "similar customers": 0}}]
    others = []
    for p in mine:
        for i in _ein(p):
            c = G_EDGES[i][1]
            read += 1
            if c == me:
                continue
            m[i] = "read"
            if c not in others:
                others.append(c)
    steps.append({"say": T(lang, f"Hop 2. Neptune reads the incoming edges of these products. Other customers who bought the same products: {', '.join(others)}. The query removes {me} herself with WHERE o <> me.",
                           f"Hop 2. Neptune bu ürünlerin gelen edge'lerini okur. Aynı ürünleri alan diğer müşteriler: {', '.join(others)}. Query, WHERE o <> me ile {me}'in kendisini çıkarır."),
                  "marks": {"e": dict(m)}, "out": [], "count": {"edges read": read, "similar customers": len(others)}})
    score = {}
    for c in others:
        kept, dropped = [], []
        for i in _eout(c):
            p = G_EDGES[i][2]
            read += 1
            if p in mine:
                dropped.append(p)
                m[i] = "skip"
            else:
                kept.append(p)
                m[i] = "match"
                score.setdefault(p, set()).add(c)
        steps.append({"say": T(lang, f"Hop 3 from {c} ({G_NAME[c]}). New products: {', '.join(kept)}. " + (f"NOT (me)-[:BOUGHT]->(rec) removes {', '.join(dropped)}, because {G_NAME[me]} already bought " + ('them.' if len(dropped) > 1 else 'it.') if dropped else ""),
                               f"{c} ({G_NAME[c]}) üzerinden hop 3. Yeni ürünler: {', '.join(kept)}. " + (f"NOT (me)-[:BOUGHT]->(rec) filtresi {', '.join(dropped)} " + ('ürünlerini' if len(dropped) > 1 else 'ürününü') + f" çıkarır, çünkü {G_NAME[me]} zaten aldı." if dropped else "")),
                      "marks": {"e": dict(m)}, "out": _ranked(score), "count": {"edges read": read, "similar customers": len(others)}})
    steps.append({"say": T(lang, "The score counts the similar customers who bought each product. This answer is personal, but it needs a purchase history. A new visitor has no edges, so the shop uses the 2-hop query from a product instead.",
                           "Score, her ürünü alan benzer müşterileri sayar. Bu cevap kişiseldir ama bir satın alma geçmişi gerektirir. Yeni bir ziyaretçinin edge'i yoktur, bu yüzden mağaza onun yerine bir üründen başlayan 2-hop query'yi kullanır."),
                  "marks": {"e": m}, "out": _ranked(score), "outmarks": {0: "new"}, "count": {"edges read": read, "similar customers": len(others)}})
    return {"tables": [_gtable(lang)], "out": {"name": T(lang, "recommendations", "öneriler"), "cols": ["product_id", "name", "score"]}, "steps": steps}


def np_path(lang):
    a, b = "C00005", "C00001"
    seen, frontier, parent, m, read = {a}, [a], {}, {}, 0
    steps = [{"say": T(lang, f"Question: how is {G_NAME[a]} ({a}) connected to {G_NAME[b]} ({b})? A fraud team asks this kind of question about shared cards or addresses. The search goes out from {a} one level at a time and treats each edge in both directions.",
                       f"Soru: {G_NAME[a]} ({a}), {G_NAME[b]} ({b}) ile nasıl bağlantılı? Bir dolandırıcılık ekibi ortak kartlar ya da adresler hakkında bu tür bir soru sorar. Arama {a}'dan her seferinde bir seviye dışarı gider ve her edge'i iki yönde de kullanır."),
              "marks": {}, "out": [[0, a, G_NAME[a], "-"]], "count": {"edges read": 0, "levels": 0}}]
    out, level, found = [[0, a, G_NAME[a], "-"]], 0, False
    while frontier and not found:
        level += 1
        nxt, found_now = [], []
        for v in frontier:
            for i, e in enumerate(G_EDGES):
                if v not in (e[1], e[2]):
                    continue
                read += 1
                w = e[2] if e[1] == v else e[1]
                if w in seen:
                    m.setdefault(i, "skip")
                    continue
                seen.add(w)
                parent[w] = (v, e[0])
                m[i] = "read"
                nxt.append(w)
                out.append([level, w, G_NAME[w], e[0]])
                found_now.append(w)
                if w == b:
                    found = True
        steps.append({"say": T(lang, f"Level {level}. From {', '.join(frontier)}, the new vertices are {', '.join(found_now) or 'none'}." + (f" {b} is in this level, so the search stops." if found else ""),
                               f"Seviye {level}. {', '.join(frontier)} vertex'lerinden yeni vertex'ler: {', '.join(found_now) or 'yok'}." + (f" {b} bu seviyede, bu yüzden arama durur." if found else "")),
                      "marks": {"e": dict(m)}, "out": deepcopy(out), "outmarks": {len(out) - 1 - k: "new" for k in range(len(found_now))}, "count": {"edges read": read, "levels": level}})
        frontier = nxt
    path, v = [b], b
    while v != a:
        v = parent[v][0]
        path.append(v)
    path.reverse()
    pm = {i: "match" for i, e in enumerate(G_EDGES) if e[0] in {parent[x][1] for x in path[1:]}}
    steps.append({"say": T(lang, f"The path has {len(path) - 1} hops: {', '.join(path)}. Zeynep and Elif both bought P0044. Elif and Ayşe both bought P0001. In SQL, an unknown number of hops needs a recursive query. In a graph, it is a normal traversal.",
                           f"Yol {len(path) - 1} hop'tur: {', '.join(path)}. Zeynep ve Elif ikisi de P0044 aldı. Elif ve Ayşe ikisi de P0001 aldı. SQL'de bilinmeyen sayıda hop recursive bir query gerektirir. Graph'ta bu normal bir traversal'dır."),
                  "marks": {"e": pm}, "out": [r for r in out if r[1] in path], "count": {"edges read": read, "levels": level}})
    return {"tables": [_gtable(lang)], "out": {"name": T(lang, "vertices reached", "ulaşılan vertex'ler"), "cols": [T(lang, "level", "seviye"), "~id", "name", T(lang, "via edge", "edge")]}, "steps": steps}


NP_CANDS = ["Neptune", "Aurora PostgreSQL", "DynamoDB", "OpenSearch", "Redshift"]


def neptune(lang):
    w1 = verdicts(NP_CANDS, [
        V((1, "vertices and edges", "vertex'ler ve edge'ler"), (1, "tables and foreign keys", "table'lar ve foreign key'ler"), (0, "no joins, relations must be copied", "join yok, ilişkiler kopyalanmalı"),
          (0, "documents do not link", "document'lar birbirine bağlanmaz"), (1, "tables and joins", "table'lar ve join'ler")),
        V((1, "a traversal reads only the neighbours", "bir traversal sadece komşuları okur"), (0, "a variable depth needs recursive SQL, one self-join per hop", "değişken derinlik recursive SQL ister, her hop bir self-join"),
          (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "built for scans, not one visitor per request", "taramalar için yapıldı, istek başına bir ziyaretçi için değil")),
        V((1, "a new edge counts at once", "yeni bir edge hemen sayılır"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
    ])
    w2 = verdicts(NP_CANDS, [
        V((0, "a query starts at vertices; a full scan is slow", "bir query vertex'lerden başlar; tam tarama yavaştır"), (1, "possible", "mümkün"), (0, "Scan of the whole table", "tüm table'ın Scan'i"),
          (1, "aggregations", "aggregation'lar"), (1, "columnar scans", "columnar taramalar")),
        V((0, "removed earlier", "daha önce elendi"), (1, "SQL joins", "SQL join'leri"), (0, "removed earlier", "daha önce elendi"), (0, "no joins between indexes", "index'ler arası join yok"), (1, "SQL joins", "SQL join'leri")),
        V((0, "removed earlier", "daha önce elendi"), (0, "the report competes with checkout", "rapor checkout ile yarışır"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (1, "a separate warehouse", "ayrı bir warehouse")),
    ])
    spec = {
        "decide_recs": decide_generic(lang, ("\"Customers who bought this also bought\" on every product page", "Her ürün sayfasında \"bunu alanlar şunları da aldı\""),
                                      [("Store entities and the relations between them", "Varlıkları ve aralarındaki ilişkileri sakla"),
                                       ("Follow 2 to 4 hops in milliseconds for each request", "Her istekte 2-4 hop'u milisaniyelerde takip et"),
                                       ("A new purchase changes the answer at once", "Yeni bir satın alma cevabı hemen değiştirir")], NP_CANDS, w1),
        "decide_report": decide_generic(lang, ("Monthly revenue by category over two years of orders", "İki yıllık siparişler üzerinde kategoriye göre aylık gelir"),
                                        [("Scan millions of rows and sum columns", "Milyonlarca row'u tara ve kolonları topla"),
                                         ("Join facts and dimensions with SQL", "Fact'leri ve dimension'ları SQL ile join'le"),
                                         ("Do not slow the checkout database", "Checkout database'ini yavaşlatma")], NP_CANDS, w2),
        "hop2": np_hop2(lang), "hop3": np_hop3(lang), "path": np_path(lang),
    }
    return {k: _localize(v, lang) for k, v in spec.items()}


COUNT_TR.update({"edges read": "okunan edge", "vertices reached": "ulaşılan vertex", "similar customers": "benzer müşteri", "levels": "seviye"})
SIMS["neptune"] = neptune


# ================================================================ Redshift (columnar warehouse)
RS_COLS = ["order_id", "order_date", "customer_id", "city", "category", "product_id", "qty", "amount"]
RS_ROWS = [["O000003", "2026-01-05", "C00001", "İstanbul", "Spor", "P0178", 3, 2635.86],
           ["O000054", "2026-01-19", "C00004", "Frankfurt", "Kitap", "P0134", 3, 9188.34],
           ["O000025", "2026-02-02", "C00001", "İstanbul", "Elektronik", "P0161", 1, 2678.72],
           ["O000061", "2026-02-21", "C00002", "Ankara", "Kitap", "P0034", 2, 4009.92],
           ["O000027", "2026-03-04", "C00001", "İstanbul", "Elektronik", "P0176", 3, 2832.03],
           ["O000070", "2026-03-17", "C00003", "İzmir", "Moda", "P0045", 3, 7842.36],
           ["O000004", "2026-04-04", "C00004", "Frankfurt", "Elektronik", "P0106", 3, 14649.69],
           ["O000082", "2026-04-22", "C00002", "Ankara", "Ev & Yaşam", "P0157", 1, 836.15]]
EXTRA_TABLES["rs_sales"] = {"cols": RS_COLS, "rows": RS_ROWS}


def _cat_sums(rows):
    s = {}
    for r in rows:
        s[r[4]] = round(s.get(r[4], 0) + r[7], 2)
    return [[k, v] for k, v in sorted(s.items(), key=lambda kv: -kv[1])]


def rs_rowcol(lang):
    per = 2
    blocks = [RS_ROWS[i:i + per] for i in range(0, len(RS_ROWS), per)]
    rowt = [[f"R{n + 1}", " | ".join(str(v) for v in b[0]), " | ".join(str(v) for v in b[1])] for n, b in enumerate(blocks)]
    colt = [[c, ", ".join(str(r[i]) for r in RS_ROWS)] for i, c in enumerate(RS_COLS)]
    need = [RS_COLS.index("category"), RS_COLS.index("amount")]
    steps = [{"say": T(lang, f"Query: SELECT category, sum(amount) FROM sales GROUP BY category. It needs 2 of the {len(RS_COLS)} columns. The same {len(RS_ROWS)} rows are stored twice: by row (first table) and by column (second table).",
                       f"Query: SELECT category, sum(amount) FROM sales GROUP BY category. {len(RS_COLS)} kolonun 2'sine ihtiyaç duyar. Aynı {len(RS_ROWS)} row iki kez saklanır: row'a göre (birinci table) ve kolona göre (ikinci table)."),
              "marks": {}, "out": [], "count": {"values read (row store)": 0, "values read (column store)": 0}}]
    m, vr = {}, 0
    for n, b in enumerate(blocks):
        m[n] = "read"
        vr += len(b) * len(RS_COLS)
        steps.append({"say": T(lang, f"Row store: block R{n + 1} holds complete rows. To get category and amount, the database reads the whole block, also the {len(RS_COLS) - 2} columns that the query does not need.",
                               f"Row store: R{n + 1} bloğu tam row'lar tutar. category ve amount'u almak için database bütün bloğu okur, query'nin ihtiyaç duymadığı {len(RS_COLS) - 2} kolonu da."),
                      "marks": {"rowt": dict(m)}, "out": [], "count": {"values read (row store)": vr, "values read (column store)": 0}})
    vc, cm = 0, {}
    for i in need:
        cm[i] = "match"
        vc += len(RS_ROWS)
        steps.append({"say": T(lang, f"Column store: the block of the column {RS_COLS[i]} holds only its {len(RS_ROWS)} values. The database reads this block.",
                               f"Column store: {RS_COLS[i]} kolonunun bloğu sadece onun {len(RS_ROWS)} değerini tutar. Database bu bloğu okur."),
                      "marks": {"rowt": {k: "read" for k in range(len(blocks))}, "colt": dict(cm)}, "out": _cat_sums(RS_ROWS) if len(cm) == 2 else [],
                      "count": {"values read (row store)": vr, "values read (column store)": vc}})
    steps.append({"say": T(lang, f"Same result, but the column store read {vc} values and the row store read {vr}. The other {len(RS_COLS) - 2} column blocks stayed on disk. A column holds similar values, so it also compresses well. With 100 columns and a query that needs 3, the difference is much larger.",
                           f"Sonuç aynı, ama column store {vc} değer, row store {vr} değer okudu. Diğer {len(RS_COLS) - 2} kolon bloğu diskte kaldı. Bir kolon benzer değerler tutar, bu yüzden iyi de sıkışır. 100 kolon ve 3 kolona ihtiyaç duyan bir query'de fark çok daha büyüktür."),
                  "marks": {"rowt": {k: "read" for k in range(len(blocks))}, "colt": {k: ("match" if k in need else "skip") for k in range(len(RS_COLS))}},
                  "out": _cat_sums(RS_ROWS), "count": {"values read (row store)": vr, "values read (column store)": vc}})
    return {"tables": [{"id": "rowt", "name": T(lang, "row store: one block = 2 complete rows", "row store: bir blok = 2 tam row"), "cols": [T(lang, "block", "blok"), T(lang, "row 1", "row 1"), T(lang, "row 2", "row 2")], "rows": rowt, "key": [0], "ref": []},
                       {"id": "colt", "name": T(lang, "column store: one block = one column", "column store: bir blok = bir kolon"), "cols": [T(lang, "column", "kolon"), T(lang, "values", "değerler")], "rows": colt, "key": [0], "ref": []}],
            "out": {"name": T(lang, "result", "sonuç"), "cols": ["category", "sum(amount)"]}, "steps": steps}


RS_BLOCKS_SORTED = [["B1", "2026-01-01", "2026-01-31"], ["B2", "2026-02-01", "2026-02-28"], ["B3", "2026-03-01", "2026-03-31"],
                    ["B4", "2026-04-01", "2026-04-30"], ["B5", "2026-05-01", "2026-05-31"], ["B6", "2026-06-01", "2026-06-30"]]
RS_BLOCKS_UNSORTED = [["U1", "2026-01-03", "2026-06-27"], ["U2", "2026-01-09", "2026-06-12"], ["U3", "2026-02-14", "2026-05-30"],
                      ["U4", "2026-01-21", "2026-06-30"], ["U5", "2026-01-01", "2026-04-18"], ["U6", "2026-02-02", "2026-06-05"]]


def rs_zonemap(lang):
    lo, hi = "2026-03-01", "2026-03-31"
    steps = [{"say": T(lang, f"Query: ... WHERE order_date BETWEEN '{lo}' AND '{hi}'. For each 1 MB block, Redshift keeps the smallest and the largest value (the zone map). It compares the range with the zone map before it reads a block.",
                       f"Query: ... WHERE order_date BETWEEN '{lo}' AND '{hi}'. Redshift her 1 MB'lık blok için en küçük ve en büyük değeri tutar (zone map). Bir bloğu okumadan önce aralığı zone map ile karşılaştırır."),
              "marks": {}, "out": [], "count": {"blocks read (sorted)": 0, "blocks read (unsorted)": 0}}]
    out = []
    res = {}
    for tid, blocks in (("srt", RS_BLOCKS_SORTED), ("uns", RS_BLOCKS_UNSORTED)):
        m, n = {}, 0
        for i, b in enumerate(blocks):
            hit = not (b[2] < lo or b[1] > hi)
            m[i] = "read" if hit else "skip"
            n += hit
        res[tid] = (m, n)
    ms, ns = res["srt"]
    steps.append({"say": T(lang, f"Sorted table (SORTKEY order_date): the blocks hold separate date ranges. Only block B3 can contain March. Redshift skips the other {len(RS_BLOCKS_SORTED) - ns} blocks without reading them.",
                           f"Sıralı table (SORTKEY order_date): bloklar ayrı tarih aralıkları tutar. Sadece B3 bloğu Mart'ı içerebilir. Redshift diğer {len(RS_BLOCKS_SORTED) - ns} bloğu okumadan atlar."),
                  "marks": {"srt": ms}, "out": [], "count": {"blocks read (sorted)": ns, "blocks read (unsorted)": 0}})
    mu, nu = res["uns"]
    steps.append({"say": T(lang, f"Unsorted table: each block holds dates from many months, so each range overlaps March. The zone map cannot exclude any of them: {nu} of {len(RS_BLOCKS_UNSORTED)} blocks must be read.",
                           f"Sırasız table: her blok birçok aydan tarih tutar, bu yüzden her aralık Mart ile çakışır. Zone map hiçbirini dışarıda bırakamaz: {len(RS_BLOCKS_UNSORTED)} bloğun {nu}'sı okunmalıdır."),
                  "marks": {"srt": ms, "uns": mu}, "out": [], "count": {"blocks read (sorted)": ns, "blocks read (unsorted)": nu}})
    steps.append({"say": T(lang, "The sort key decides the order of the rows on disk. A good sort key is the column that most queries filter on with a range, often a date. The AWS guide says: if recent data is queried most often, make the timestamp column the leading sort key column.",
                           "Sort key, row'ların diskteki sırasına karar verir. İyi bir sort key, çoğu query'nin bir aralıkla filtrelediği kolondur, çoğunlukla bir tarih. AWS kılavuzu şöyle der: en sık yeni veri sorgulanıyorsa timestamp kolonunu sort key'in ilk kolonu yap."),
                  "marks": {"srt": ms, "uns": mu}, "out": [], "count": {"blocks read (sorted)": ns, "blocks read (unsorted)": nu}})
    return {"tables": [{"id": "srt", "name": T(lang, "sorted by order_date: zone map", "order_date'e göre sıralı: zone map"), "cols": [T(lang, "block", "blok"), "min", "max"], "rows": RS_BLOCKS_SORTED, "key": [0], "ref": []},
                       {"id": "uns", "name": T(lang, "unsorted: zone map", "sırasız: zone map"), "cols": [T(lang, "block", "blok"), "min", "max"], "rows": RS_BLOCKS_UNSORTED, "key": [0], "ref": []}],
            "out": {"name": T(lang, "result", "sonuç"), "cols": ["-"]}, "steps": steps}


def _slice(cid):
    """A small teaching hash: the customer number modulo 2. Redshift uses its own hash function."""
    return int(cid[1:]) % 2


def rs_dist(lang):
    rows = [[r[0], r[2], r[7]] for r in RS_ROWS]
    key = {0: [], 1: []}
    for r in rows:
        key[_slice(r[1])].append(r)
    even = {0: rows[0::2], 1: rows[1::2]}
    cust = {0: [c for c in ("C00002", "C00004")], 1: [c for c in ("C00001", "C00003")]}

    def tabs(d):
        return {"s0": deepcopy(d[0]), "s1": deepcopy(d[1])}

    steps = [{"say": T(lang, "Redshift splits each table across slices (parts of the compute nodes) and runs a query on all slices in parallel. The table customers is distributed by customer_id: slice 0 holds C00002 and C00004, slice 1 holds C00001 and C00003.",
                       "Redshift her table'ı slice'lara (compute node'larının parçaları) böler ve bir query'yi bütün slice'larda paralel çalıştırır. customers table'ı customer_id'ye göre dağıtılmıştır: slice 0 C00002 ve C00004'ü, slice 1 C00001 ve C00003'ü tutar."),
              "marks": {}, "rows": tabs({0: [], 1: []}), "out": [], "count": {"rows moved": 0}}]
    steps.append({"say": T(lang, "DISTSTYLE KEY, DISTKEY customer_id: each sales row goes to the slice of its customer_id. The teaching hash here is the customer number modulo 2.",
                           "DISTSTYLE KEY, DISTKEY customer_id: her sales row'u kendi customer_id'sinin slice'ına gider. Buradaki öğretici hash, müşteri numarasının 2'ye göre modudur."),
                  "marks": {}, "rows": tabs(key), "out": [], "count": {"rows moved": 0}})
    steps.append({"say": T(lang, "JOIN customers ON customer_id: on each slice, every sales row finds its customer on the same slice. No row moves between slices. The AWS guide calls this collocation.",
                           "JOIN customers ON customer_id: her slice'ta her sales row'u kendi müşterisini aynı slice'ta bulur. Hiçbir row slice'lar arasında taşınmaz. AWS kılavuzu buna collocation der."),
                  "marks": {"s0": {i: "match" for i in range(len(key[0]))}, "s1": {i: "match" for i in range(len(key[1]))}}, "rows": tabs(key), "out": [], "count": {"rows moved": 0}})
    steps.append({"say": T(lang, "DISTSTYLE EVEN: the rows go to the slices in turn (round robin), with no regard to the customer. The slices hold the same number of rows, but the customer of a row is often on the other slice.",
                           "DISTSTYLE EVEN: row'lar müşteriye bakılmadan sırayla (round robin) slice'lara gider. Slice'lar aynı sayıda row tutar, ama bir row'un müşterisi çoğunlukla diğer slice'tadır."),
                  "marks": {}, "rows": tabs(even), "out": [], "count": {"rows moved": 0}})
    moved, mk = 0, {"s0": {}, "s1": {}}
    for s in (0, 1):
        for i, r in enumerate(even[s]):
            ok = r[1] in cust[s]
            mk[f"s{s}"][i] = "match" if ok else "bad"
            moved += 0 if ok else 1
    steps.append({"say": T(lang, f"The same join with EVEN: {moved} of {len(rows)} sales rows have their customer on the other slice. Redshift must send these rows over the network before the join (redistribution).",
                           f"EVEN ile aynı join: {len(rows)} sales row'unun {moved}'inin müşterisi diğer slice'tadır. Redshift bu row'ları join'den önce ağ üzerinden göndermelidir (redistribution)."),
                  "marks": mk, "rows": tabs(even), "out": [], "count": {"rows moved": moved}})
    steps.append({"say": T(lang, "Rule of the guide: distribute the fact table and its largest joined dimension on their common column. A small dimension can use ALL, a copy on every node. With AUTO, Redshift chooses and changes the style itself.",
                           "Kılavuzun kuralı: fact table'ı ve en büyük join'lenen dimension'ını ortak kolonlarına göre dağıt. Küçük bir dimension ALL kullanabilir, yani her node'da bir kopya. AUTO ile stili Redshift kendisi seçer ve değiştirir."),
                  "marks": mk, "rows": tabs(even), "out": [], "count": {"rows moved": moved}})
    cols = ["order_id", "customer_id", "amount"]
    return {"tables": [{"id": "s0", "name": "slice 0 (customers: C00002, C00004)", "cols": cols, "rows": [], "key": [0], "ref": [1]},
                       {"id": "s1", "name": "slice 1 (customers: C00001, C00003)", "cols": cols, "rows": [], "key": [0], "ref": [1]}],
            "out": {"name": T(lang, "result", "sonuç"), "cols": ["-"]}, "steps": steps}


RS_CANDS = ["Redshift", "Aurora PostgreSQL", "DynamoDB", "OpenSearch", "Neptune"]


def redshift(lang):
    w1 = verdicts(RS_CANDS, [
        V((1, "SQL with joins", "join'li SQL"), (1, "SQL with joins", "join'li SQL"), (0, "no joins", "join yok"), (0, "no joins between indexes", "index'ler arası join yok"), (0, "graph queries, not table joins", "graph query'leri, table join'leri değil")),
        V((1, "columnar, reads only the needed columns, in parallel", "columnar, sadece gereken kolonları paralel okur"), (0, "row storage reads whole rows", "row storage bütün row'ları okur"),
          (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
        V((1, "a separate warehouse, fed by zero-ETL", "zero-ETL ile beslenen ayrı bir warehouse"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
    ])
    w2 = verdicts(RS_CANDS, [
        V((0, "built for large loads and scans, not one small insert per click", "büyük yüklemeler ve taramalar için yapıldı, tıklama başına küçük insert için değil"), (1, "OLTP", "OLTP"), (1, "single-digit ms writes", "tek haneli ms yazmalar"),
          (0, "a search copy, not the source", "bir arama kopyası, kaynak değil"), (1, "transactional writes", "transactional yazmalar")),
        V((0, "removed earlier", "daha önce elendi"), (1, "ACID transactions", "ACID transaction'lar"), (1, "TransactWriteItems", "TransactWriteItems"), (0, "removed earlier", "daha önce elendi"), (1, "ACID transactions", "ACID transaction'lar")),
        V((0, "removed earlier", "daha önce elendi"), (1, "foreign keys, CHECK", "foreign key'ler, CHECK"), (0, "no foreign keys", "foreign key yok"), (0, "removed earlier", "daha önce elendi"), (0, "no foreign keys or CHECK", "foreign key ya da CHECK yok")),
    ])
    spec = {
        "decide_report": decide_generic(lang, ("Monthly revenue by category and city over two years of orders, for the analysts", "Analistler için iki yıllık siparişler üzerinde kategori ve şehre göre aylık gelir"),
                                        [("SQL with joins of facts and dimensions", "Fact ve dimension'ların join'li SQL'i"),
                                         ("Scan hundreds of millions of rows in seconds", "Yüz milyonlarca row'u saniyelerde tara"),
                                         ("Do not slow the checkout database", "Checkout database'ini yavaşlatma")], RS_CANDS, w1),
        "decide_checkout": decide_generic(lang, ("Write one order per checkout, thousands per second", "Her checkout'ta bir sipariş yaz, saniyede binlerce"),
                                          [("Many small writes with low latency", "Düşük gecikmeli çok sayıda küçük yazma"),
                                           ("Several rows change as one unit", "Birkaç row tek bir birim olarak değişir"),
                                           ("Rules between tables (foreign keys, CHECK)", "Table'lar arası kurallar (foreign key, CHECK)")], RS_CANDS, w2),
        "rowcol": rs_rowcol(lang), "zonemap": rs_zonemap(lang), "dist": rs_dist(lang),
    }
    return {k: _localize(v, lang) for k, v in spec.items()}


COUNT_TR.update({"values read (row store)": "okunan değer (row store)", "values read (column store)": "okunan değer (column store)",
                 "blocks read (sorted)": "okunan blok (sıralı)", "blocks read (unsorted)": "okunan blok (sırasız)", "rows moved": "taşınan row"})
SIMS["redshift"] = redshift


# ================================================================ Timestream for InfluxDB (time series)
IX_LINES = ["warehouse_env,warehouse=IST-1,sensor=temperature value=21.2 1793433600",
            "warehouse_env,warehouse=IST-1,sensor=humidity value=44.8 1793433600",
            "warehouse_env,warehouse=ANK-1,sensor=temperature value=19.6 1793433600",
            "orders,channel=web count=14i 1793433600",
            "warehouse_env,warehouse=IST-1,sensor=temperature value=21.4 1793433900",
            "orders,channel=web count=11i 1793433660"]
IX_RAW = [["10:00", 21.2], ["10:05", 21.4], ["10:10", 21.9], ["10:15", 22.3], ["10:20", 22.8], ["10:25", 23.1], ["10:30", 22.6], ["10:35", 22.0], ["10:40", 21.7]]
EXTRA_TABLES["ix_lines"] = {"cols": ["line protocol"], "rows": [[x] for x in IX_LINES]}
EXTRA_TABLES["ix_raw"] = {"cols": ["_time", "_value"], "rows": IX_RAW}


def _parse_line(line):
    head, fields, ts = line.split(" ")
    parts = head.split(",")
    meas, tags = parts[0], parts[1:]
    fk = fields.split("=")[0]
    return meas, ",".join(tags), fields, ts, f"{meas},{','.join(tags)} {fk}"


def ix_series(lang):
    rows = [[x] for x in IX_LINES]
    steps = [{"say": T(lang, "Each line of line protocol is one point: measurement, tags, fields and a timestamp. The measurement, the tag set and the field key together form the series key. InfluxDB stores the points of one series together, in time order.",
                       "Line protocol'ün her satırı bir point'tir: measurement, tag'ler, field'lar ve bir timestamp. Measurement, tag set ve field key birlikte series key'i oluşturur. InfluxDB bir series'in point'lerini zaman sırasıyla bir arada saklar."),
              "marks": {}, "out": [], "count": {"points": 0, "series": 0}}]
    series, out = [], []
    for i, line in enumerate(IX_LINES):
        meas, tags, fields, ts, key = _parse_line(line)
        new = key not in series
        if new:
            series.append(key)
            out.append([key, 1])
        else:
            out[series.index(key)][1] += 1
        steps.append({"say": T(lang, f"Point {i + 1}: measurement {meas}, tags {tags}, field {fields}, time {ts}. " + ("This is a new series." if new else "This series exists already, so the point goes to the end of it."),
                               f"Point {i + 1}: measurement {meas}, tag'ler {tags}, field {fields}, zaman {ts}. " + ("Bu yeni bir series'tir." if new else "Bu series zaten var, bu yüzden point onun sonuna eklenir.")),
                      "marks": {"l": {k: ("match" if k == i else "read") for k in range(i + 1)}}, "out": deepcopy(out), "outmarks": {series.index(key): "new"},
                      "count": {"points": i + 1, "series": len(series)}})
    steps.append({"say": T(lang, f"{len(IX_LINES)} points, {len(series)} series. The number of series is the cardinality. Tags are indexed, so each new tag value can create new series. Put values with few possible values in tags (warehouse, sensor). Put measured numbers in fields. Never put a customer id or a request id in a tag.",
                           f"{len(IX_LINES)} point, {len(series)} series. Series sayısı cardinality'dir. Tag'ler index'lenir, bu yüzden her yeni tag değeri yeni series'ler oluşturabilir. Az sayıda olası değeri olan değerleri tag'lere koy (warehouse, sensor). Ölçülen sayıları field'lara koy. Bir müşteri id'sini ya da bir request id'sini asla tag'e koyma."),
                  "marks": {"l": {k: "read" for k in range(len(IX_LINES))}}, "out": out, "count": {"points": len(IX_LINES), "series": len(series)}})
    return {"tables": [{"id": "l", "name": "line protocol", "cols": ["line"], "rows": rows, "key": [], "ref": []}],
            "out": {"name": T(lang, "series", "series"), "cols": ["series key", "points"]}, "steps": steps}


def ix_window(lang):
    every = 15
    wins = {}
    for t, v in IX_RAW:
        h, mi = map(int, t.split(":"))
        start = f"{h:02d}:{(mi // every) * every:02d}"
        wins.setdefault(start, []).append((t, v))
    steps = [{"say": T(lang, "aggregateWindow(every: 15m, fn: mean): the raw points of IST-1 temperature arrive every 5 minutes. The function puts them into windows of 15 minutes and calculates one mean for each window.",
                       "aggregateWindow(every: 15m, fn: mean): IST-1 sıcaklığının ham point'leri 5 dakikada bir gelir. Fonksiyon onları 15 dakikalık pencerelere koyar ve her pencere için bir ortalama hesaplar."),
              "marks": {}, "out": [], "count": {"raw points read": 0, "points returned": 0}}]
    out, done, m = [], 0, {}
    for start, pts in wins.items():
        idx = [i for i, r in enumerate(IX_RAW) if (r[0], r[1]) in pts]
        done += len(pts)
        mean = round(sum(v for _, v in pts) / len(pts), 2)
        h, mi = map(int, start.split(":"))
        stop = f"{h + (mi + every) // 60:02d}:{(mi + every) % 60:02d}"
        out.append([stop, mean])
        m = {**{k: "skip" for k in m}, **{i: "match" for i in idx}}
        steps.append({"say": T(lang, f"Window {start} to {stop}: the points {', '.join(t for t, _ in pts)}. Mean: ({' + '.join(str(v) for _, v in pts)}) / {len(pts)} = {mean}. By default, aggregateWindow puts the end of the window ({stop}) in _time.",
                               f"{start} - {stop} penceresi: {', '.join(t for t, _ in pts)} point'leri. Ortalama: ({' + '.join(str(v) for _, v in pts)}) / {len(pts)} = {mean}. aggregateWindow varsayılan olarak pencerenin sonunu ({stop}) _time'a koyar."),
                      "marks": {"r": dict(m)}, "out": deepcopy(out), "outmarks": {len(out) - 1: "new"}, "count": {"raw points read": done, "points returned": len(out)}})
    steps.append({"say": T(lang, f"{len(IX_RAW)} raw points became {len(out)} points. A chart of 6 hours with 5-minute points has 72 points per line. With 1-hour windows, it has 6. The same query with every: 1h returns fewer points for the same time range.",
                           f"{len(IX_RAW)} ham point {len(out)} point'e dönüştü. 5 dakikalık point'lerle 6 saatlik bir grafikte çizgi başına 72 point vardır. 1 saatlik pencerelerle 6 point vardır. Aynı query every: 1h ile aynı zaman aralığı için daha az point döndürür."),
                  "marks": {"r": {k: "skip" for k in range(len(IX_RAW))}}, "out": out, "count": {"raw points read": len(IX_RAW), "points returned": len(out)}})
    return {"tables": [{"id": "r", "name": T(lang, "raw points: IST-1, temperature", "ham point'ler: IST-1, temperature"), "cols": ["_time", "_value"], "rows": IX_RAW, "key": [0], "ref": []}],
            "out": {"name": T(lang, "result: one point per 15 minutes", "sonuç: 15 dakikada bir point"), "cols": ["_time", "mean"]}, "steps": steps}


IX_SHARDS = [["SG1", "Oct 21", "Oct 22", 288], ["SG2", "Oct 22", "Oct 23", 288], ["SG3", "Oct 23", "Oct 24", 288], ["SG4", "Oct 24", "Oct 25", 288], ["SG5", "Oct 25", "Oct 26", 160]]


def ix_retention(lang):
    rows = deepcopy(IX_SHARDS)
    steps = [{"say": T(lang, "The bucket has a retention period of 3 days (an example). InfluxDB groups the points by time into shard groups, here one per day. Now it is Oct 25, 13:20.",
                       "Bucket'ın retention period'u 3 gündür (örnek). InfluxDB point'leri zamana göre shard group'lara gruplar, burada günde bir. Şimdi 25 Ekim, 13:20."),
              "marks": {}, "rows": {"g": deepcopy(rows)}, "out": [], "count": {"shard groups read": 0, "shard groups deleted": 0}}]
    steps.append({"say": T(lang, "Query: range(start: -1d). The shard groups SG4 and SG5 cover the last day. InfluxDB reads only these two. It does not open the older shard groups.",
                           "Query: range(start: -1d). SG4 ve SG5 shard group'ları son günü kapsar. InfluxDB sadece bu ikisini okur. Daha eski shard group'ları açmaz."),
                  "marks": {"g": {3: "read", 4: "read", 0: "skip", 1: "skip", 2: "skip"}}, "rows": {"g": deepcopy(rows)}, "out": [], "count": {"shard groups read": 2, "shard groups deleted": 0}})
    steps.append({"say": T(lang, "The retention check runs. The end of SG1 (Oct 22) is more than 3 days before now (Oct 25, 13:20). All points of SG1 are too old, so InfluxDB drops the complete shard group. It does not delete point by point.",
                           "Retention kontrolü çalışır. SG1'in sonu (22 Ekim) şimdiden (25 Ekim, 13:20) 3 günden daha önce. SG1'in bütün point'leri çok eski, bu yüzden InfluxDB bütün shard group'u düşürür. Point point silmez."),
                  "marks": {"g": {0: "bad"}}, "rows": {"g": deepcopy(rows)}, "out": [], "count": {"shard groups read": 2, "shard groups deleted": 0}})
    rows = rows[1:]
    steps.append({"say": T(lang, "SG1 is gone. SG2 ends on Oct 23, which is less than 3 days ago, so it stays until a later check. The storage stays near the same size every day: new points come in, a full old day goes out. You write no delete job.",
                           "SG1 gitti. SG2 23 Ekim'de biter, bu 3 günden kısa bir süre önce, bu yüzden sonraki bir kontrole kadar kalır. Storage her gün yaklaşık aynı boyutta kalır: yeni point'ler gelir, eski ve dolu bir gün gider. Hiç silme job'u yazmazsın."),
                  "marks": {"g": {0: "read"}}, "rows": {"g": deepcopy(rows)}, "out": [], "count": {"shard groups read": 2, "shard groups deleted": 1}})
    return {"tables": [{"id": "g", "name": T(lang, "shard groups of the bucket metrics", "metrics bucket'ının shard group'ları"), "cols": ["shard group", "start", "end", "points"], "rows": IX_SHARDS, "key": [0], "ref": []}],
            "out": {"name": T(lang, "result", "sonuç"), "cols": ["-"]}, "steps": steps}


IX_CANDS = ["Timestream for InfluxDB", "Aurora PostgreSQL", "DynamoDB", "Redshift", "OpenSearch"]


def influxdb(lang):
    w1 = verdicts(IX_CANDS, [
        V((1, "line protocol, append in time order", "line protocol, zaman sırasıyla ekleme"), (1, "INSERT", "INSERT"), (1, "PutItem", "PutItem"),
          (0, "built for large loads, not a point every few seconds", "büyük yüklemeler için yapıldı, birkaç saniyede bir point için değil"), (1, "bulk indexing", "bulk indexing")),
        V((1, "aggregateWindow", "aggregateWindow"), (0, "GROUP BY over a large row table for each chart", "her grafik için büyük bir row table'ı üzerinde GROUP BY"), (0, "no aggregation", "aggregation yok"),
          (0, "removed earlier", "daha önce elendi"), (1, "date_histogram", "date_histogram")),
        V((1, "retention period of the bucket", "bucket'ın retention period'u"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"),
          (0, "needs an index per day and a lifecycle policy that you design", "gün başına bir index ve senin tasarladığın bir lifecycle policy ister")),
    ])
    w2 = verdicts(IX_CANDS, [
        V((0, "points are appended, not updated with rules", "point'ler eklenir, kurallarla güncellenmez"), (1, "UPDATE with constraints", "constraint'lerle UPDATE"), (1, "UpdateItem with conditions", "koşullu UpdateItem"),
          (0, "not for single-row changes", "tek row değişiklikleri için değil"), (0, "a search copy", "bir arama kopyası")),
        V((0, "removed earlier", "daha önce elendi"), (1, "ACID transactions", "ACID transaction'lar"), (1, "TransactWriteItems", "TransactWriteItems"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
        V((0, "removed earlier", "daha önce elendi"), (1, "foreign keys, CHECK", "foreign key'ler, CHECK"), (0, "no foreign keys", "foreign key yok"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
    ])
    spec = {
        "decide_metrics": decide_generic(lang, ("Temperature and humidity of 4 warehouses every 5 minutes, charts per 15 minutes, data older than 30 days goes away", "4 deponun sıcaklık ve nemi 5 dakikada bir, 15 dakikalık grafikler, 30 günden eski veri gider"),
                                         [("A steady stream of small, time-stamped writes", "Küçük, zaman damgalı yazmaların sürekli akışı"),
                                          ("Time windows and means in milliseconds for each chart", "Her grafik için milisaniyelerde zaman pencereleri ve ortalamalar"),
                                          ("Old points expire automatically", "Eski point'ler otomatik olarak sona erer")], IX_CANDS, w1),
        "decide_orders": decide_generic(lang, ("The order records of the shop", "Mağazanın sipariş kayıtları"),
                                        [("Update one record under rules", "Bir kaydı kurallar altında güncelle"),
                                         ("Several records change as one unit", "Birkaç kayıt tek bir birim olarak değişir"),
                                         ("Rules between tables are enforced", "Table'lar arası kurallar uygulanır")], IX_CANDS, w2),
        "series": ix_series(lang), "window": ix_window(lang), "retention": ix_retention(lang),
    }
    return {k: _localize(v, lang) for k, v in spec.items()}


COUNT_TR.update({"points": "point", "series": "series", "raw points read": "okunan ham point", "points returned": "dönen point",
                 "shard groups read": "okunan shard group", "shard groups deleted": "silinen shard group"})
SIMS["influxdb"] = influxdb


# ================================================================ Amazon S3 (object storage)
S3_KEYS = [["products/P0001.jpg", 48213, "image/jpeg"], ["products/P0016.jpg", 51022, "image/jpeg"], ["products/P0044.jpg", 46870, "image/jpeg"],
           ["uploads/v-3c8d/photo.jpg", 230411, "image/jpeg"], ["uploads/v-7f3a/invoice.pdf", 88120, "application/pdf"], ["uploads/v-7f3a/photo.jpg", 194002, "image/jpeg"]]
EXTRA_TABLES["s3_keys"] = {"cols": ["key", "size (bytes)", "Content-Type"], "rows": S3_KEYS}


def s3_prefix(lang):
    pre = "uploads/v-7f3a/"
    steps = [{"say": T(lang, "A bucket is flat: it holds keys and objects, and no folders. A slash in a key is a normal character.",
                       "Bir bucket düzdür: key'ler ve object'ler tutar, klasör tutmaz. Bir key'deki slash normal bir karakterdir."),
              "marks": {}, "out": [], "count": {"keys returned": 0, "common prefixes": 0}}]
    out, m = [], {}
    for i, (k, size, ct) in enumerate(S3_KEYS):
        hit = k.startswith(pre)
        m[i] = "match" if hit else "skip"
        if hit:
            out.append([k, size])
    steps.append({"say": T(lang, f"ListObjectsV2(Prefix='{pre}'): S3 returns only the keys that start with this text. S3 lists keys in sorted order, so all keys with one prefix come together in the list.",
                           f"ListObjectsV2(Prefix='{pre}'): S3 sadece bu metinle başlayan key'leri döndürür. S3 key'leri sıralı listeler, bu yüzden aynı prefix'e sahip bütün key'ler listede yan yana gelir."),
                  "marks": {"k": dict(m)}, "out": deepcopy(out), "count": {"keys returned": len(out), "common prefixes": 0}})
    groups = []
    for k, _, _ in S3_KEYS:
        g = k.split("/")[0] + "/"
        if g not in groups:
            groups.append(g)
    steps.append({"say": T(lang, "ListObjectsV2(Delimiter='/') with no prefix: S3 groups the keys up to the first slash. Each group comes back once, as a CommonPrefixes element. This is how the console shows \"folders\".",
                           "Prefix olmadan ListObjectsV2(Delimiter='/'): S3 key'leri ilk slash'e kadar gruplar. Her grup bir kez, bir CommonPrefixes elemanı olarak döner. Konsol \"klasörleri\" böyle gösterir."),
                  "marks": {"k": {i: ("read" if k.startswith("products/") else "new") for i, (k, _, _) in enumerate(S3_KEYS)}}, "out": [[g, "CommonPrefixes"] for g in groups], "count": {"keys returned": 0, "common prefixes": len(groups)}})
    steps.append({"say": T(lang, "Result: a \"folder\" is only the common start of some keys. To delete a folder, you delete every key with that prefix. The Lale Market reset does this for uploads/.",
                           "Sonuç: bir \"klasör\" sadece bazı key'lerin ortak başlangıcıdır. Bir klasörü silmek için o prefix'e sahip her key'i silersin. Lale Market'in reset'i bunu uploads/ için yapar."),
                  "marks": {"k": {i: ("match" if k.startswith("uploads/") else "skip") for i, (k, _, _) in enumerate(S3_KEYS)}}, "out": [[g, "CommonPrefixes"] for g in groups], "count": {"keys returned": 0, "common prefixes": len(groups)}})
    return {"tables": [{"id": "k", "name": T(lang, "keys in the bucket (sorted)", "bucket'taki key'ler (sıralı)"), "cols": ["key", "size", "Content-Type"], "rows": S3_KEYS, "key": [0], "ref": []}],
            "out": {"name": T(lang, "response", "cevap"), "cols": ["Key / Prefix", T(lang, "size or type", "boyut ya da tür")]}, "steps": steps}


def s3_versions(lang):
    key = "uploads/v-7f3a/photo.jpg"
    v = []
    steps = [{"say": T(lang, f"Versioning is on for the bucket. The key {key} has no object yet.", f"Bucket'ta versioning açık. {key} key'inin henüz object'i yok."),
              "marks": {}, "rows": {"v": []}, "out": [], "count": {"versions": 0}}]
    v.insert(0, ["3HL4kqtJ", "PUT", "194,002 bytes", T(lang, "yes", "evet")])
    steps.append({"say": T(lang, "PUT photo.jpg: S3 stores the object and gives it the version id 3HL4kqtJ. It is the current version.",
                           "PUT photo.jpg: S3 object'i saklar ve ona 3HL4kqtJ version id'sini verir. Güncel version budur."),
                  "marks": {"v": {0: "new"}}, "rows": {"v": deepcopy(v)}, "out": [["GET " + key, "3HL4kqtJ, 194,002 bytes"]], "count": {"versions": 1}})
    v[0][3] = T(lang, "no", "hayır")
    v.insert(0, ["QUpfdndh", "PUT", "201,377 bytes", T(lang, "yes", "evet")])
    steps.append({"say": T(lang, "The visitor uploads a new photo with the same key. S3 does not overwrite the old object. It adds a new version, QUpfdndh, on top. A GET without a version id returns the newest version.",
                           "Ziyaretçi aynı key ile yeni bir fotoğraf yükler. S3 eski object'in üstüne yazmaz. Üstüne yeni bir version ekler: QUpfdndh. Version id'siz bir GET en yeni version'ı döndürür."),
                  "marks": {"v": {0: "new", 1: "read"}}, "rows": {"v": deepcopy(v)}, "out": [["GET " + key, "QUpfdndh, 201,377 bytes"]], "count": {"versions": 2}})
    v[0][3] = T(lang, "no", "hayır")
    v.insert(0, ["Uk2a9mcE", "DELETE marker", "-", T(lang, "yes", "evet")])
    steps.append({"say": T(lang, "DELETE without a version id: S3 deletes nothing. It adds a delete marker as the newest version. A normal GET now returns 404 Not Found.",
                           "Version id'siz DELETE: S3 hiçbir şey silmez. En yeni version olarak bir delete marker ekler. Normal bir GET artık 404 Not Found döndürür."),
                  "marks": {"v": {0: "bad"}}, "rows": {"v": deepcopy(v)}, "out": [["GET " + key, "404 Not Found"]], "count": {"versions": 3}})
    steps.append({"say": T(lang, "GET with versionId=3HL4kqtJ still returns the first photo. To restore it, copy that version to the same key, or delete the delete marker. In Lale Market, a lifecycle rule deletes a version 1 day after it stops being the current version.",
                           "versionId=3HL4kqtJ ile GET hâlâ ilk fotoğrafı döndürür. Onu geri getirmek için o version'ı aynı key'e kopyala ya da delete marker'ı sil. Lale Market'te bir lifecycle kuralı, bir version'ı güncel olmaktan çıktıktan 1 gün sonra siler."),
                  "marks": {"v": {0: "bad", 2: "match"}}, "rows": {"v": deepcopy(v)}, "out": [["GET " + key, "404 Not Found"], ["GET ...?versionId=3HL4kqtJ", "3HL4kqtJ, 194,002 bytes"]], "count": {"versions": 3}})
    return {"tables": [{"id": "v", "name": T(lang, f"versions of {key} (newest first)", f"{key} version'ları (en yeni önce)"), "cols": ["VersionId", T(lang, "request", "istek"), T(lang, "size", "boyut"), "IsLatest"], "rows": [], "key": [0], "ref": []}],
            "out": {"name": T(lang, "what a reader gets", "bir okuyucunun aldığı"), "cols": [T(lang, "request", "istek"), T(lang, "response", "cevap")]}, "steps": steps}


def s3_presign(lang):
    reqs = [["t = 0 s", T(lang, "the Engine App signs a GET URL with ExpiresIn=300", "Engine App ExpiresIn=300 ile bir GET URL'sini imzalar")],
            ["t = 12 s", T(lang, "the browser opens the URL", "tarayıcı URL'yi açar")],
            ["t = 140 s", T(lang, "a second person opens the same URL", "ikinci bir kişi aynı URL'yi açar")],
            ["t = 410 s", T(lang, "the browser opens the URL again", "tarayıcı URL'yi yeniden açar")]]
    steps = [{"say": T(lang, "The bucket is private. A browser has no AWS credentials. The Engine App has an IAM role that can read products/P0001.jpg.",
                       "Bucket private'tır. Bir tarayıcının AWS kimlik bilgisi yoktur. Engine App'in products/P0001.jpg'i okuyabilen bir IAM role'ü vardır."),
              "marks": {}, "out": [], "count": {"allowed": 0, "refused": 0}}]
    out = [["t = 0 s", "https://...amazonaws.com/products/P0001.jpg?X-Amz-Expires=300&X-Amz-Signature=..."]]
    steps.append({"say": T(lang, "The Engine App calls generate_presigned_url. It does not call S3. It calculates a signature with its own credentials and puts it, with the expiry, in the query string of the URL.",
                           "Engine App generate_presigned_url'i çağırır. S3'ü çağırmaz. Kendi kimlik bilgileriyle bir imza hesaplar ve onu süresiyle birlikte URL'nin query string'ine koyar."),
                  "marks": {"r": {0: "new"}}, "out": deepcopy(out), "count": {"allowed": 0, "refused": 0}})
    out.append(["t = 12 s", "200 OK (48,213 bytes)"])
    steps.append({"say": T(lang, "At 12 seconds, the browser sends GET with the URL. S3 checks the signature and the time. Both are valid, so S3 returns the image. The request uses the permissions of the role that signed it.",
                           "12. saniyede tarayıcı URL ile GET gönderir. S3 imzayı ve zamanı kontrol eder. İkisi de geçerli, bu yüzden S3 görseli döndürür. İstek, onu imzalayan role'ün izinlerini kullanır."),
                  "marks": {"r": {0: "read", 1: "match"}}, "out": deepcopy(out), "count": {"allowed": 1, "refused": 0}})
    out.append(["t = 140 s", "200 OK (48,213 bytes)"])
    steps.append({"say": T(lang, "At 140 seconds, a second person uses the same URL, and it works too. Anyone who has the URL can use it until it expires. Keep presigned URLs short-lived and do not log them.",
                           "140. saniyede ikinci bir kişi aynı URL'yi kullanır ve o da çalışır. URL'ye sahip olan herkes onu süresi dolana kadar kullanabilir. Presigned URL'leri kısa ömürlü tut ve log'lama."),
                  "marks": {"r": {0: "read", 1: "match", 2: "match"}}, "out": deepcopy(out), "count": {"allowed": 2, "refused": 0}})
    out.append(["t = 410 s", "403 AccessDenied: Request has expired"])
    steps.append({"say": T(lang, "At 410 seconds, the 300 seconds are over. S3 refuses with AccessDenied, \"Request has expired\". The application must sign a new URL.",
                           "410. saniyede 300 saniye dolmuştur. S3 AccessDenied, \"Request has expired\" ile reddeder. Uygulama yeni bir URL imzalamalıdır."),
                  "marks": {"r": {0: "read", 1: "match", 2: "match", 3: "bad"}}, "out": deepcopy(out), "outmarks": {3: "bad"}, "count": {"allowed": 2, "refused": 1}})
    return {"tables": [{"id": "r", "name": T(lang, "timeline", "zaman çizelgesi"), "cols": [T(lang, "time", "zaman"), T(lang, "action", "eylem")], "rows": reqs, "key": [0], "ref": []}],
            "out": {"name": T(lang, "responses", "cevaplar"), "cols": [T(lang, "time", "zaman"), T(lang, "result", "sonuç")]}, "steps": steps}


S3_CANDS = ["Amazon S3", "Aurora PostgreSQL", "DynamoDB", "DocumentDB", "ElastiCache"]


def s3(lang):
    w1 = verdicts(S3_CANDS, [
        V((1, "objects up to 5 TB", "5 TB'a kadar object'ler"), (0, "large binaries make tables, backups and replicas heavy", "büyük binary'ler table'ları, yedekleri ve replica'ları ağırlaştırır"),
          (0, "an item is at most 400 KB", "bir item en fazla 400 KB"), (0, "a document is at most 16 MB", "bir document en fazla 16 MB"), (0, "memory is expensive and not the durable store", "bellek pahalıdır ve kalıcı depo değildir")),
        V((1, "presigned URL or CloudFront", "presigned URL ya da CloudFront"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
        V((1, "versioning", "versioning"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi"), (0, "removed earlier", "daha önce elendi")),
    ])
    w2 = verdicts(S3_CANDS, [
        V((0, "an object is replaced as a whole", "bir object bütün olarak değiştirilir"), (1, "UPDATE one column", "tek kolonu UPDATE"), (1, "UpdateItem", "UpdateItem"), (1, "$inc on one field", "tek field'da $inc"), (1, "DECRBY on one key", "tek key'de DECRBY")),
        V((0, "removed earlier", "daha önce elendi"), (1, "UPDATE ... WHERE stock >= n", "UPDATE ... WHERE stock >= n"), (1, "ConditionExpression", "ConditionExpression"), (1, "filter in updateOne", "updateOne'da filtre"), (1, "a Lua script or WATCH", "bir Lua script'i ya da WATCH")),
        V((0, "removed earlier", "daha önce elendi"), (1, "ACID, durable", "ACID, kalıcı"), (1, "durable, transactions", "kalıcı, transaction'lar"), (1, "durable, transactions", "kalıcı, transaction'lar"), (0, "a cache, not the source of truth", "bir cache, source of truth değil")),
    ])
    spec = {
        "decide_images": decide_generic(lang, ("Product images and files that sellers upload: 50 KB to 50 MB each, shown in the browser", "Ürün görselleri ve satıcıların yüklediği dosyalar: her biri 50 KB ile 50 MB arası, tarayıcıda gösterilir"),
                                        [("Store files of any size durably", "Her boyuttaki dosyayı kalıcı olarak sakla"),
                                         ("The browser downloads a file directly, not through the app", "Tarayıcı dosyayı uygulama üzerinden değil, doğrudan indirir"),
                                         ("Keep the old file when a seller uploads a new one", "Satıcı yenisini yüklediğinde eski dosyayı tut")], S3_CANDS, w1),
        "decide_stock": decide_generic(lang, ("The stock count of each product, reduced at each checkout", "Her ürünün stok sayısı, her checkout'ta azaltılır"),
                                       [("Change one number inside a record", "Bir kaydın içindeki tek bir sayıyı değiştir"),
                                        ("Reduce only if enough stock is left", "Sadece yeterli stok kaldıysa azalt"),
                                        ("Durable source of truth", "Kalıcı source of truth")], S3_CANDS, w2),
        "prefix": s3_prefix(lang), "versions": s3_versions(lang), "presign": s3_presign(lang),
    }
    return {k: _localize(v, lang) for k, v in spec.items()}


COUNT_TR.update({"keys returned": "dönen key", "common prefixes": "common prefix", "versions": "version", "allowed": "izin verilen", "refused": "reddedilen"})
SIMS["s3"] = s3
