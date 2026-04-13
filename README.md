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
2. **Start the runner (proxy)**
   ```bash
   # Listens for clients on port 8000, proxies packets to port 9000
   python runner.py --listen-port 8000 --target-port 9000
   ```
3. **Start the client**
   ```bash
   python nodes/client.py --port 8000
   ```

## Usage commands

Inside the interactive terminal of the Client or Server:
- **Type any text**: Sent as a standard UTF-8 string.
- **Type `!array`**: Sends a multidimensional NumPy array to prove dynamic serialization over the socket.

## Architecture

Please review [doc/ARCHITECTURE.md](doc/ARCHITECTURE.md) to understand the wire framing protocol, the `Connection` abstraction, and type-tagging implementation.
