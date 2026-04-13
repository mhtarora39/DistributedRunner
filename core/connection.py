"""
Connection abstraction for handling socket communication and background receiving.
"""

import socket
import threading
from typing import Callable

from core.message import Message


class Connection:
    """Wraps a socket and manages background receiving and callbacks safely."""

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.is_connected = True
        self._lock = threading.Lock()
        
        # Callbacks that can be set by the user
        self.on_message: Callable[['Connection', Message], None] = lambda conn, msg: None
        self.on_disconnect: Callable[['Connection'], None] = lambda conn: None

        self._recv_thread = threading.Thread(target=self._receive_loop, daemon=True)

    def start(self) -> None:
        """Start the background receiving thread."""
        self._recv_thread.start()

    def send(self, msg: Message) -> bool:
        """Send a message. Returns True if successful, False if disconnected."""
        with self._lock:
            if not self.is_connected:
                return False
        
        try:
            self.sock.sendall(msg.to_bytes())
            return True
        except OSError:
            self.close()
            return False

    def close(self) -> None:
        """Close the socket and trigger disconnect handling if active."""
        with self._lock:
            if not self.is_connected:
                return
            self.is_connected = False
            
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
            
        try:
            self.sock.close()
        except OSError:
            pass

    def _receive_loop(self) -> None:
        """Continuously listen for incoming messages from the socket."""
        try:
            while True:
                with self._lock:
                    if not self.is_connected:
                        break
                msg = Message.from_socket(self.sock)
                if msg is None:
                    break
                self.on_message(self, msg)
        except ConnectionResetError:
            pass
        except OSError:
            pass
        finally:
            # We capture is_connected before close runs to ensure on_disconnect invokes exactly once
            should_notify = False
            with self._lock:
                should_notify = self.is_connected
                
            self.close()
            
            if should_notify:
                self.on_disconnect(self)
