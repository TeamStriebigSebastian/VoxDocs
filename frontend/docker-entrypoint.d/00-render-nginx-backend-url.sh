#!/bin/sh
set -eu

TEMPLATE="/etc/nginx/conf.d/default.conf.template"
OUT="/etc/nginx/conf.d/default.conf"

# Default backend URL if not provided (safe local default; override in deployment)
: "${BACKEND_URL:=http://127.0.0.1:8000}"
export BACKEND_URL

if [ -f "$TEMPLATE" ]; then
  envsubst '${BACKEND_URL}' < "$TEMPLATE" > "$OUT"
fi
