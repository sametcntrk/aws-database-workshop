"""Synthetic e-commerce Domain data shared by all Engine Apps.

The data is deterministic for a given size, so every Engine models the same customers, products and
orders. No external dependency (no Faker) so the code runs on a fresh EC2 instance.
"""
import math
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

SIZES = {
    "small": {"customers": 200, "products": 50, "orders": 1000, "events": 2000, "readings": 2000, "images": 12},
    "medium": {"customers": 1000, "products": 200, "orders": 5000, "events": 10000, "readings": 10000, "images": 30},
    "large": {"customers": 5000, "products": 500, "orders": 25000, "events": 50000, "readings": 50000, "images": 60},
}

FIRST = ["Ayşe", "Mehmet", "Elif", "Can", "Zeynep", "Emre", "Deniz", "Selin", "Burak", "Ece", "Mert", "Derya",
         "Kerem", "Naz", "Ozan", "İrem", "Tolga", "Seda", "Umut", "Gizem", "Anna", "Lukas", "Mia", "Jonas"]
LAST = ["Yılmaz", "Kaya", "Demir", "Şahin", "Çelik", "Yıldız", "Aydın", "Öztürk", "Arslan", "Doğan", "Koç",
        "Kurt", "Müller", "Schmidt", "Weber", "Fischer"]
CITIES = [  # name, lat, lon
    ("İstanbul", 41.0082, 28.9784), ("Ankara", 39.9334, 32.8597), ("İzmir", 38.4237, 27.1428),
    ("Bursa", 40.1885, 29.0610), ("Antalya", 36.8969, 30.7133), ("Frankfurt", 50.1109, 8.6821),
    ("Berlin", 52.5200, 13.4050), ("München", 48.1351, 11.5820), ("Hamburg", 53.5511, 9.9937),
]
CATEGORIES = {
    "Elektronik": ["Kablosuz Kulaklık", "Akıllı Saat", "Bluetooth Hoparlör", "Powerbank", "Mekanik Klavye", "Oyuncu Mouse"],
    "Ev & Yaşam": ["Kahve Makinesi", "Su Isıtıcı", "Hava Temizleyici", "Robot Süpürge", "Masa Lambası"],
    "Spor": ["Koşu Ayakkabısı", "Yoga Matı", "Dambıl Seti", "Spor Çantası", "Matara"],
    "Kitap": ["Veritabanı Tasarımı", "Bulut Mimarisi", "Dağıtık Sistemler", "Python ile Veri", "Algoritmalar"],
    "Moda": ["Deri Ceket", "Kot Pantolon", "Yün Kazak", "Güneş Gözlüğü", "Sırt Çantası"],
}
BRANDS = ["Anadolu", "Bosphorus", "Kapadokya", "Rhein", "Alpen", "Nordwind", "Ege", "Toros"]
COLORS = ["siyah", "beyaz", "lacivert", "kırmızı", "yeşil", "gri"]
EVENT_TYPES = ["view", "search", "add_to_cart", "remove_from_cart", "wishlist", "purchase"]
WAREHOUSES = ["IST-1", "ANK-1", "FRA-1", "BER-1"]
SENSORS = ["temperature", "humidity"]

from .visitor import PERSONAS  # noqa: E402

# How many past orders each Persona has in the medium and large datasets, and the category they prefer.
PERSONA_ORDERS = {"C00001": 30, "C00002": 12, "C00004": 15, "C00005": 10, "C00006": 8}
PERSONA_CATEGORY = {"C00004": "Kitap", "C00005": "Moda", "C00006": "Spor"}


@dataclass
class Dataset:
    size: str
    customers: list = field(default_factory=list)
    products: list = field(default_factory=list)
    orders: list = field(default_factory=list)      # order header + items
    stores: list = field(default_factory=list)
    events: list = field(default_factory=list)
    readings: list = field(default_factory=list)
    order_rate: list = field(default_factory=list)


