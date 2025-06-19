import socket
import base64
import json

VSOCK_HOST_CID = 3
VSOCK_PORT = 8000
# ciphertextBlob must be base64 encoded encrypted data to decrypt
ciphertext_blob_b64 = "BASE64_ENCRYPTED_DATA_HERE"

def get_attestation_doc():
    with open("/dev/attestation", "rb") as f:
        return base64.b64encode(f.read()).decode()

def decrypt_with_kms(attestation_doc, ciphertext_blob):
    payload = {
        "attestationDocument": attestation_doc,
        "ciphertextBlob": ciphertext_blob,
        # Include encryptionContext here if used in encryption
        "encryptionContext": {}
    }

    request_bytes = json.dumps(payload).encode()

    with socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM) as sock:
        sock.connect((VSOCK_HOST_CID, VSOCK_PORT))
        sock.sendall(request_bytes)

        response_bytes = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response_bytes += chunk

    return json.loads(response_bytes.decode())

def main():
    att_doc = get_attestation_doc()
    response = decrypt_with_kms(att_doc, ciphertext_blob_b64)

    plaintext_b64 = response.get("Plaintext")
    if plaintext_b64:
        plaintext = base64.b64decode(plaintext_b64)
        print("Decrypted plaintext (bytes):", plaintext)
    else:
        print("No plaintext in response:", response)

if __name__ == "__main__":
    main()
