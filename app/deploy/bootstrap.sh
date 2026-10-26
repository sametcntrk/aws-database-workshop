#!/bin/bash
# Installs and starts one Engine App. Called by EC2 UserData after /etc/engine-app.env is written
# and the repository is cloned to /opt/engine-app. Safe to run again (idempotent).
set -euxo pipefail

set -a
source /etc/engine-app.env
set +a
: "${ENGINE:?ENGINE is not set in /etc/engine-app.env}"

ROOT=/opt/engine-app
dnf install -y python3.11 python3.11-pip

if ! id engineapp >/dev/null 2>&1; then
  useradd --system --home-dir "$ROOT" --shell /sbin/nologin engineapp
fi

python3.11 -m venv "$ROOT/venv"
"$ROOT/venv/bin/pip" install --quiet --upgrade pip
# cassandra-driver: pure-Python install, no compiler needed on the instance
CASS_DRIVER_NO_CYTHON=1 CASS_DRIVER_NO_EXTENSIONS=1 \
  "$ROOT/venv/bin/pip" install --quiet -r "$ROOT/app/requirements/base.txt" -r "$ROOT/app/requirements/$ENGINE.txt"

# CA bundle for Amazon RDS / DocumentDB TLS
mkdir -p "$ROOT/certs"
curl -fsSL -o "$ROOT/certs/global-bundle.pem" https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

chown -R engineapp:engineapp "$ROOT"
install -m 0644 "$ROOT/app/deploy/engine-app.service" /etc/systemd/system/engine-app.service
systemctl daemon-reload
systemctl enable engine-app
systemctl restart engine-app

for i in $(seq 1 30); do
  if curl -fs "http://127.0.0.1:8000${URL_PREFIX}/health"; then
    echo "engine app ${ENGINE} is up"
    exit 0
  fi
  sleep 2
done
echo "engine app ${ENGINE} did not start; see: journalctl -u engine-app" >&2
exit 1
