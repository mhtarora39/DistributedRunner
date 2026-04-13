"""
Message struct used for all client ↔ server communication.

Wire format:
    [1 byte : type tag]
    [4 bytes: length (big-endian uint32)]  — length of the payload that follows
    [length bytes: payload]
"""

import struct
import socket
import json
from dataclasses import dataclass, field
from typing import Union

import numpy as np

# ── Type tags ────────────────────────────────────────────────────────────────
TAG_STRING: int = 0x01
TAG_NDARRAY: int = 0x02
TAG_CONTROL: int = 0x03


@dataclass
class Message:
    """A message struct representing typed payload layouts cleanly translated into byte frames."""
    data: Union[str, np.ndarray, dict]
    length: int
    _cached_payload: bytes = field(default=None, repr=False)

    # ── Constructors ─────────────────────────────────────────────────────

    @classmethod
    def from_string(cls, text: str) -> "Message":
        """Create a Message from a plain UTF-8 string."""
        encoded = text.encode("utf-8")
        return cls(data=text, length=len(encoded), _cached_payload=encoded)

    @classmethod
    def from_ndarray(cls, array: np.ndarray) -> "Message":
        """Create a Message from a NumPy array recursively framing its dtype and shape limits."""
        payload = _encode_ndarray(array)
        return cls(data=array, length=len(payload), _cached_payload=payload)
        
    @classmethod
    def from_control(cls, cmd: dict) -> "Message":
        """Create a System Control Message from a json dictionary."""
        payload = json.dumps(cmd).encode("utf-8")
        return cls(data=cmd, length=len(payload), _cached_payload=payload)

    # ── Serialisation ────────────────────────────────────────────────────

    def to_bytes(self) -> bytes:
        """Serialize the message for transmission. Format: [1-byte tag][4-byte uint32 length][payload]"""
        if isinstance(self.data, np.ndarray):
            tag = TAG_NDARRAY
            payload = self._cached_payload if self._cached_payload is not None else _encode_ndarray(self.data)
        elif isinstance(self.data, dict):
            tag = TAG_CONTROL
            payload = self._cached_payload if self._cached_payload is not None else json.dumps(self.data).encode("utf-8")
        else:
            tag = TAG_STRING
            payload = self._cached_payload if self._cached_payload is not None else self.data.encode("utf-8")

        # Network Byte Order (!I prevents 32-bit endianness failure). I allows max 4GB per frame.
        header = struct.pack("!BI", tag, len(payload))
        return header + payload

    # ── Deserialisation ──────────────────────────────────────────────────

    @classmethod
    def from_socket(cls, sock: socket.socket) -> "Message | None":
        """Strictly decodes the Byte stream buffer recursively against matching type tags."""
        header = _recv_exact(sock, 5)
        if header is None:
            return None

        tag, length = struct.unpack("!BI", header)

        raw = _recv_exact(sock, length)
        if raw is None:
            return None

        if tag == TAG_NDARRAY:
            data = _decode_ndarray(raw)
        elif tag == TAG_CONTROL:
            data = json.loads(raw.decode("utf-8"))
        else:
            data = raw.decode("utf-8")

        return cls(data=data, length=length, _cached_payload=raw)

    def __repr__(self) -> str:
        if isinstance(self.data, np.ndarray):
            return f"Message(type=ndarray, dtype={self.data.dtype}, shape={self.data.shape}, length={self.length})"
        elif isinstance(self.data, dict):
            return f"Message(type=control_json, length={self.length}, data={self.data})"
        return f"Message(type=string, length={self.length}, data={self.data!r})"


# ── Internal encoding tools ──────────────────────────────────────────────────

def _encode_ndarray(array: np.ndarray) -> bytes:
    """Encode a NumPy array securely down to un-typed bytes stream limit: ``dtype[2B]|shape[2B]|raw_data``."""
    dtype_bytes = str(array.dtype).encode("utf-8")
    shape_bytes = ",".join(str(d) for d in array.shape).encode("utf-8")
    raw = array.tobytes()
    return (
        struct.pack("!H", len(dtype_bytes)) + dtype_bytes
        + struct.pack("!H", len(shape_bytes)) + shape_bytes
        + raw
    )

def _decode_ndarray(payload: bytes) -> np.ndarray:
    """Decode offset-based raw buffers back into formatted read-write NumPy objects safely."""
    offset = 0
    (dtype_len,) = struct.unpack_from("!H", payload, offset)
    offset += 2
    dtype_str = payload[offset: offset + dtype_len].decode("utf-8")
    offset += dtype_len

    (shape_len,) = struct.unpack_from("!H", payload, offset)
    offset += 2
    shape_str = payload[offset: offset + shape_len].decode("utf-8")
    offset += shape_len
    shape = tuple(int(d) for d in shape_str.split(","))

    raw = payload[offset:]
    
    # We enforce .copy() on the resulting layout because numpy buffer targets from memory are read-only!
    # Assignment violations like RMSNorm passes will crash randomly unless duplicated independently.
    return np.frombuffer(raw, dtype=np.dtype(dtype_str)).reshape(shape).copy()

def _recv_exact(sock: socket.socket, num_bytes: int) -> bytes | None:
    """Consumes sequentially over bytearray loops. Blocks silently resolving packet stream tearing failures."""
    buf = bytearray()
    while len(buf) < num_bytes:
        chunk = sock.recv(num_bytes - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)
