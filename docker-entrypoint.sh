#!/bin/sh
# Hosted volumes (Railway, Render) mount root-owned over DATA_DIR: fix ownership, then drop root.
set -e
if [ "$(id -u)" = "0" ]; then
  mkdir -p "$DATA_DIR"
  chown -R measulor:measulor "$DATA_DIR"
  exec setpriv --reuid=measulor --regid=measulor --init-groups "$@"
fi
exec "$@"
