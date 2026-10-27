"""One module per Engine. Each module defines:

META            Engine descriptor shown in the Behind-the-Scenes Panel
PAGES           pages of this Engine (from catalog.py)
register(bp)    API routes under /<engine>/api/...
seed(ds)        writes the Shared Catalog slice of this Engine, returns summary lines
reset_visitors() deletes Visitor data, returns summary lines
status()        small dict for the Admin Console
"""

# On-demand list prices, EU (Frankfurt), from the AWS Price List API (2026-10).
PRICE_READ_RU = 0.1525 / 1_000_000    # DynamoDB and Keyspaces, per read request unit
PRICE_WRITE_RU = 0.7625 / 1_000_000   # DynamoDB and Keyspaces, per write request unit



def usd(value):
    """Format a very small dollar amount for the panel."""
    if value is None:
        return None
    return f"≈ ${value:.10f}".rstrip("0").rstrip(".") if value < 0.01 else f"≈ ${value:.4f}"


def clean(v):
    """A JSON-safe value: Decimal → float, datetime → ISO text, UUID and other objects → text."""
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, (list, tuple, set)):
        return [clean(x) for x in v]
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if hasattr(v, "as_integer_ratio"):
        return float(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return str(v)


def table(columns, rows, note=None, **extra):
    """Result of an E2E query as a table: {"columns": [...], "rows": [[...], ...]}."""
    return {"columns": list(columns), "rows": [[clean(v) for v in r] for r in rows], "note": note, **extra}
