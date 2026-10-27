"""Amazon S3 - blob: product images (served to every page), the seller panel upload and the gallery."""
import re
import time
from functools import lru_cache
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from flask import Response, jsonify, request

from .. import catalog, trace
from ..base import env, region
from ..visitor import visitor_id

META = catalog.META["s3"]
PAGES = catalog.PAGES["s3"]
PHOTOS = Path(__file__).resolve().parent.parent / "static" / "products"   # Wikimedia Commons photos, see CREDITS.md
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


def photo_slug(product_type):
    return product_type.lower().translate(str.maketrans("ıişğüöç ", "iisguoc-"))


@lru_cache(maxsize=1)
def credits():
    """Product type -> (author, licence) from CREDITS.md, stored as S3 user metadata."""
    out = {}
    for line in (PHOTOS / "CREDITS.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == 4 and cells[0] not in ("Product type", "---"):
            out[cells[0]] = (cells[2], cells[3])
    return out


def photo(product):
    """The photo bytes for a product: one Commons photo per product type."""
    return (PHOTOS / f"{photo_slug(product.get('type', ''))}.jpg").read_bytes()


def register(bp):
    @bp.get("/api/img/<pid>")
    def api_img(pid):
        if not re.fullmatch(r"P\d{4}", pid):
            return Response(status=404)
        try:
            obj = s3().get_object(Bucket=env("BUCKET_NAME"), Key=f"products/{pid}.jpg")
        except ClientError:
            return Response(status=404)
        return Response(obj["Body"].read(), mimetype="image/jpeg", headers={"Cache-Control": "public, max-age=300"})

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
        key = f"products/{pid}.jpg"
        with trace.call("generate_presigned_url", f"s3.generate_presigned_url('get_object', Params={{'Key': '{key}'}}, ExpiresIn=300)",
                        {"expires_in": "300 s"}) as t:
            url = s3().generate_presigned_url("get_object", Params={"Bucket": env("BUCKET_NAME"), "Key": key}, ExpiresIn=300)
            t.result(note="No request goes to S3 here: the app only signs a URL. The browser then downloads straight from S3, "
                     "so the Engine App does not carry the bytes. The bucket stays private.")
        return jsonify(trace.payload({"url": url}))


def seed(ds):
    bucket = env("BUCKET_NAME")
    with trace.call("DeleteObjects + PutObject × N",
                    f"s3.delete_objects(products/*); {len(ds.products)} × s3.put_object(Key='products/<id>.jpg', ContentType='image/jpeg', Metadata=...)",
                    {}) as t:
        for pg in s3().get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix="products/"):
            keys = [{"Key": o["Key"]} for o in pg.get("Contents", [])]
            if keys:
                s3().delete_objects(Bucket=bucket, Delete={"Objects": keys, "Quiet": True})
        total = 0
        for p in ds.products:
            body = photo(p)
            total += len(body)
            author, licence = credits().get(p.get("type"), ("unknown", "see CREDITS.md"))
            s3().put_object(Bucket=bucket, Key=f"products/{p['product_id']}.jpg", Body=body, ContentType="image/jpeg",
                            Metadata={"name": ascii_text(p["name"]), "category": ascii_text(p["category"]),
                                      "author": ascii_text(author)[:100], "license": ascii_text(licence),
                                      "source": "Wikimedia Commons"})
        t.result(items=len(ds.products))
    return [f"Wrote {len(ds.products)} product photos ({total // 1024} KB) from Wikimedia Commons, with author and licence metadata."]


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


def learn_overview(lesson, focus):
    """101: the bucket's keys by prefix. Your uploads and the objects of the call are marked."""
    mine = f"uploads/{visitor_id()}/"
    f = set(focus)
    groups, total, size = {}, 0, 0
    with trace.call("ListObjectsV2", "s3.list_objects_v2(Bucket=..., Prefix='products/' | 'uploads/')", {}) as t:
        for prefix in ("products/", "uploads/"):
            resp = s3().list_objects_v2(Bucket=env("BUCKET_NAME"), Prefix=prefix, MaxKeys=400)
            for o in resp.get("Contents", []):
                total += 1
                size += o["Size"]
                label = "Your uploads" if o["Key"].startswith(mine) else ("products/" if prefix == "products/" else "uploads/ (other visitors)")
                groups.setdefault(label, []).append(o["Key"])
        t.result(items=total)
    hit = lambda k: k in f or k.startswith(mine) or any(k.endswith(f"/{x}.jpg") for x in f)
    order = ["Your uploads", "products/", "uploads/ (other visitors)"]
    return {"title": "S3: the product image bucket", "text": "Each square is one object. The shelves are key prefixes. They look like folders, but S3 has no folders.",
            "facts": [[total, "objects"], [f"{size / 1048576:.1f} MB", "total"], ["versioning", "on"], [sum(1 for ks in groups.values() for k in ks if hit(k)), "objects in your call"]],
            "groups": [{"label": g, "items": [{"id": k, "title": k, "hit": hit(k)} for k in sorted(groups[g], key=lambda k: (not hit(k), k))[:120]]}
                       for g in order if g in groups],
            "hit_label": "The objects that your call read or wrote"}


def learn_item(lesson, key):
    with trace.call("HeadObject", f"s3.head_object(Bucket=..., Key='{key}')", {}) as t:
        h = s3().head_object(Bucket=env("BUCKET_NAME"), Key=key)
        t.result(note="HEAD returns the metadata without the bytes.")
    rec = {"Key": key, "ContentLength (bayt)": h["ContentLength"], "ContentType": h.get("ContentType"), "ETag": h.get("ETag", "").strip('"'),
           "LastModified": h["LastModified"].isoformat(), "StorageClass": h.get("StorageClass", "STANDARD"), "VersionId": h.get("VersionId"),
           "ServerSideEncryption": h.get("ServerSideEncryption"), "Metadata (x-amz-meta-*)": h.get("Metadata", {})}
    return {"title": key.rsplit("/", 1)[-1], "sub": "One object: the bytes (not read here) and the metadata that describes them. Yellow: the key and the metadata that you wrote.",
            "record": rec, "marks": {"Key": "kept", "Metadata (x-amz-meta-*)": "kept"}}
