from flask import Flask, request, jsonify
import base64
from boto3.dynamodb.conditions import Key
import requests
import boto3
import json
import socket
import subprocess

ENCLAVE_PORT = 12345

def get_enclave_cid():
    result = subprocess.run(["nitro-cli", "describe-enclaves"], capture_output=True, text=True)
    enclaves = json.loads(result.stdout)
    return enclaves[0]["EnclaveCID"] if enclaves else None

def prepare_server_request(ciphertext : str):
    """
    Get the AWS credential from EC2 instance metadata
    """
    # 169.254.169.254 is a special IP address used by AWS to access instance metadata
    # This is only accessible from within the instance itself
    # The token is required for security reasons to access the metadata service
    token_url = "http://169.254.169.254/latest/api/token"
    token_headers = {"X-aws-ec2-metadata-token-ttl-seconds": "21600"}
    token_resp = requests.put(token_url, headers=token_headers)
    token = token_resp.text

    headers = {"X-aws-ec2-metadata-token": token}
    r = requests.get(
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
        headers=headers)
    instance_profile_name = r.text

    r = requests.get(
        "http://169.254.169.254/latest/meta-data/iam/security-credentials/%s" %
        instance_profile_name,
        headers=headers)

    response = r.json()

    print(ciphertext)

    credential = {
        'access_key_id': response['AccessKeyId'],
        'secret_access_key': response['SecretAccessKey'],
        'token': response['Token'],
        'region': 'eu-central-1',  # Adjust region as necessary
        'ciphertext': ciphertext
    }

    return credential



app = Flask(__name__)
@app.route('/verify', methods=['GET'])
def process_request():
    dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
    table = dynamodb.Table('wine-table')
    response = table.query(KeyConditionExpression=Key('ID').eq('1'))
    response_key = response['Items'][0]['Key']
    if not response_key:
        print("Inserted item not found in DynamoDB.")
        print(response_key)


    json_body = prepare_server_request(response_key)
    json_body['s'] = request.args.get('s')
    json_body['e'] = request.args.get('e')
    json_body['c'] = request.args.get('c')
    json_body = json.dumps(json_body)
    print(f"Original request:\n {json_body}")
    data=""
    cid=get_enclave_cid()
    print(f"Enclave CID: {cid}")
    try:
        if cid is None:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('127.0.0.1', ENCLAVE_PORT))
                s.sendall(bytes(json_body, 'utf-8'))
                print(f"Sent:\n {json_body}")
                data = s.recv(1024)
                print(f"Received: {data.decode()}")
                print("Finished sending messages.")
        else:
            with socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM) as s:
                s.connect((cid, ENCLAVE_PORT))
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
