#!/bin/bash

# Default port
PORT=${1:-8000}
timeout=30
start_time=$(date +%s)

echo "Waiting for backend to start on port $PORT..."

while true; do
  if curl -s -f "http://localhost:$PORT/health" | grep -q "healthy"; then
    echo "Backend is ready on port $PORT"
    exit 0
  fi
  current_time=$(date +%s)
  elapsed=$((current_time - start_time))
  if [ $elapsed -ge $timeout ]; then
    echo "Timeout waiting for backend to start on port $PORT"
    exit 1
  fi
  sleep 1
done
