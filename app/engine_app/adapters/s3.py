"""Amazon S3 - blob: product images with object metadata."""
import base64
import hashlib
import io

import boto3
from PIL import Image, ImageDraw

from ..base import Adapter, ReadResult, SeedResult, env, region

PREFIX = "products/"
MODEL = """\
s3://<bucket>/products/<category>/<product_id>.png
  Content-Type: image/png
  x-amz-meta-product-id, x-amz-meta-name, x-amz-meta-category   (user metadata)

Objects are immutable blobs addressed by key; "folders" are only key prefixes."""

PALETTE = {"Elektronik": (35, 47, 62), "Ev & Yaşam": (1, 168, 141), "Spor": (236, 114, 17), "Kitap": (140, 79, 255),
           "Moda": (221, 52, 76)}


def render(product):
    img = Image.new("RGB", (320, 320), PALETTE.get(product["category"], (90, 90, 90)))
    d = ImageDraw.Draw(img)
    seed = int(hashlib.sha1(product["product_id"].encode()).hexdigest()[:6], 16)
    for k in range(6):  # simple generated pattern so each image differs
        x, y, r = (seed >> k) % 260, (seed >> (k + 3)) % 260, 30 + (seed >> k) % 60
        d.ellipse([x, y, x + r, y + r], outline=(255, 255, 255), width=3)
    d.rectangle([0, 250, 320, 320], fill=(0, 0, 0))
    d.text((12, 262), product["product_id"], fill=(255, 255, 255))
    d.text((12, 284), ascii_text(product["name"])[:40], fill=(255, 200, 120))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


ASCII = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iIsSgGuUoOcC")


def ascii_text(text):
    """S3 user metadata must be ASCII: transliterate Turkish letters instead of dropping them."""
    return text.translate(ASCII).encode("ascii", "replace").decode()


def slug(category):
    return category.lower().replace(" & ", "-").replace("ş", "s").replace("ı", "i").replace("ö", "o").replace("ü", "u")


class S3(Adapter):
    engine_id = "s3"
    title = "Amazon S3"
    data_type = "Unstructured"
    category = "Blob"
    domain_slice = "ürün görselleri"
    why = ("Dosya ve büyük nesneler için (görsel, video, yedek, log, veri gölü). Neredeyse sınırsız ölçek, "
           "11 dokuz dayanıklılık, nesne başına metadata. Sorgu motoru değildir: nesneye anahtarıyla erişilir.")
    model = MODEL

    def __init__(self):
        self.bucket = env("BUCKET_NAME")
        self.s3 = boto3.client("s3", region_name=region())

    def seed(self, ds):
        deleted = 0
        for page in self.s3.get_paginator("list_objects_v2").paginate(Bucket=self.bucket, Prefix=PREFIX):
            keys = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if keys:
                self.s3.delete_objects(Bucket=self.bucket, Delete={"Objects": keys, "Quiet": True})
                deleted += len(keys)
        n = min(len(ds.products), {"small": 12, "medium": 30, "large": 60}[ds.size])
        total = 0
        for p in ds.products[:n]:
            body = render(p)
            total += len(body)
            self.s3.put_object(Bucket=self.bucket, Key=f"{PREFIX}{slug(p['category'])}/{p['product_id']}.png", Body=body,
                               ContentType="image/png",
                               Metadata={"product-id": p["product_id"], "category": slug(p["category"]),
                                         "name": ascii_text(p["name"])})
        return SeedResult(
            summary=[f"{deleted} eski nesne silindi (DeleteObjects)", f"{n} PNG görsel yazıldı, toplam {total // 1024} KB",
                     "Her nesnede Content-Type ve kullanıcı metadata'sı var"],
            operation=f"put_object(Bucket='{self.bucket}', Key='products/elektronik/P0001.png', Body=<png>,\n"
                      "           ContentType='image/png', Metadata={'product-id': 'P0001', ...})",
            counts={"objects": n})

    def read(self):
        resp = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=f"{PREFIX}elektronik/", MaxKeys=6)
        rows, images = [], []
        for o in resp.get("Contents", []):
            obj = self.s3.get_object(Bucket=self.bucket, Key=o["Key"])
            data = obj["Body"].read()
            images.append("data:image/png;base64," + base64.b64encode(data).decode())
            rows.append((o["Key"], o["Size"], obj["ContentType"], obj["Metadata"].get("name"), obj.get("VersionId")))
        return ReadResult(["key", "size_bytes", "content_type", "x-amz-meta-name", "version_id"], rows,
                          f"list_objects_v2(Bucket='{self.bucket}', Prefix='products/elektronik/', MaxKeys=6)\n"
                          "get_object(Bucket=..., Key=...)  # her nesne için",
                          note="Görseller Engine App üzerinden okunup gösterildi; bucket public değil, trafik S3 gateway endpoint'inden geçer.",
                          images=images)


ADAPTER = S3
