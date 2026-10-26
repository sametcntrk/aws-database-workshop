"""Amazon Keyspaces - wide column: user activity feed partitioned by user, clustered by time."""
import ssl
import time

import boto3
from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.concurrent import execute_concurrent_with_args
from cassandra.policies import DCAwareRoundRobinPolicy
from cassandra_sigv4.auth import SigV4AuthProvider

from ..base import Adapter, ReadResult, SeedResult, env, region

MODEL = """\
CREATE TABLE dbws.activity_by_user (
  user_id    text,
  event_time timestamp,
  event_id   uuid,
  event_type text,
  product_id text,
  detail     text,
  PRIMARY KEY ((user_id), event_time, event_id)
) WITH CLUSTERING ORDER BY (event_time DESC, event_id ASC);

Partition = one user; rows inside the partition are stored newest first."""


class Keyspaces(Adapter):
    engine_id = "keyspaces"
    title = "Amazon Keyspaces (for Apache Cassandra)"
    data_type = "Semi-structured"
    category = "Wide column"
    domain_slice = "kullanıcı aktivite akışı"
    why = ("Çok yüksek yazma hacmi olan, partition anahtarıyla okunan zaman sıralı veriler için (akış, IoT, log). "
           "Cassandra uyumlu (CQL), sunucusuz. Sorgu her zaman partition anahtarını içermeli; JOIN ve serbest filtre yok.")
    model = MODEL

    def __init__(self):
        self.ks, self.table = env("KEYSPACE"), env("TABLE_NAME")
        self._session = None

    def _s(self):
        if self._session is None:
            host = f"cassandra.{region()}.amazonaws.com"
            ctx = ssl.create_default_context()          # Amazon Trust Services roots from the OS store
            auth = SigV4AuthProvider(boto3.Session(region_name=region()))
            profile = ExecutionProfile(consistency_level=ConsistencyLevel.LOCAL_QUORUM,
                                       load_balancing_policy=DCAwareRoundRobinPolicy(local_dc=region()))
            # the driver connects to the endpoint ENI IPs it learns from system.peers, so the certificate
            # is checked against the service host name instead of the IP
            cluster = Cluster([host], port=9142, ssl_context=ctx, ssl_options={"server_hostname": host}, auth_provider=auth,
                              execution_profiles={EXEC_PROFILE_DEFAULT: profile}, protocol_version=4)
            self._session = cluster.connect()
        return self._session

    def seed(self, ds):
        s = self._s()
        users = sorted({c["customer_id"] for c in ds.customers})
        delete = s.prepare(f"DELETE FROM {self.ks}.{self.table} WHERE user_id = ?")
        self._write_all(s, delete, [(u,) for u in users])
        insert = s.prepare(f"INSERT INTO {self.ks}.{self.table} (user_id, event_time, event_id, event_type, product_id, detail) "
                           "VALUES (?, ?, ?, ?, ?, ?)")
        args = [(e["user_id"], e["event_time"], e["event_id"], e["event_type"], e["product_id"], e["detail"]) for e in ds.events]
        written, retried = self._write_all(s, insert, args)
        return SeedResult(
            summary=[f"{len(users)} kullanıcı partition'ı temizlendi (Keyspaces TRUNCATE desteklemez)",
                     f"{written} olay yazıldı (LOCAL_QUORUM, 32 eşzamanlı istek)",
                     f"{retried} istek zaman aşımı/kısıtlama sonrası yeniden denendi (yeni on-demand tablo kapasitesini kademeli artırır)"],
            operation=f"DELETE FROM {self.ks}.{self.table} WHERE user_id = ?;\n"
                      f"INSERT INTO {self.ks}.{self.table} (user_id, event_time, event_id, event_type, product_id, detail)\n"
                      "VALUES (?, ?, ?, ?, ?, ?);  -- prepared statement, SigV4 auth, TLS 9142",
            counts={"events": written, "retried": retried})

    @staticmethod
    def _write_all(session, stmt, args, concurrency=32, attempts=6):
        """Concurrent writes; rows that time out or are throttled are retried with backoff."""
        pending, retried = list(args), 0
        for attempt in range(attempts):
            results = execute_concurrent_with_args(session, stmt, pending, concurrency=concurrency, raise_on_first_error=False)
            failed = [a for a, (ok, _) in zip(pending, results) if not ok]
            if not failed:
                return len(args), retried
            retried += len(failed)
            pending = failed
            time.sleep(min(2 ** attempt, 10))
        raise RuntimeError(f"{len(pending)} writes still failing after {attempts} attempts")

    def read(self):
        cql = f"SELECT event_time, event_type, product_id, detail FROM {self.ks}.{self.table} WHERE user_id = 'C00001' LIMIT 20"
        rows = [(r.event_time, r.event_type, r.product_id, r.detail) for r in self._s().execute(cql)]
        return ReadResult(["event_time", "event_type", "product_id", "detail"], rows, cql + ";",
                          note="Tek partition okundu; satırlar diskte zaten en yeniden eskiye sıralı, ORDER BY gerekmez.")


ADAPTER = Keyspaces
