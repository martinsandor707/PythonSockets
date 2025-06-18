#!/usr/bin/env bash
set +x
set -e

# This script is used to create and run a Nitro Enclave using Docker.
# It assumes that the Nitro Enclaves CLI and Docker are already installed and configured.
# It also assumes that the user has the necessary permissions to run Docker and Nitro Enclaves commands.

docker rmi -f $(docker images -a -q) # Remove all Docker images
docker build -t enclave-test .
nitro-cli build-enclave --docker-uri enclave-test:latest --output-file enclave-test.eif
nitro-cli run-enclave --cpu-count 2 --memory 1024 --enclave-cid 16 --eif-path enclave-test.eif --debug-mode
nitro-cli describe-enclaves