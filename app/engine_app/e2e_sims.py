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
    return tr if lang == "tr" else en


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


# ---------------------------------------------------------------- 0. Architecture decision: requirements remove candidates
# Each candidate answers each requirement with yes or no, and a short reason. A "no" removes the candidate.
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
    return {"decide_checkout": decide(lang, "checkout"), "decide_dashboard": decide(lang, "dashboard"), "decide_sessions": decide(lang, "sessions"),
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
        "decide_cart": decide_generic(lang, ("Shopping carts of all visitors, with a 50 times traffic jump on a sale day", "Bütün ziyaretçilerin sepetleri, indirim gününde 50 kat trafik artışıyla"),
                                      [("Traffic can jump 50 times in minutes, with no capacity plan", "Trafik, kapasite planı olmadan dakikalar içinde 50 kat artabilir"),
                                       ("Every confirmed write must survive the loss of a data center", "Onaylanan her yazma bir veri merkezinin kaybından sağ çıkmalı"),
                                       ("No servers to size, and the bill follows the requests", "Boyutlandırılacak sunucu yok, fatura istekleri takip eder"),
                                       ("Items of different shapes: a cart line, a coupon, a gift note", "Farklı şekillerde item'lar: bir sepet satırı, bir kupon, bir hediye notu")],
                                      DDB_CANDS, w1),
        "decide_report": decide_generic(lang, ("A finance report that joins carts, orders and products in new ways each month", "Her ay yeni şekillerde sepetleri, siparişleri ve ürünleri join eden bir finans raporu"),
                                        [("New questions with JOIN on any column, without a redesign", "Yeniden tasarım yapmadan, her column'da JOIN ile yeni sorular"),
                                         ("The same system also takes many small writes each second", "Aynı sistem saniyede çok sayıda küçük yazma da alır")],
                                        DDB_CANDS, w2),
        "decide_holds": decide_generic(lang, ("Seat holds for a concert: a hold expires after 10 minutes, and two people must never hold the same seat", "Bir konser için koltuk tutma: tutma 10 dakika sonra düşer ve iki kişi asla aynı koltuğu tutmamalı"),
                                       [("Each hold deletes itself after a time", "Her tutma bir süre sonra kendini siler"),
                                        ("A confirmed hold must survive a crash", "Onaylanan bir tutma çökmeden sağ çıkmalı"),
                                        ("A second hold of the same seat must fail", "Aynı koltuğun ikinci tutması başarısız olmalı"),
                                        ("The hold carries free extra fields (price class, promo code)", "Tutma serbest ek alanlar taşır (fiyat sınıfı, promosyon kodu)")],
                                       DDB_CANDS, w3),
        "hash": ddb_hash(lang), "queryscan": ddb_query_scan(lang), "condition": ddb_condition(lang), "gsi": ddb_gsi(lang),
    }
    return {k: _localize(v, lang) for k, v in spec.items()}


COUNT_TR.update({"partitions touched": "dokunulan partition", "items read": "okunan item", "items returned": "dönen item",
                 "items read on the base table": "ana table'da okunan item", "items read on the GSI": "GSI'da okunan item", "candidates left": "kalan aday"})
SIMS["dynamodb"] = dynamodb

EXTRA_TABLES["cart"] = CART
