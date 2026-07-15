#!/usr/bin/env bash

echo "=== Karen services ==="
systemctl is-active ollama || true
docker compose ps || true

echo
echo "=== Memory ==="
free -h

echo
echo "=== Swap ==="
swapon --show
