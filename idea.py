import socket
import ssl
import json
from botocore.awsrequest import AWSRequest
from botocore.credentials import InstanceMetadataProvider, InstanceMetadataFetcher
from botocore.auth import SigV4Auth

# Constants
VSOCK_HOST_CID = 3
VSOCK_PORT = 8000
REGION = "eu-central-1"
DYNAMODB_ENDPOINT = f"https://dynamodb.{REGION}.amazonaws.com"

def create_vsock_ssl_connection():
    """Establish TLS-over-vsock connection to the host"""
    vsock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
    vsock.connect((VSOCK_HOST_CID, VSOCK_PORT))
    context = ssl.create_default_context()
    return context.wrap_socket(vsock, server_hostname=f"dynamodb.{REGION}.amazonaws.com")

def get_aws_credentials():
    provider = InstanceMetadataProvider(
        iam_role_fetcher=InstanceMetadataFetcher(timeout=1000, num_attempts=2)
    )
    return provider.load()

def main():
    credentials = get_aws_credentials()

    # Example GetItem request body
    request_payload = {
        "TableName": "wine-table",
        "Key": {
            "ID": {
                "S": "0"
            }
        }
    }

    headers = {
        "Content-Type": "application/x-amz-json-1.0",
        "X-Amz-Target": "DynamoDB_20120810.GetItem"
    }

    request = AWSRequest(
        method="POST",
        url=DYNAMODB_ENDPOINT,
        data=json.dumps(request_payload),
        headers=headers
    )

    SigV4Auth(credentials, "dynamodb", REGION).add_auth(request)
    prepared = request.prepare()

    conn = create_vsock_ssl_connection()
    http_request = (
        f"{prepared.method} / HTTP/1.1\r\n"
        f"Host: dynamodb.{REGION}.amazonaws.com\r\n" +
        ''.join(f"{k}: {v}\r\n" for k, v in prepared.headers.items()) +
        "\r\n" +
        (prepared.body or "")
    )

    conn.sendall(http_request.encode())
    response = b""
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            break
        response += chunk

    print("DynamoDB Response:\n")
    print(response.decode())
    conn.close()

if __name__ == "__main__":
    main()
