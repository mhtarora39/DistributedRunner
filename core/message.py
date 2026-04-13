"""
Message struct used for all client ↔ server communication.

Wire format:
    [1 byte : type tag]
    [4 bytes: length (big-endian uint32)]  — length of the payload that follows
    [length bytes: payload]

Type tags:
    0x01 — UTF-8 string
    0x02 — NumPy array  (payload = dtype str + '|' + shape str + '|' + raw bytes)
"""

import struct
import socket
from dataclasses import dataclass
from typing import Union

import numpy as np

# ── Type tags ────────────────────────────────────────────────────────────────
TAG_STRING: int = 0x01
TAG_NDARRAY: int = 0x02


@dataclass
class Message:
    """A message with a data payload and its byte-length on the wire."""
    data: Union[str, np.ndarray]
    length: int

    # ── Constructors ─────────────────────────────────────────────────────

    @classmethod
    def from_string(cls, text: str) -> "Message":
        """Create a Message from a plain string."""
        encoded = text.encode("utf-8")
        return cls(data=text, length=len(encoded))

    @classmethod
    def from_ndarray(cls, array: np.ndarray) -> "Message":
        """Create a Message from a NumPy array."""
        payload = _encode_ndarray(array)
        return cls(data=array, length=len(payload))

    # ── Serialisation ────────────────────────────────────────────────────

    def to_bytes(self) -> bytes:
        """Serialize the message for transmission.

        Format: [1-byte tag][4-byte length][payload]
        """
        if isinstance(self.data, np.ndarray):
            tag = TAG_NDARRAY
            payload = _encode_ndarray(self.data)
        else:
            tag = TAG_STRING
            payload = self.data.encode("utf-8")

        header = struct.pack("!BI", tag, len(payload))  # 1 + 4 = 5 bytes
        return header + payload

    # ── Deserialisation ──────────────────────────────────────────────────

    @classmethod
    def from_socket(cls, sock: socket.socket) -> "Message | None":
        """Read a complete Message from a socket.

        Returns None if the connection is closed.
        """
        # Read the 5-byte header (1 tag + 4 length)
        header = _recv_exact(sock, 5)
        if header is None:
            return None

        tag, length = struct.unpack("!BI", header)

        # Read exactly `length` bytes of payload
        raw = _recv_exact(sock, length)
        if raw is None:
            return None

        if tag == TAG_NDARRAY:
            data = _decode_ndarray(raw)
        else:
            data = raw.decode("utf-8")

        return cls(data=data, length=length)

    # ── Display ──────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        if isinstance(self.data, np.ndarray):
            return (
                f"Message(type=ndarray, dtype={self.data.dtype}, "
                f"shape={self.data.shape}, length={self.length})"
            )
        return f"Message(type=string, length={self.length}, data={self.data!r})"


# ── NumPy helpers ────────────────────────────────────────────────────────────

def _encode_ndarray(array: np.ndarray) -> bytes:
    """Encode a NumPy array into bytes: ``dtype|shape|raw_data``."""
    dtype_bytes = str(array.dtype).encode("utf-8")
    shape_bytes = ",".join(str(d) for d in array.shape).encode("utf-8")
    raw = array.tobytes()
    # format: dtype_len(2) + dtype + shape_len(2) + shape + raw
    return (
        struct.pack("!H", len(dtype_bytes)) + dtype_bytes
        + struct.pack("!H", len(shape_bytes)) + shape_bytes
        + raw
    )


def _decode_ndarray(payload: bytes) -> np.ndarray:
    """Decode bytes produced by ``_encode_ndarray`` back into a NumPy array."""
    offset = 0

    # dtype
    (dtype_len,) = struct.unpack_from("!H", payload, offset)
    offset += 2
    dtype_str = payload[offset: offset + dtype_len].decode("utf-8")
    offset += dtype_len

    # shape
    (shape_len,) = struct.unpack_from("!H", payload, offset)
    offset += 2
    shape_str = payload[offset: offset + shape_len].decode("utf-8")
    offset += shape_len
    shape = tuple(int(d) for d in shape_str.split(","))

    # raw data
    raw = payload[offset:]
    return np.frombuffer(raw, dtype=np.dtype(dtype_str)).reshape(shape)


# ── Socket helper ────────────────────────────────────────────────────────────

def _recv_exact(sock: socket.socket, num_bytes: int) -> bytes | None:
    """Read exactly ``num_bytes`` from the socket, or return None on disconnect."""
    chunks: list[bytes] = []
    remaining = num_bytes
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            return None
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)
