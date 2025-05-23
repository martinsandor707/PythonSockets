from flask import Flask, request, jsonify
import json
import socket
import subprocess

PORT = 12345

def get_enclave_cid():
    result = subprocess.run(["nitro-cli", "describe-enclaves"], capture_output=True, text=True)
    enclaves = json.loads(result.stdout)
    return enclaves[0]["EnclaveCID"] if enclaves else None

# def start_vsock_proxy():
#     # Start vsock proxy in the background
#     subprocess.Popen(["nitro-cli", "vsock-proxy", "--port", str(PORT)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)



app = Flask(__name__)
@app.route('/verify', methods=['GET'])
def process_request():
    s = request.args.get('s')
    e = request.args.get('e')
    c = request.args.get('c')
    json_body = {
        "s": s,
        "e": e,
        "c": c
    }
    json_body = json.dumps(json_body)
    print(f"Original request:\n {json_body}")
    data=""
    cid=get_enclave_cid()
    print(f"Enclave CID: {cid}")
    try:
        if cid is None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', PORT))
                s.sendall(bytes(json_body, 'utf-8'))
                print(f"Sent:\n {json_body}")
                data = s.recv(1024)
                print(f"Received: {data.decode()}")
                print("Finished sending messages.")
        else:
            with socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM) as s:
                s.connect((cid, PORT))
                s.sendall(bytes(json_body, 'utf-8'))
                print(f"Sent:\n {json_body}")
                data = s.recv(1024)
                print(f"Received: {data.decode()}")
                print("Finished sending messages.")
            
    except BrokenPipeError:
        print("The server closed connection.")
    except ConnectionRefusedError:
        print("Connection refused. Please check if the server is running.")
        
    return jsonify(json.loads(data.decode()))

if __name__ == '__main__':
    app.run(debug=True)
