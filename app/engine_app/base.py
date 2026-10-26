"""Adapter contract shared by the ten Engine Apps."""
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache

import boto3


@dataclass
class SeedResult:
    summary: list                 # human-readable lines: what was written
    operation: str                # the statements/API calls used, shown on the page
    counts: dict = field(default_factory=dict)


@dataclass
class ReadResult:
    columns: list
    rows: list
    query: str                    # the query/API call used, shown on the page
    note: str = ""
    images: list = field(default_factory=list)   # data URLs (S3 only)


class Adapter:
    engine_id = ""
    title = ""                    # e.g. "Amazon Aurora PostgreSQL"
    data_type = ""                # Structured / Semi-structured / Unstructured
    category = ""                 # Relational, Key-value, ...
    domain_slice = ""             # part of the e-commerce Domain this Engine holds
    why = ""                      # when to choose this Engine (Turkish)
    model = ""                    # data model shown on the page (Turkish + code)

    def seed(self, ds) -> SeedResult:
        raise NotImplementedError

    def read(self) -> ReadResult:
        raise NotImplementedError


def env(name, default=None):
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"environment variable {name} is not set (see /etc/engine-app.env)")
    return value


def region():
    return env("AWS_REGION", "eu-central-1")


@lru_cache(maxsize=None)
def secret(arn):
    """Secrets Manager JSON secret (read through the interface endpoint)."""
    value = boto3.client("secretsmanager", region_name=region()).get_secret_value(SecretId=arn)["SecretString"]
    return json.loads(value)
