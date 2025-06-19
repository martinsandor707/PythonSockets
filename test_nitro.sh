#!/usr/bin/env bash
set +x
set -euo pipefail

# This script is used to create and run a Nitro Enclave using Docker, as well as create a vsock-proxy to forward traffic to the AWS KMS service.
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

all_containers=$(docker ps -a -q)
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

PID=$(pgrep -f vsock-proxy)

if [ -z "$PID" ]; then
    echo "No vsock-proxy processes are currently running."
else
    echo "Found vsock-proxy process(es) with PID(s): $PID"
    echo "Stopping vsock-proxy processes..."
    kill $PID
    # Wait a moment and verify they were stopped
    sleep 1
    if pgrep -f vsock-proxy >/dev/null; then
        echo "Warning: Some vsock-proxy processes did not terminate gracefully."
        echo "Attempting to force kill..."
        kill -9 $PID
        sleep 1
        if pgrep -f vsock-proxy >/dev/null; then
            echo "Error: Failed to stop all vsock-proxy processes."
            exit 1
        else
            echo "Successfully force-stopped all vsock-proxy processes."
        fi
    else
        echo "Successfully stopped all vsock-proxy processes."
    fi
fi

vsock-proxy 11111 kms.eu-central-1.amazonaws.com 443
echo "✅ Started vsock-proxy to forward traffic from port 11111 to kms.eu-central-1.amazonaws.com:443."

nitro-cli run-enclave --cpu-count 2 --memory 1024 --enclave-cid 16 --eif-path enclave-test.eif --debug-mode
nitro-cli describe-enclaves