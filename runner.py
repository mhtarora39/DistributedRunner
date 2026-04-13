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
import numpy as np

from core.message import Message
from core.connection import Connection


def start_runner(listen_host: str, listen_port: int, target_host: str, target_port: int, mode: str) -> None:
    import threading

    # 1. Listen for incoming loop connection
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((listen_host, listen_port))
        server_socket.listen(1)
    except OSError as e:
        print(f"[ERROR] Could not bind to {listen_host}:{listen_port}: {e}")
        return

    # Accept incoming connection concurrently to avoid cyclic deadlock
    accepted = []
    def do_accept():
        try:
            conn, addr = server_socket.accept()
            accepted.append(conn)
        except:
            pass
            
    accept_thread = threading.Thread(target=do_accept, daemon=True)
    accept_thread.start()

    # 2. Continually try to connect to the next node in the ring
    target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"[RUNNER] Listening on {listen_port}. Dialing downstream node at {target_port}...")
    
    while True:
        try:
            target_socket.connect((target_host, target_port))
            print(f"[RUNNER] Connected downstream successfully to {target_port}!")
            break
        except ConnectionRefusedError:
            time.sleep(1)
        except KeyboardInterrupt:
            server_socket.close()
            return
            
    print(f"[RUNNER] Waiting for upstream node to form loop on {listen_port}...")
    while not accepted:
        time.sleep(0.5)
        
    client_sock = accepted[0]
    print("[RUNNER] Network Loop Node fully established!\n")

    # 3. Setup proxy connections using our new abstraction
    client_conn = Connection(client_sock)
    server_conn = Connection(target_socket)

    # Handlers for data
    def on_client_msg(c: Connection, msg: Message):
        if mode == "proxy":
            print(f"\n[CLIENT -> SERVER] Forwarding message of length {msg.length}")
            server_conn.send(msg)
        else:
            print(f"\n[CLIENT] Intercepted message: {msg.data}")
        print("You (runner) > ", end="", flush=True)

    def on_server_msg(c: Connection, msg: Message):
        if mode == "proxy":
            print(f"\n[SERVER -> CLIENT] Forwarding message of length {msg.length}")
            client_conn.send(msg)
        else:
            print(f"\n[SERVER] Intercepted message: {msg.data}")
        print("You (runner) > ", end="", flush=True)

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

    print("Runner is proxying messages. You can also inject messages:")
    print("  !c <text>    -> send to Client")
    print("  !s <text>    -> send to Server")
    print("  !b <text>    -> send to Both")
    print("  !array       -> send numpy array to Both")
    print("Press Ctrl+C to quit.\n")

    # Start listening to both
    client_conn.start()
    server_conn.start()

    try:
        while client_conn.is_connected and server_conn.is_connected:
            text = input("You (runner) > ")
            if not text or not client_conn.is_connected or not server_conn.is_connected:
                continue

            if text.startswith("!c "):
                msg = Message.from_string(text[3:])
                client_conn.send(msg)
            elif text.startswith("!s "):
                msg = Message.from_string(text[3:])
                server_conn.send(msg)
            elif text.startswith("!b "):
                msg = Message.from_string(text[3:])
                client_conn.send(msg)
                server_conn.send(msg)
            elif text.strip() == "!array":
                arr = np.array([[9, 9], [9, 9]], dtype=np.int32)
                msg = Message.from_ndarray(arr)
                client_conn.send(msg)
                server_conn.send(msg)
                print(f"[RUNNER] Injected array {arr.shape} dtype={arr.dtype} to both.")
            else:
                print("Unknown command. Use: !c <msg>, !s <msg>, !b <msg>, or !array")
    except (KeyboardInterrupt, EOFError):
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
    parser.add_argument("--mode", choices=["proxy", "isolate"], default="proxy", 
                        help="proxy: actively forward messages. isolate: receive without forwarding.")
    args = parser.parse_args()

    start_runner(args.listen_host, args.listen_port, args.target_host, args.target_port, args.mode)
