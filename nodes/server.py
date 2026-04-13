"""
TCP Server — listens for a client connection, then enters an interactive
send / receive loop so both sides can exchange messages freely.

Usage:
    python server.py [--host HOST] [--port PORT]
"""

import socket
import argparse
import numpy as np
import sys
import os

# Add parent directory to path so we can import 'core'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.message import Message
from core.connection import Connection


def start_server(host: str, port: int) -> None:
    """Start the TCP server and handle a single client connection."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(1)
    except OSError as e:
        print(f"[ERROR] Bind failed on {host}:{port}: {e}")
        return

    print(f"[SERVER] Listening on {host}:{port} …\n[SERVER] Waiting for a client to connect …\n")
    conn_sock, addr = server_socket.accept()
    print(f"[SERVER] Client connected from {addr}\n")
    print("Commands:  type text to send a string,  '!array' to send a sample NumPy array")
    print("Press Ctrl+C to quit.\n")

    # Create our abstraction
    conn = Connection(conn_sock)

    def on_message(c: Connection, msg: Message):
        print(f"\n[CLIENT {addr}] {msg}")
        if isinstance(msg.data, np.ndarray):
            print(f"         array =\n{msg.data}")
        print("You (server) > ", end="", flush=True)

    def on_disconnect(c: Connection):
        print(f"\n[INFO] Client {addr} disconnected.")
        print("Press Enter to exit...")

    conn.on_message = on_message
    conn.on_disconnect = on_disconnect
    conn.start()

    try:
        while conn.is_connected:
            text = input("You (server) > ")
            if not text or not conn.is_connected:
                continue

            if text.strip() == "!array":
                arr = np.arange(12, dtype=np.float64).reshape(3, 4)
                msg = Message.from_ndarray(arr)
                print(f"[SERVER] Sending array {arr.shape} dtype={arr.dtype}")
            else:
                msg = Message.from_string(text)

            conn.send(msg)
    except (KeyboardInterrupt, EOFError):
        print("\n[SERVER] Shutting down …")
    finally:
        conn.close()
        server_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple TCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=9000, help="Port to bind")
    args = parser.parse_args()
    
    start_server(args.host, args.port)
