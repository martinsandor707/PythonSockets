import socket
import threading
import json
from binascii import unhexlify, hexlify
from Crypto.Cipher import AES #pip install pycryptodome
from Crypto.Hash import CMAC

PORT = 12345
key = "00000000000000000000000000000000" # This is the placeholder key to be pushed to GitHub, change it in production

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
                "tamperstatus": status
            }

            client_socket.sendall(json.dumps(response).encode())


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind(('0.0.0.0', PORT))
    server_socket.listen()
    print(f"Server listening on port {PORT}...")

    while True:
        client_socket, addr = server_socket.accept()
        # Start a new thread for each client
        client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        client_thread.start()
        print(f"Started thread for {addr}")
