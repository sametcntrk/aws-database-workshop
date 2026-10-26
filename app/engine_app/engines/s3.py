"""Amazon S3 - blob: product images (served to every page), the seller panel upload and the gallery."""
import hashlib
import io
import re
import time

import boto3
from botocore.exceptions import ClientError
from flask import Response, jsonify, request
from PIL import Image, ImageDraw

from .. import trace
from ..base import env, region
from ..visitor import visitor_id
from . import page

META = {
    "id": "s3", "name": "Amazon S3", "data_type": "Unstructured", "category": "Blob", "auth": "IAM role (SigV4)",
    "via": "S3/DynamoDB gateway endpoint → S3", "section": "Seller panel and images",
    "model": "s3://<bucket>/products/<product_id>.png       Content-Type, x-amz-meta-name, x-amz-meta-category\n"
             "s3://<bucket>/uploads/<visitor>/<file>        x-amz-meta-product-id   (versioning on)",
}
PAGES = [page("seller", "seller", "Seller panel", "/seller")]
PALETTE = {"Elektronik": (20, 33, 61), "Ev & Yaşam": (27, 138, 143), "Spor": (200, 16, 46), "Kitap": (92, 64, 51),
           "Moda": (122, 31, 92)}
ASCII = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iIsSgGuUoOcC")
MAX_UPLOAD = 2 * 1024 * 1024

_s3 = None


def s3():
    global _s3
    if _s3 is None:
        _s3 = boto3.client("s3", region_name=region())
    return _s3


def ascii_text(text):
    return text.translate(ASCII).encode("ascii", "replace").decode()


def render(product):
    """A generated product picture: category colour, a simple shape pattern and the product name."""
    img = Image.new("RGB", (480, 480), PALETTE.get(product["category"], (90, 90, 90)))
    d = ImageDraw.Draw(img)
    seed = int(hashlib.sha1(product["product_id"].encode()).hexdigest()[:8], 16)
    for k in range(7):     # a simple pattern, different for each product
        x, y, rad = (seed >> k) % 360, (seed >> (k + 4)) % 360, 40 + (seed >> k) % 90
        d.ellipse([x, y, x + rad, y + rad], outline=(255, 255, 255), width=4)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def register(bp):
    @bp.get("/api/img/<pid>")
    def api_img(pid):
        if not re.fullmatch(r"P\d{4}", pid):
            return Response(status=404)
        try:
            obj = s3().get_object(Bucket=env("BUCKET_NAME"), Key=f"products/{pid}.png")
        except ClientError:
            return Response(status=404)
        return Response(obj["Body"].read(), mimetype="image/png", headers={"Cache-Control": "public, max-age=300"})

    @bp.get("/api/gallery")
    def api_gallery():
        prefix = "uploads/" if request.args.get("source") == "uploads" else "products/"
        with trace.call("ListObjectsV2", f"s3.list_objects_v2(Bucket=..., Prefix='{prefix}', MaxKeys=12)", {"prefix": prefix}) as t:
            resp = s3().list_objects_v2(Bucket=env("BUCKET_NAME"), Prefix=prefix, MaxKeys=12)
            objs = resp.get("Contents", [])
            t.result(items=len(objs), note="A prefix only looks like a folder: S3 has one flat namespace of keys.")
        out = []
        for o in objs[:6]:
            with trace.call("HeadObject", f"s3.head_object(Bucket=..., Key='{o['Key']}')", {}) as t:
                h = s3().head_object(Bucket=env("BUCKET_NAME"), Key=o["Key"])
                t.result(note="HEAD returns the metadata without the bytes.")
            out.append({"key": o["Key"], "size": o["Size"], "type": h["ContentType"], "metadata": h["Metadata"],
                        "version": h.get("VersionId"), "modified": o["LastModified"].isoformat()})
        return jsonify(trace.payload(out))

    @bp.post("/api/upload")
    def api_upload():
        f = request.files.get("file")
        if not f:
            return jsonify(ok=False, error="Select an image file.", trace=[]), 400
        data = f.read(MAX_UPLOAD + 1)
        if len(data) > MAX_UPLOAD:
            return jsonify(ok=False, error="The file is larger than 2 MB.", trace=[]), 400
        name = re.sub(r"[^A-Za-z0-9._-]", "_", f.filename or "image")[:60]
        key = f"uploads/{visitor_id()}/{int(time.time())}-{name}"
        meta = {"product-id": request.form.get("product_id", "P0001")[:10], "uploaded-by": visitor_id()}
        with trace.call("PutObject", f"s3.put_object(Bucket=..., Key='{key}', Body=<{len(data)} bytes>,\n"
                        f"  ContentType='{f.mimetype}', Metadata={meta})", {"bytes": len(data)}) as t:
            resp = s3().put_object(Bucket=env("BUCKET_NAME"), Key=key, Body=data, ContentType=f.mimetype or "application/octet-stream",
                                   Metadata=meta)
            t.result(items=1, note=f"S3 stored the object on at least 3 AZs. Version id {resp.get('VersionId')} "
                     "keeps the old version when you upload the same key again.")
        return jsonify(trace.payload({"key": key, "version": resp.get("VersionId")}))

    @bp.get("/api/presign/<pid>")
    def api_presign(pid):
        key = f"products/{pid}.png"
        with trace.call("generate_presigned_url", f"s3.generate_presigned_url('get_object', Params={{'Key': '{key}'}}, ExpiresIn=300)",
                        {"expires_in": "300 s"}) as t:
            url = s3().generate_presigned_url("get_object", Params={"Bucket": env("BUCKET_NAME"), "Key": key}, ExpiresIn=300)
            t.result(note="No request goes to S3 here: the app only signs a URL. The browser then downloads straight from S3, "
                     "so the Engine App does not carry the bytes. The bucket stays private.")
        return jsonify(trace.payload({"url": url}))


def seed(ds):
    with trace.call("PutObject × N", f"{len(ds.products)} × s3.put_object(Key='products/<id>.png', ContentType='image/png', Metadata=...)", {}) as t:
        total = 0
        for p in ds.products:
            body = render(p)
            total += len(body)
            s3().put_object(Bucket=env("BUCKET_NAME"), Key=f"products/{p['product_id']}.png", Body=body, ContentType="image/png",
                            Metadata={"name": ascii_text(p["name"]), "category": ascii_text(p["category"])})
        t.result(items=len(ds.products))
    return [f"Wrote {len(ds.products)} product images ({total // 1024} KB)."]


def reset_visitors():
    n = 0
    for pg in s3().get_paginator("list_objects_v2").paginate(Bucket=env("BUCKET_NAME"), Prefix="uploads/"):
        keys = [{"Key": o["Key"]} for o in pg.get("Contents", [])]
        if keys:
            s3().delete_objects(Bucket=env("BUCKET_NAME"), Delete={"Objects": keys, "Quiet": True})
            n += len(keys)
    return [f"Deleted {n} uploaded objects (old versions expire after 1 day by the lifecycle rule)."]


def status():
    resp = s3().list_objects_v2(Bucket=env("BUCKET_NAME"), Prefix="products/", MaxKeys=1000)
    return {"product images": resp.get("KeyCount", 0)}
