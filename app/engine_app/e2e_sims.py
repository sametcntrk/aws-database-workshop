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
    return {"customers": CUSTOMERS, "products": PRODUCTS, "orders": ORDERS, "order_items": ITEMS}


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
    return {"where": where_city(lang), "index": seq_vs_index(lang), "join": join_order(lang), "group": group_by_category(lang),
            "constraints": constraints(lang), "tx": tx_rollback(lang), "lost": last_piece(lang, False), "locked": last_piece(lang, True),
            "storage": aurora_write(lang)}


SIMS = {"aurora": aurora}