def build(size="medium", seed=42):
    if size not in SIZES:
        raise ValueError(f"unknown size {size!r}; use one of {', '.join(SIZES)}")
    n = SIZES[size]
    rnd = random.Random(seed)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    ds = Dataset(size=size)

    personas = {p["id"]: p for p in PERSONAS}
    for i in range(1, n["customers"] + 1):
        cid = f"C{i:05d}"
        if cid in personas:                       # the six Personas are fixed customers
            p = personas[cid]
            first, last = p["name"].split(" ", 1)
            ds.customers.append({
                "customer_id": cid, "name": p["name"],
                "email": f"{ascii_name(first)}.{ascii_name(last)}@example.com",
                "city": p["city"], "segment": p["segment"],
                "created_at": (now - timedelta(days=20 if cid == "C00003" else 600)).isoformat()})
            continue
        city = rnd.choice(CITIES)
        first, last = rnd.choice(FIRST), rnd.choice(LAST)
        ds.customers.append({
            "customer_id": f"C{i:05d}", "name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}{i}@example.com".encode("ascii", "ignore").decode(),
            "city": city[0], "segment": rnd.choice(["bireysel", "kurumsal", "premium"]),
            "created_at": (now - timedelta(days=rnd.randint(30, 900))).isoformat(),
        })

    cat_names = list(CATEGORIES)
    for i in range(1, n["products"] + 1):
        cat = cat_names[(i - 1) % len(cat_names)]
        base = rnd.choice(CATEGORIES[cat])
        if i == 1:      # every size has the product the OpenSearch Read searches for
            base = "Kablosuz Kulaklık"
        brand = rnd.choice(BRANDS)
        color = "siyah" if i == 1 else rnd.choice(COLORS)   # P0001 matches the DocumentDB Read filter
        ds.products.append({
            "product_id": f"P{i:04d}", "name": f"{brand} {base} {i}", "category": cat, "brand": brand, "type": base,
            "price": round(rnd.uniform(49, 4999), 2), "stock": rnd.randint(0, 500), "color": color,
            "rating": 4.8 if i == 1 else round(rnd.uniform(2.5, 5.0), 1),
            "attributes": {"renk": color, "garanti_ay": rnd.choice([12, 24, 36]),
                           "agirlik_kg": round(rnd.uniform(0.1, 12), 2)},
            "tags": rnd.sample(["yeni", "indirim", "çok satan", "çevreci", "hızlı kargo", "sınırlı"], 2),
            "description": f"{brand} markalı {color} {base.lower()}. {cat} kategorisinde, "
                           f"{rnd.choice(['dayanıklı', 'hafif', 'şık', 'ekonomik', 'profesyonel'])} bir ürün.",
        })

    by_cat = {c: [p for p in ds.products if p["category"] == c] for c in CATEGORIES}
    others = [c for c in ds.customers if c["customer_id"] not in personas or c["customer_id"] == "C00001"]
    plan = PERSONA_ORDERS if n["orders"] >= 1000 else {k: max(1, v // 3) for k, v in PERSONA_ORDERS.items()}
    queue = [cid for cid, count in plan.items() for _ in range(count)]   # Persona orders first, then random
    cmap = {c["customer_id"]: c for c in ds.customers}
    for i in range(1, n["orders"] + 1):
        cid = queue[i - 1] if i <= len(queue) else rnd.choice(others)["customer_id"]
        cust = cmap[cid]
        when = now - timedelta(days=rnd.randint(0, 365), minutes=rnd.randint(0, 1439))
        favourite = PERSONA_CATEGORY.get(cid)
        pool = by_cat[favourite] if favourite and rnd.random() < 0.85 else ds.products
        items = []
        for p in rnd.sample(pool, min(len(pool), rnd.randint(1, 4))):
            qty = rnd.randint(5, 20) if cid == "C00002" else rnd.randint(1, 3)
            items.append({"product_id": p["product_id"], "qty": qty, "unit_price": p["price"],
                          "category": p["category"]})
        ds.orders.append({
            "order_id": f"O{i:06d}", "customer_id": cust["customer_id"], "order_date": when.isoformat(),
            "status": rnd.choices(["delivered", "shipped", "processing", "cancelled"], [70, 15, 10, 5])[0],
            "items": items, "total": round(sum(x["qty"] * x["unit_price"] for x in items), 2),
        })

    for i, (city, lat, lon) in enumerate(CITIES * 3, start=1):
        ds.stores.append({"store_id": f"S{i:03d}", "name": f"{city} Mağaza {(i - 1) // len(CITIES) + 1}",
                          "city": city, "lat": round(lat + rnd.uniform(-0.15, 0.15), 5),
                          "lon": round(lon + rnd.uniform(-0.15, 0.15), 5)})

    hot_users = [c for c in ds.customers[:20] if c["customer_id"] != "C00003"]
    heavy = next(c for c in ds.customers if c["customer_id"] == "C00005")      # Zeynep browses a lot
    for _ in range(n["events"]):
        r = rnd.random()
        cust = heavy if r < 0.08 else rnd.choice(hot_users) if r < 0.35 else rnd.choice(ds.customers)
        prod = rnd.choice(ds.products)
        ds.events.append({
            "user_id": cust["customer_id"], "event_time": now - timedelta(minutes=rnd.randint(0, 60 * 24 * 30)),
            "event_id": uuid.UUID(int=rnd.getrandbits(128), version=4), "event_type": rnd.choice(EVENT_TYPES),
            "product_id": prod["product_id"], "detail": f"{prod['name']} · {prod['category']}",
        })

    per_series = max(1, n["readings"] // (len(WAREHOUSES) * len(SENSORS)))
    for wh in WAREHOUSES:
        for sensor in SENSORS:
            base = 21.0 if sensor == "temperature" else 45.0
            for k in range(per_series):
                t = now - timedelta(minutes=5 * (per_series - k))
                ds.readings.append({"warehouse": wh, "sensor": sensor, "time": t,
                                    "value": round(base + 3 * rnd.random() + (k % 288) / 96, 2)})
    for k in range(24 * 60):                                  # orders per minute, last 24 hours
        t = now - timedelta(minutes=24 * 60 - k)
        hour = t.hour + 3                                     # Türkiye time drives the daily curve
        base = 20 + 60 * max(0.0, math.sin((hour % 24 - 6) / 18 * math.pi))
        ds.order_rate.append({"time": t, "orders": max(0, int(rnd.gauss(base, base * 0.15)))})
    return ds


def ascii_name(text):
    return text.lower().translate(str.maketrans("ıişğüöç", "iisguoc")).encode("ascii", "ignore").decode()


def sample_customer(ds):
    """The customer used by Read pages: the first 'hot' user, so every Engine shows data for the same person."""
    return ds.customers[0]
