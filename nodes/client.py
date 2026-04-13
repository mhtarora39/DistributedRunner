"""
TCP Client — connects to the server, then enters an interactive
send / receive loop.  Supports sending both text and NumPy arrays.

Usage:
    python client.py [--host HOST] [--port PORT]
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


def start_client(host: str, port: int) -> None:
    """Connect to the TCP server and handle interactive messaging."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"[CLIENT] Connecting to {host}:{port} …")
    
    try:
        client_socket.connect((host, port))
    except ConnectionRefusedError:
        print("[ERROR] Could not connect — is the server running?")
        return

    print(f"[CLIENT] Connected to server at {host}:{port}\n")
    print("Commands:  type text to send a string,  '!array' to send a sample NumPy array")
    print("Press Ctrl+C to quit.\n")

    # Wrap the raw socket in our Connection abstraction
    conn = Connection(client_socket)

    def on_message(c: Connection, msg: Message):
        print(f"\n[SERVER] {msg}")
        if isinstance(msg.data, np.ndarray):
            print(f"         array =\n{msg.data}")
        print("You (client) > ", end="", flush=True)

    def on_disconnect(c: Connection):
        print("\n[INFO] Server closed the connection.")
        print("Press Enter to exit...")

    conn.on_message = on_message
    conn.on_disconnect = on_disconnect
    conn.start()

    try:
        while conn.is_connected:
            text = input("You (client) > ")
            if not text or not conn.is_connected:
                continue

            if text.strip() == "!array":
                arr = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int32)
                msg = Message.from_ndarray(arr)
                print(f"[CLIENT] Sending array {arr.shape} dtype={arr.dtype}")
            else:
                msg = Message.from_string(text)

            conn.send(msg)
    except (KeyboardInterrupt, EOFError):
        print("\n[CLIENT] Disconnecting …")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple TCP Client")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=9000, help="Server port")
    args = parser.parse_args()
    
    start_client(args.host, args.port)
