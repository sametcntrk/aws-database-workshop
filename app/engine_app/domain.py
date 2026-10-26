"""Synthetic e-commerce Domain data shared by all Engine Apps.

The data is deterministic for a given size, so every Engine models the same customers, products and
orders. No external dependency (no Faker) so the code runs on a fresh EC2 instance.
"""
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


@dataclass
class Dataset:
    size: str
    customers: list = field(default_factory=list)
    products: list = field(default_factory=list)
    orders: list = field(default_factory=list)      # order header + items
    stores: list = field(default_factory=list)
    events: list = field(default_factory=list)
    readings: list = field(default_factory=list)


def build(size="medium", seed=42):
    if size not in SIZES:
        raise ValueError(f"unknown size {size!r}; use one of {', '.join(SIZES)}")
    n = SIZES[size]
    rnd = random.Random(seed)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    ds = Dataset(size=size)

    for i in range(1, n["customers"] + 1):
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
        brand = rnd.choice(BRANDS)
        color = rnd.choice(COLORS)
        ds.products.append({
            "product_id": f"P{i:04d}", "name": f"{brand} {base} {i}", "category": cat, "brand": brand,
            "price": round(rnd.uniform(49, 4999), 2), "stock": rnd.randint(0, 500), "color": color,
            "rating": round(rnd.uniform(2.5, 5.0), 1),
            "attributes": {"renk": color, "garanti_ay": rnd.choice([12, 24, 36]),
                           "agirlik_kg": round(rnd.uniform(0.1, 12), 2)},
            "tags": rnd.sample(["yeni", "indirim", "çok satan", "çevreci", "hızlı kargo", "sınırlı"], 2),
            "description": f"{brand} markalı {color} {base.lower()}. {cat} kategorisinde, "
                           f"{rnd.choice(['dayanıklı', 'hafif', 'şık', 'ekonomik', 'profesyonel'])} bir ürün.",
        })

    for i in range(1, n["orders"] + 1):
        cust = rnd.choice(ds.customers)
        when = now - timedelta(days=rnd.randint(0, 365), minutes=rnd.randint(0, 1439))
        items = []
        for p in rnd.sample(ds.products, rnd.randint(1, 4)):
            items.append({"product_id": p["product_id"], "qty": rnd.randint(1, 3), "unit_price": p["price"],
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

    hot_users = ds.customers[:20]
    for _ in range(n["events"]):
        cust = rnd.choice(hot_users) if rnd.random() < 0.3 else rnd.choice(ds.customers)
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
    return ds


def sample_customer(ds):
    """The customer used by Read pages: the first 'hot' user, so every Engine shows data for the same person."""
    return ds.customers[0]
