#!/usr/bin/env python3
"""Download one freely licensed photo per product type from Wikimedia Commons.

Writes app/engine_app/static/products/<slug>.jpg and app/engine_app/static/products/CREDITS.md.
Only CC0, public domain, CC BY and CC BY-SA files are used; the credits file records author and licence.
Usage: python3 tools/fetch_product_images.py
"""
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "engine_app" / "static" / "products"
UA = "LaleMarketWorkshop/1.0 (https://github.com/sametcntrk/aws-database-workshop)"
# product type (as in engine_app/domain.py) -> Commons search terms, best first
TYPES = {
    "Kablosuz Kulaklık": ["headphones product", "headphones"], "Akıllı Saat": ["smartwatch", "smart watch"],
    "Bluetooth Hoparlör": ["bluetooth speaker", "portable speaker"], "Powerbank": ["power bank smartphone", "portable charger power bank", "power bank"],
    "Mekanik Klavye": ["mechanical keyboard"], "Oyuncu Mouse": ["gaming mouse", "computer mouse"],
    "Kahve Makinesi": ["espresso machine kitchen", "coffee machine kitchen", "espresso machine"], "Su Isıtıcı": ["electric kettle"],
    "Hava Temizleyici": ["air purifier"], "Robot Süpürge": ["robotic vacuum cleaner", "roomba"],
    "Masa Lambası": ["desk lamp on desk", "table lamp", "desk lamp"], "Koşu Ayakkabısı": ["running shoes", "running shoe"],
    "Yoga Matı": ["rolled yoga mat", "yoga mats", "yoga mat exercise"], "Dambıl Seti": ["dumbbells"], "Spor Çantası": ["sports bag", "duffel bag"],
    "Matara": ["water bottle"], "Veritabanı Tasarımı": ["stack of books"], "Bulut Mimarisi": ["book cover blank"],
    "Dağıtık Sistemler": ["hardcover book"], "Python ile Veri": ["python programming book", "book on desk", "notebook and book on desk"], "Algoritmalar": ["books on shelf"],
    "Deri Ceket": ["leather jacket"], "Kot Pantolon": ["folded jeans", "jeans on hanger", "pile of jeans"], "Yün Kazak": ["wool sweater", "sweater"],
    "Güneş Gözlüğü": ["sunglasses on table", "pair of sunglasses", "aviator sunglasses"], "Sırt Çantası": ["backpack"],
}
# files that matched a search term but do not show the product
EXCLUDE = {"File:2 الحداد.jpg", "File:Shattered light fixture 3.jpg", "File:Open Book Tahquitz.JPG",
           "File:Turbo Akku Vac Easy Home VC 618WP - battery pack-1376.jpg", "File:Yoga Mat Made of Carpet Underlay.jpg",
           "File:Espresso Machine oldest.jpg", "File:Official Program Woman Suffrage Procession - March 3, 1913.jpg",
           "File:Long (5748149058).jpg", "File:Levis Jeans (3849532157).jpg",
           "File:Max Giesinger - 2021-09-12 - Mannheim - Sven Mandel - 1D X MK II - 0229 - B70I3683 (re-developed).jpg"}
OK_LICENSES = re.compile(r"^(cc0|public domain|pd|cc by(-sa)? \d\.\d|cc by(-sa)?)", re.I)


def slug(text):
    return text.lower().translate(str.maketrans("ıişğüöç ", "iisguoc-"))


def api(params):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=30))


def clean(value):
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def find(term, used):
    data = api({"action": "query", "generator": "search", "gsrsearch": f"{term} filetype:bitmap", "gsrnamespace": 6,
                "gsrlimit": 25, "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 600})
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    for p in pages:
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic = clean(meta.get("LicenseShortName", {}).get("value"))
        if info.get("mime") != "image/jpeg" or not OK_LICENSES.match(lic) or p["title"] in used or p["title"] in EXCLUDE:
            continue
        if info.get("width", 0) < 500 or info.get("height", 0) < 400:
            continue
        return {"title": p["title"], "thumb": info["thumburl"], "page": info.get("descriptionurl"), "license": lic,
                "license_url": clean(meta.get("LicenseUrl", {}).get("value")), "artist": clean(meta.get("Artist", {}).get("value"))[:120]}
    return None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    used, credits = set(), []
    only = set(sys.argv[1:])
    if only:   # refresh some types; keep the other credit rows
        old = (OUT / "CREDITS.md").read_text(encoding="utf-8").splitlines()
        credits = [l for l in old if l.startswith("| ") and not l.startswith("| Product") and l.split(" | ")[0][2:] not in only]
    for name, terms in TYPES.items():
        if only and name not in only:
            continue
        hit = None
        for term in terms:
            hit = find(term, used)
            if hit:
                break
            time.sleep(0.5)
        if not hit:
            print("NO IMAGE", name, file=sys.stderr)
            continue
        used.add(hit["title"])
        req = urllib.request.Request(hit["thumb"], headers={"User-Agent": UA})
        (OUT / f"{slug(name)}.jpg").write_bytes(urllib.request.urlopen(req, timeout=60).read())
        credits.append(f"| {name} | [{hit['title'][5:]}]({hit['page']}) | {hit['artist'] or 'unknown'} | {hit['license']} |")
        print("ok", name, "←", hit["title"], hit["license"])
        time.sleep(0.5)
    (OUT / "CREDITS.md").write_text(
        "# Product photo credits\n\nPhotos from Wikimedia Commons, downloaded by `tools/fetch_product_images.py`.\n"
        "Each file keeps its own licence. Click the file name for the source page.\n\n"
        "| Product type | File | Author | Licence |\n|---|---|---|---|\n" + "\n".join(credits) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
