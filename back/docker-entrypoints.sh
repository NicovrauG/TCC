#!/usr/bin/env bash
set -e

# exemplo de espera simples pro Postgres (ajuste host/port conforme seu compose)
host="${DB_HOST:-db}"
port="${DB_PORT:-5432}"

echo "Aguardando banco em ${host}:${port}..."
# loop simples de espera
until nc -z "$host" "$port"; do
  echo "Esperando ${host}:${port}..."
  sleep 1
done

echo "Banco acessível. Iniciando aplicação..."
exec uvicorn app.server:app --host 0.0.0.0 --port 8000
