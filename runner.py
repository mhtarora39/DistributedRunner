"""
TCP Runner (Proxy) — acts as both a server and a client.
It receives connections from a client, connects to a downstream server,
and forwards messages between them.

Usage:
    python runner.py [--listen-host HOST] [--listen-port PORT] [--target-host HOST] [--target-port PORT]
"""

import socket
import argparse
import time

from core.message import Message
from core.connection import Connection


def start_runner(listen_host: str, listen_port: int, target_host: str, target_port: int) -> None:
    # 1. Listen for client (act as server)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((listen_host, listen_port))
        server_socket.listen(1)
    except OSError as e:
        print(f"[ERROR] Could not bind to {listen_host}:{listen_port}: {e}")
        return

    print(f"[RUNNER] Listening for client on {listen_host}:{listen_port} …")
    
    try:
        client_sock, client_addr = server_socket.accept()
    except KeyboardInterrupt:
        print("\n[RUNNER] Shutting down …")
        server_socket.close()
        return
        
    print(f"[RUNNER] Client connected from {client_addr}\n")
    
    # 2. Connect to target server (act as client)
    target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"[RUNNER] Connecting to target server at {target_host}:{target_port} …")
    
    try:
        target_socket.connect((target_host, target_port))
    except ConnectionRefusedError:
        print(f"[ERROR] Could not connect to target server — is it running on {target_port}?")
        client_sock.close()
        server_socket.close()
        return

    print(f"[RUNNER] Connected to target server.\n")
    print("Runner is now proxying messages. Press Ctrl+C to stop.\n")

    # 3. Setup proxy connections using our new abstraction
    client_conn = Connection(client_sock)
    server_conn = Connection(target_socket)

    # Handlers for forwarding data
    def on_client_msg(c: Connection, msg: Message):
        print(f"[CLIENT -> SERVER] Forwarding message of length {msg.length}")
        server_conn.send(msg)

    def on_server_msg(c: Connection, msg: Message):
        print(f"[SERVER -> CLIENT] Forwarding message of length {msg.length}")
        client_conn.send(msg)

    def on_disconnect(c: Connection):
        print("\n[INFO] A connection dropped. Tearing down proxy...")
        # Since it is a proxy, if one drops, both drop.
        client_conn.close()
        server_conn.close()

    # Assign callbacks
    client_conn.on_message = on_client_msg
    client_conn.on_disconnect = on_disconnect
    
    server_conn.on_message = on_server_msg
    server_conn.on_disconnect = on_disconnect

    # Start listening to both
    client_conn.start()
    server_conn.start()

    try:
        # Keep main thread alive
        while client_conn.is_connected and server_conn.is_connected:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[RUNNER] Shutting down …")
    finally:
        client_conn.close()
        server_conn.close()
        server_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TCP Runner (Proxy)")
    parser.add_argument("--listen-host", default="127.0.0.1", help="Host to listen on")
    parser.add_argument("--listen-port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--target-host", default="127.0.0.1", help="Target server host")
    parser.add_argument("--target-port", type=int, default=9000, help="Target server port")
    args = parser.parse_args()

    start_runner(args.listen_host, args.listen_port, args.target_host, args.target_port)
