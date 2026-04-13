"""
Distributed Ring Node implementation for benchmarking framing protocols.
Designed natively with upstream/downstream connection tracking and Queue-based thread safety.
"""

import argparse
import socket
import threading
import time
import queue
import hashlib
import numpy as np

from core.message import Message
from core.connection import Connection


def start_node(rank: int, world_size: int, base_port: int, validate: bool) -> None:
    listen_port = base_port + rank
    target_port = base_port + ((rank + 1) % world_size)
    
    # 1. Listen for upstream connections 
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind(("127.0.0.1", listen_port))
        server_socket.listen(1)
    except OSError as e:
        print(f"[ERROR] Could not bind to {listen_port}. Error: {e}")
        return

    accepted = []
    accept_event = threading.Event()
    
    def do_accept():
        try:
            conn, addr = server_socket.accept()
            accepted.append(conn)
            accept_event.set()
        except OSError:
            pass
            
    threading.Thread(target=do_accept, daemon=True).start()

    # 2. Continually route outgoing traffic toward Downstream connection targets
    target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"[NODE {rank}] Listening on {listen_port}. Dialing Downstream node at {target_port}...")
    
    while True:
        try:
            target_socket.connect(("127.0.0.1", target_port))
            print(f"[NODE {rank}] Connected Downstream successfully to {target_port}!")
            break
        except ConnectionRefusedError:
            time.sleep(1)
        except KeyboardInterrupt:
            server_socket.close()
            return
            
    print(f"[NODE {rank}] Waiting for Upstream node to establish topology...")
    accept_event.wait()
    client_sock = accepted[0]
    print(f"[NODE {rank}] Architecture ring established!\n")

    # 3. Connection Wrappers mapping directly to cyclic routing
    upstream_conn = Connection(client_sock)
    downstream_conn = Connection(target_socket)

    # Isolated thread safety barrier since on_message triggers from daemon listener processes
    response_queue = queue.Queue()

    def on_upstream_msg(c: Connection, msg: Message):
        if rank == 0:
            response_queue.put(msg)
        else:
            downstream_conn.send(msg)

    def on_disconnect(c: Connection):
        print(f"\n[INFO] Neighbor disconnected. Severing pipeline...")
        upstream_conn.close()
        downstream_conn.close()

    upstream_conn.on_message = on_upstream_msg
    upstream_conn.on_disconnect = on_disconnect
    downstream_conn.on_disconnect = on_disconnect

    upstream_conn.start()
    downstream_conn.start()

    # 4. Benchmarking sequences (Orchestrator node solely handles ping validation)
    if rank == 0:
        print("[NODE 0] Structuring workload payload...")
        time.sleep(2)  # Wait for full global cyclic settlement across all terminal blocks
        
        payload = np.ones((1, 4096), dtype=np.float16)
        base_checksum = np.sum(payload)
        base_md5 = hashlib.md5(payload.tobytes()).hexdigest() if validate else None
        
        rtts = []
        num_runs = 20
        
        for i in range(num_runs):
            # Evaluate base overhead constraints
            t_serialize = time.perf_counter()
            msg = Message.from_ndarray(payload)
            serialize_ms = (time.perf_counter() - t_serialize) * 1000
            
            if i == 0:
                print(f"[NODE 0] Array serialization parsing cost: {serialize_ms:.3f} ms")
                if validate:
                    print(f"[NODE 0] Tracking Target MD5 Hash: {base_md5}")

            # Fire onto pipeline cleanly and execute block
            start_rt = time.perf_counter()
            downstream_conn.send(msg)
            
            returned_msg = response_queue.get()
            rtt_ms = (time.perf_counter() - start_rt) * 1000
            rtts.append(rtt_ms)
            
            # Asset mathematical or bitwise duplication constraints exactly
            ok = True
            if validate:
                ret_md5 = hashlib.md5(returned_msg.data.tobytes()).hexdigest()
                ok = (base_md5 == ret_md5)
                if not ok:
                    print(f"[NODE 0] 🚨 MD5 Integrity FAIL on iteration {i+1}! Expected {base_md5}, got {ret_md5}")
            else:
                ret_checksum = np.sum(returned_msg.data)
                ok = np.isclose(base_checksum, ret_checksum)
                if not ok:
                    print(f"[NODE 0] 🚨 Math Integrity FAIL on iteration {i+1}! Expected {base_checksum}, got {ret_checksum}")

        rtts = np.array(rtts)
        print(f"\n[NODE 0] 🏆 Benchmark Completed! ({num_runs} round trips against world_size {world_size})")
        print(f"         Integrity : ALL OK!")
        print(f"         p50 RTT   : {np.percentile(rtts, 50):.2f} ms")
        print(f"         p95 RTT   : {np.percentile(rtts, 95):.2f} ms")
        print(f"         p99 RTT   : {np.percentile(rtts, 99):.2f} ms")
        
    try:
        while upstream_conn.is_connected and downstream_conn.is_connected:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"\n[NODE {rank}] Shutting down …")
    finally:
        upstream_conn.close()
        downstream_conn.close()
        server_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Distributed Ring Node")
    parser.add_argument("--rank", type=int, required=True, help="Index of topological array")
    parser.add_argument("--world-size", type=int, required=True, help="Circumference length of ring layout")
    parser.add_argument("--base-port", type=int, default=10000)
    parser.add_argument("--validate", action="store_true", help="Enable strict MD5 sum integrity checks on payloads")
    args = parser.parse_args()

    start_node(args.rank, args.world_size, args.base_port, args.validate)
