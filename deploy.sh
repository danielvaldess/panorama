#!/usr/bin/env bash
# Despliegue del proyecto del hackathon (rama main).
set -euo pipefail
umask 022
cd "$(dirname "$0")"

echo "==> 1/2 Actualizando código"
git pull --ff-only origin main

if [ -f docker-compose.yml ]; then
  echo "==> 2/2 Construyendo y levantando contenedores"
  docker compose up -d --build --remove-orphans
  docker compose ps
else
  echo "==> Sin docker-compose.yml todavía: no hay nada que desplegar."
fi
