# TODO: Rewrite package manager to be alpine compatible
FROM amazonlinux:2
# Copy file into container
WORKDIR /app

COPY enclave.py ./
# COPY traffic_forwarder.py ./
COPY run_inside_docker.sh ./
COPY kmstool_enclave_cli ./
COPY libnsm.so ./

ENV AWS_STS_REGIONAL_ENDPOINTS=regional
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/app

# Install dependencies
RUN yum update -y \
    && yum install -y iproute gcc python3 python3-devel libffi-devel \
    && python3 -m pip install --no-cache-dir pycryptodome boto3 \
    && yum clean all

# Expose socket port
EXPOSE 12345

RUN chmod +x run_inside_docker.sh

CMD [ "/app/run_inside_docker.sh" ]