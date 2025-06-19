import socket
import threading
import json
import base64
import subprocess
import boto3
from binascii import unhexlify, hexlify
from Crypto.Cipher import AES #pip install pycryptodome
from Crypto.Hash import CMAC

SERVER_PORT = 12345
KMS_PROXY_PORT = 8001
key = "00000000000000000000000000000000" # This is the placeholder key to be pushed to GitHub, we will use AWS KMS to get the real key

def get_plaintext(credentials):
    """
    prepare inputs and invoke decrypt function
    """

    # take all data from client
    access = credentials['access_key_id']
    secret = credentials['secret_access_key']
    token = credentials['token']
    ciphertext= credentials['ciphertext']
    region = credentials['region']
    creds = decrypt_cipher(access, secret, token, ciphertext, region)
    return creds

def decrypt_cipher(access, secret, token, ciphertext, region):
    """
    use KMS Tool Enclave Cli to decrypt cipher text
    Look at https://github.com/aws/aws-nitro-enclaves-sdk-c/blob/main/bin/kmstool-enclave-cli/README.md
    for more info.
    """
    proc = subprocess.Popen(
    [
        "/app/kmstool_enclave_cli",
        "decrypt",
        "--region", region,
        "--proxy-port", str(KMS_PROXY_PORT),
        "--aws-access-key-id", access,
        "--aws-secret-access-key", secret,
        "--aws-session-token", token,
        "--ciphertext", ciphertext,
        "--key-id", "alias/wine-encryption-key", #TODO: Check if kmstool supports key aliases. Otherwise need to hardcode key ID (Should be good tbh)
        "--encryption-algorithm", "RSAES_OAEP_SHA_256" # Must match key spec
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

    ret = proc.communicate()

    if ret[0]:
        ret0 = proc.communicate()[0].decode()
        b64text = ret0.split(":")[1]
        plaintext = base64.b64decode(b64text).decode('utf-8')
        return plaintext
    else:
        return "KMS Error. Decryption Failed." + str(ret) #returning the full error stack when something fails


key_alias = 'alias/wine-encryption-key'
kms = boto3.client('kms', region_name='eu-central-1')  # Adjust region as necessary

def kms_decrypt(ciphertext: str) -> str:
    try:
        ciphertext = base64.b64decode(ciphertext)
        response = kms.decrypt(
            KeyId=key_alias,
            CiphertextBlob=ciphertext,
            EncryptionAlgorithm='RSAES_OAEP_SHA_256'  # Must match key spec
        )
        return response['Plaintext'].decode() if 'Plaintext' in response else None
    except Exception as e:
        print(f"Error decrypting with KMS: {e}")
        return None


def calculate_cmac_hex(key_hex: str, data_hex: str) -> str:

    try:
        key = unhexlify(key_hex)  # Convert hex key to bytes
        data = unhexlify(data_hex)  # Convert hex data to bytes
        
       
        cmac = CMAC.new(key, ciphermod=AES)
        cmac.update(data)
        return hexlify(cmac.digest()).decode()
    
    except Exception as e:
        print(f"Error computing CMAC: {e}")
        return None
def calculate_cmac_hex_zero(key_hex: str) -> str:

    try:
        
        #key = unhexlify(key_hex)  # Convert hex key to bytes

        cmac = CMAC.new(key_hex, ciphermod=AES)
        cmac.update(b'')  # Zero-length input
        return hexlify(cmac.digest()).decode()
    
    except Exception as e:
        print(f"Error computing CMAC: {e}")
        return None


def calculate_truncated_cmac(key_hex: str) -> str:

    key = unhexlify(key_hex)  
    
    full_cmac = calculate_cmac_hex_zero(key)  # Compute full CMAC
    truncated_cmac = full_cmac  # Take the first 8 bytes
    
    return truncated_cmac
    
def extract_alternate_bytes(hex_string: str) -> str:
    return "".join(hex_string[i:i+2] for i in range(2, len(hex_string), 4))

def handle_client(client_socket, addr):
    print(f"Connected by {addr}")
    with client_socket:
        data = client_socket.recv(1024)
        if data:
            message = json.loads(data.decode())
            print(f"Received from {addr}:\n {message}")
            s= message['s']
            e= message['e']
            c= message['c']
            secret = message['ciphertext'] if 'ciphertext' in message else None
            plaintext = None
            if secret:
                plaintext = get_plaintext(message)

            encrypted_data = bytes.fromhex(e)
            cipher = AES.new(bytes.fromhex(key), AES.MODE_ECB)
            decrypted_data = cipher.decrypt(encrypted_data).hex().upper()
            
            uid = decrypted_data[2:16]
            sdmcount = decrypted_data[16:22]
            
            mac_key = f"3CC300010080{uid}{sdmcount}"
            
            cmac_result = calculate_cmac_hex(key, mac_key)
            
            MAC = extract_alternate_bytes(calculate_truncated_cmac(cmac_result).upper())
            status = ""
            if s == "CC":
                status = "Not tampered!"
            elif s == "OO":
                status = "Tampered!"
            elif s == "OI":
                status = "Manipulated"
            elif s == "II":
                status = "Config error"
            else:
                status = "General error"
            
            response = {
                "s": s,
                "e": e,
                "c": c,
                "verify": MAC == c,
                "tamperstatus": status,
                "ciphertext": secret if secret else None,
                "plaintext": plaintext if plaintext else None,
            }

            client_socket.sendall(json.dumps(response).encode())


with socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((socket.VMADDR_CID_ANY, SERVER_PORT))
    server_socket.listen()
    print(f"Enclave listening on port {SERVER_PORT}...")

    while True:
        client_socket, addr = server_socket.accept()
        # Start a new thread for each client
        client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        client_thread.start()
        print(f"Started thread for {addr}")