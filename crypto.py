from flask import Flask, request, jsonify
import re
from binascii import unhexlify, hexlify
from Crypto.Cipher import AES
from Crypto.Hash import CMAC


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
app = Flask(__name__)



@app.route('/verify', methods=['GET'])
def process_request():
    s = request.args.get('s')
    e = request.args.get('e')
    c = request.args.get('c')
    ###### key management
    key = "00000000000000000000000000000000"
    
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
    return jsonify({
        "s": s,
        "e": e,
        "c": c,
        "verify": MAC == c,
        "tamperstatus": status
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)