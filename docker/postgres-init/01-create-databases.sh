#!/usr/bin/env bash
# Creates application databases on first cluster init (docker-entrypoint-initdb.d).
# CSV in POSTGRES_CREATE_DATABASES (names /^[a-zA-Z_][a-zA-Z0-9_]*$/).
#
# Existing ./db/postgres_data: init scripts do not re-run; create DBs by hand or reset the volume.

set -euo pipefail

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB (bootstrap database) is required}"

list="${POSTGRES_CREATE_DATABASES:-}"
[[ -z "${list//[[:space:]]/}" ]] && exit 0

while IFS= read -r db; do
  [[ -z "${db}" ]] && continue
  if [[ ! "${db}" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
    echo "error: invalid database name '${db}' (allowed: [a-zA-Z_][a-zA-Z0-9_]*)" >&2
    exit 1
  fi
  if [[ "${db}" == "${POSTGRES_DB}" ]]; then
    continue
  fi
  exists="$(psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" -tAc \
    "SELECT 1 FROM pg_database WHERE datname='${db}'")"
  if [[ "${exists}" == "1" ]]; then
    continue
  fi
  # db validated above; OWNER is postgres image default role (typically [a-z0-9_]+).
  psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname "${POSTGRES_DB}" \
    -c "CREATE DATABASE ${db} OWNER \"${POSTGRES_USER}\";"
done < <(
  echo "${list}" | tr ',' '\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | grep -v '^$' || true
)
