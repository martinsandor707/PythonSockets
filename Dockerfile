# Use Amazon Linux 2 as base image
FROM amazonlinux:2
# Set working directory
WORKDIR /app

# Copy file into container
COPY enclave.py .

# Install dependencies
RUN yum update -y && \
    yum install -y python3 python3-pip && \
    python3 -m pip install --no-cache-dir pycryptodome && \
    yum clean all

# Expose socket port
EXPOSE 12345

# Run the Python script
CMD ["python3", "enclave.py"]

