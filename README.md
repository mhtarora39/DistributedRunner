# Distributed Runner

A clean, event-driven networking architecture in Python supporting text and multidimensional NumPy arrays over TCP sockets.

## Project Structure

```text
DistributedRunner/
├── core/
│   ├── connection.py    # Abstraction for threaded socket rx/tx
│   └── message.py       # Wire-serialization definition
├── nodes/
│   ├── client.py        # Terminal client script
│   └── server.py        # Terminal server script
├── doc/
│   └── ARCHITECTURE.md  # Detailed architectural overview
└── runner.py            # Transparent TCP proxy node
```

## How to run

The repository allows instances to connect as a standard server-client or with a transparent proxy ("runner") in between.

### Option 1: Direct Connection (Client ↔ Server)

1. **Start the server**
   ```bash
   python nodes/server.py --port 9000
   ```
2. **Start the client**
   ```bash
   python nodes/client.py --port 9000
   ```

### Option 2: Proxy Connection (Client ↔ Runner ↔ Server)

1. **Start the main server**
   ```bash
   python nodes/server.py --port 9000
   ```
2. **Start the runner**
   ```bash
   # Listens on 8000, proxies to 9000 (Default: --mode proxy)
   python runner.py --listen-port 8000 --target-port 9000

   # Alternately, you can run in isolated man-in-the-middle mode where 
   # no packets are automatically forwarded.
   python runner.py --listen-port 8000 --target-port 9000 --mode isolate
   ```
3. **Start the client**
   ```bash
   python nodes/client.py --port 8000
   ```

### Option 3: Cyclic Distributed Ring Benchmark

1. **Start the Ring Orchestrator (Windows Terminal)**
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\examples\start_ring_benchmark.ps1
   ```
   *This officially instantiates a localized cluster of identical `node.py` modules scaled via `--world-size` and `--rank`. The network dynamically binds downstream continuously whilst processing incoming upstream blocks asynchronously across `threading.Event()` loops to structurally prevent TCP Cycle deadlocks.*
   
   *Node 0 inherently evaluates the physical transmission validity (comparing MD5 or raw `np.sum()` checksums of the arrays perfectly tracking payload memory structures uncorrupted). It natively generates Round-Trip Time statistics across `p50`, `p95`, and `p99` latency bands guaranteeing baseline bounds before continuing!*

## Usage commands

Inside the interactive terminal of the **Client or Server**:
- **Type any text**: Sent as a standard UTF-8 string.
- **Type `!array`**: Sends a multidimensional NumPy array.

Inside the interactive terminal of the **Runner**:
- **`!c <text>`**: Send a string msg explicitly to the Client.
- **`!s <text>`**: Send a string msg explicitly to the Server.
- **`!b <text>`**: Broadcast a string msg to Both.
- **`!array`**: Broadcast a multidimensional NumPy array to Both.

## Architecture

Please review [doc/ARCHITECTURE.md](doc/ARCHITECTURE.md) to understand the wire framing protocol, the `Connection` abstraction, and type-tagging implementation.
