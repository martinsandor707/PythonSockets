import socket
import threading

PORT = 12345

def handle_client(client_socket, addr):
    print(f"Connected by {addr}")
    with client_socket:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            message = data.decode()
            response = f"Server echo: {message}"
            print(f"Received from {addr}: {message}")
            client_socket.sendall(response.encode())


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind(('localhost', PORT))
    server_socket.listen()
    print(f"Server listening on port {PORT}...")

    while True:
        client_socket, addr = server_socket.accept()
        # Start a new thread for each client
        client_thread = threading.Thread(target=handle_client, args=(client_socket, addr))
        client_thread.start()
        print(f"Started thread for {addr}")