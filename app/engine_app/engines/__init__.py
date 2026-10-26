"""One module per Engine. Each module defines:

META            Engine descriptor shown in the Behind-the-Scenes Panel
PAGES           Storefront Section and Report Screen pages ({id, template, title, paths})
register(bp)    API routes under /<engine>/api/...
seed(ds)        writes the Shared Catalog slice of this Engine, returns summary lines
reset_visitors() deletes Visitor data, returns summary lines
status()        small dict for the Admin Console
"""

# On-demand list prices, EU (Frankfurt), from the AWS Price List API (2026-10).
PRICE_READ_RU = 0.1525 / 1_000_000    # DynamoDB and Keyspaces, per read request unit
PRICE_WRITE_RU = 0.7625 / 1_000_000   # DynamoDB and Keyspaces, per write request unit


def page(pid, template, title, *paths):
    return {"id": pid, "template": template, "title": title, "paths": list(paths)}


def usd(value):
    """Format a very small dollar amount for the panel."""
    if value is None:
        return None
    return f"≈ ${value:.10f}".rstrip("0").rstrip(".") if value < 0.01 else f"≈ ${value:.4f}"
