#!/usr/bin/env bash
set +x
set -euo pipefail

# This script is used to create and run a Nitro Enclave using Docker.
# It assumes that the Nitro Enclaves CLI and Docker are already installed and configured.
# It also assumes that the user has the necessary permissions to run Docker and Nitro Enclaves commands.
# Since this ec2 instance is only supposed to run an enclave, I will include cleanup commands for docker images and containers.

# Stop all running containers
running_containers=$(docker ps -q)
if [[ -n "$running_containers" ]]; then
  echo "🛑 Stopping running containers..."
  docker stop $running_containers
else
  echo "✅ No running containers to stop."
fi

# Remove all stopped containers
if [[ -n "$all_containers" ]]; then
  echo "🗑️ Removing all containers..."
  docker rm $all_containers
  echo "✅ Removed containers: $all_containers"
else
  echo "✅ No containers to remove."
fi

all_images=$(docker images -a -q)
if [[ -z "$all_images" ]]; then
  echo "✅ No Docker images to remove."
else
  echo "🗑️ Removing all Docker images..."
  docker rmi -f $all_images
  echo "✅ Removed images: $all_images"
fi

docker build -t enclave-test .
echo "✅ Docker image 'enclave-test' built successfully."
nitro-cli build-enclave --docker-uri enclave-test:latest --output-file enclave-test.eif
echo "✅ Enclave image 'enclave-test.eif' built successfully."
nitro-cli run-enclave --cpu-count 2 --memory 1024 --enclave-cid 16 --eif-path enclave-test.eif --debug-mode
nitro-cli describe-enclaves