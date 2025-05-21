#!/usr/bin/env bash
set +x
set -e

# This script is used to create a hello world enclave application using the hello app located at /usr/share/nitro_enclaves/examples/hello

docker build -t enclave-test .
nitro-cli build-enclave --docker-uri enclave-test:latest --output-file enclave-test.eif
nitro-cli run-enclave --cpu-count 2 --memory 1024 --enclave-cid 16 --eif-path enclave-test.eif --debug-mode
nitro-cli describe-enclaves