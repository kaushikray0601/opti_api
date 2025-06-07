#!/bin/bash

echo "Checking if Docker network 'shared_network' exists..."
if ! docker network ls | grep -q 'shared_network'; then
  echo "Creating shared network..."
  docker network create shared_network
else
  echo "shared_network already exists. Skipping creation."
fi

echo "Building and starting optimizer_api stack..."
docker compose --env-file .env -f optimizerAPI_docker-compose.yml up -d --build

echo "All done! Services should be up and running."
