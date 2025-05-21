import socket
import threading
import traceback
import json
from binascii import unhexlify, hexlify
from Crypto.Cipher import AES #pip install pycryptodome
from Crypto.Hash import CMAC

PORT = 12345
key = "00000000000000000000000000000000" # This is the placeholder key to be pushed to GitHub, we will use AWS KMS to get the real key

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

class VsockListener:
    """Server"""
    def __init__(self, conn_backlog=128):
        self.conn_backlog = conn_backlog

    def bind(self, port):
        """Bind and listen for connections on the specified port"""
        print(f"Listening on port {port}")
        self.sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
        self.sock.bind((socket.VMADDR_CID_ANY, port))
        self.sock.listen(self.conn_backlog)

    def recv_data(self):
        """Receive data from a remote endpoint"""
        while True:
            (from_client, (remote_cid, remote_port)) = self.sock.accept()
            # Read 1024 bytes at a time
            while True:
                try:
                    data = from_client.recv(1024)
                    if data:
                        message = json.loads(data.decode())
                        print(f"Received from CID {remote_cid}:\n {message}")
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

                        self.sock.sendall(json.dumps(response).encode())
                        from_client.close()
                except socket.error:
                    # Handle socket error (e.g., connection reset by peer)
                    print(f"Socket error occurred. Closing connection.\nStack trace:\n{traceback.format_exc()}")
                    break
                print()

    def send_data(self, data):
        """Send data to a renote endpoint"""
        while True:
            (to_client, (remote_cid, remote_port)) = self.sock.accept()
            to_client.sendall(data)
            to_client.close()


def server_handler():
    server = VsockListener()
    server.bind(PORT)
    server.recv_data()

if __name__ == "__main__":
    server_handler()