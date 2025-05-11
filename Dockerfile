# Use official Python 3.12 image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy file into container
COPY enclave.py .

# Install dependencies
RUN pip install --no-cache-dir pycryptodome

# Expose socket port
EXPOSE 12345

# Run the Python script
CMD ["python3", "enclave.py"]

