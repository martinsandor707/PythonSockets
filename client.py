import socket
import time
PORT = 12345
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('localhost', PORT))
        counter = 1
        while True:
            message = f"Message {counter}"
            s.sendall(bytes(message, 'utf-8'))
            print(f"Sent: {message}")
            data = s.recv(1024)
            print(f"Received: {data.decode()}")
            counter += 1
            time.sleep(1)
            if counter > 10:
                break
        print("Finished sending messages.")
        
except BrokenPipeError:
    print("The server closed connection.")
except ConnectionRefusedError:
    print("Connection refused. Please check if the server is running.")
