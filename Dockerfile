# TODO: Rewrite package manager to be alpine compatible
FROM python:3.7.9-alpine3.12
# Set working directory
WORKDIR /app

# Copy file into container
COPY enclave.py .

# Install dependencies
RUN apk add --no-cache --virtual .build-deps \
    gcc musl-dev libffi-dev python3-dev \
    && pip install --no-cache-dir pycryptodome \
    && apk del .build-deps

# Expose socket port
EXPOSE 12345

# Run the Python script
CMD ["python3", "enclave.py"]

