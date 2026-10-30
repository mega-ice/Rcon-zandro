#!/usr/bin/env python3
# Zandronum RCON client (with CLI args + persistent command history)

import hashlib
import socket
import threading
import os
import time
import ipaddress
from io import BytesIO
import sys
import argparse
from pathlib import Path
import re
from typing import Union, Sequence

import huffman
import headers
from headers import clrc, protocol_ver

# Network constants
MAX_PACKET_SIZE = 4096
SOCKET_TIMEOUT = 4.0
BATCH_RESPONSE_DELAY = 2.0

# ================================
# CONFIGURATION SECTION
# ================================

# RCON password - set via environment variable.
# Usage:
#   RCON_PASSWORD=your_password python3 rcon_client.py <ip> <port>
RCON_PASSWORD: str | None = os.environ.get("RCON_PASSWORD")

# ================================
# COLOR STRIPPING UTILITY
# ================================
# Strip Zandronum color codes (e.g. \c[uh0], \c[0;35m) from server text.
COLOR_PATTERN = re.compile(r"\\c\[[0-9;uhA-Za-z\-]*m\]?|\\c\[[0-9;uhA-Za-z\-]*\]?|\\c\[[0-9;uhA-Za-z\-]*|\\c[a-zA-Z0-9\-]")

# Match the server's command-echo packet (e.g. "-> map dmmap1 (RCON by Bob@10.10.0.3:37325)").
# In batch/CI mode this echo is suppressed so only the real answer is printed.
CMD_ECHO_PATTERN = re.compile(r"^-> .+ \(RCON by .+\)$")

# Capture the current client's attribution from the LoggedIn log blob
# (e.g. "[..] RCON client at 10.10.0.3:45762 connected.").
CMD_IDENTITY_PATTERN = re.compile(r"RCON client at (\d+\.\d+\.\d+\.\d+:\d+) connected")

def strip_colors(text: str) -> str:
    """Strip ANSI/RCON color escape sequences from server messages."""
    return COLOR_PATTERN.sub("", text)

# ================================
# PERSISTENT HISTORY
# ================================
HISTORY_FILE = Path.home() / ".rcon_history"
MAX_HISTORY = 1000  # Max lines to keep

try:
    import readline
except ImportError:
    try:
        import pyreadline3 as readline
    except ImportError:
        readline = None

# Load history at startup
if readline:
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        readline.add_history(line)
    except Exception as e:
        print(f"[Warning] Failed to load history: {e}", file=sys.stderr)

def save_history() -> None:
    """Save current session history to file."""
    if not readline:
        return
    try:
        # Get current history and deduplicate preserving order
        hist = [readline.get_history_item(i) for i in range(1, readline.get_current_history_length() + 1)]
        unique = list(dict.fromkeys(hist))[:MAX_HISTORY]
        # Write
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for cmd in unique:
                f.write(cmd + "\n")
    except Exception as e:
        print(f"[Warning] Failed to save history: {e}", file=sys.stderr)

# ================================
# HUFFMAN OBJECT
# ================================
H = huffman.DEFAULT_HUFFMAN


class ZandronumError(Exception):
    pass


class RCONClient:
    def __init__(self, show_colors: bool = False):
        self.socket: socket.socket | None = None
        self.address: tuple[str, int] | None = None
        self.rcon_password: str | None = None
        self.running = False
        self.show_colors = show_colors
        self.logged_in = False
        self.rcon_identity: str | None = None
        self._output_lock = threading.Lock()

    # ================================
    #  Huffman encode/decode
    # ================================
    def encode(self, seq: Sequence[Union[int, str, bytes]]) -> bytes:
        buf = BytesIO()
        for item in seq:
            if isinstance(item, bytes):
                if len(item) > MAX_PACKET_SIZE:
                    raise ValueError(f"Packet element too large: {len(item)} bytes")
                buf.write(item)
            elif isinstance(item, str):
                buf.write(item.encode())
            elif isinstance(item, int):
                if not 0 <= item <= 255:
                    raise ValueError(f"Int out of range (0-255): {item}")
                buf.write(bytes([item]))
            else:
                raise TypeError(f"Unsupported packet element: {item!r}")
        return H.encode(buf.getvalue())

    def decode(self, packet: bytes) -> bytes:
        return H.decode(packet)

    # ================================
    #  Packet handling
    # ================================
    def send_packet(self, parts: Sequence[Union[int, str, bytes]]) -> None:
        encoded = self.encode(parts)
        self.socket.sendto(encoded, self.address)

    def _print(self, *args) -> None:
        """Thread-safe print; each output line is prefixed with '>> '."""
        message = " ".join(str(a) for a in args)
        message = message.rstrip("\r\n")
        with self._output_lock:
            for line in message.split("\n"):
                print(">> " + line)

    def _format(self, packet_data: bytes) -> str:
        """Decode server text and optionally strip color codes."""
        msg = packet_data.decode(errors="replace")
        if not self.show_colors:
            msg = strip_colors(msg)
        return msg.replace("\x00", "")

    def _parse_rcon_identity(self, packet_data: bytes) -> str | None:
        """Extract our '(RCON by ip:port)' attribution from the LoggedIn log blob."""
        matches = list(CMD_IDENTITY_PATTERN.finditer(packet_data.decode(errors="replace")))
        if not matches:
            return None
        return f"(RCON by {matches[-1].group(1)})"

    def handle_packet(self, packet_id: int, packet_data: bytes) -> None:
        match packet_id:
            case headers.OLD_PROTOCOL:
                raise ZandronumError("Server reports old protocol.")
            case headers.BANNED:
                raise ZandronumError("Your IP is banned on this server.")
            case headers.SALT:
                salt = packet_data[:32]
                md5 = hashlib.md5(salt + self.rcon_password.encode()).hexdigest()
                self.send_packet((clrc["Password"], md5.encode()))
            case headers.LOGGED_IN:
                self.rcon_identity = self._parse_rcon_identity(packet_data)
                self.logged_in = True
            case headers.INVALID_PASSWORD:
                raise ZandronumError("Invalid RCON password.")
            case headers.MESSAGE:
                msg = self._format(packet_data)
                # Suppress the server's command-echo (e.g. "-> cmd (RCON by ...)") in all modes.
                if not CMD_ECHO_PATTERN.match(strip_colors(msg)):
                    self._print(msg)
            case headers.TABCOMPLETE:
                self._print(self._format(packet_data))
            case headers.TOO_MANY_TABCOMPLETE:
                self._print("[Warning] Server reports too many tab completion results; some results omitted.")
            case headers.UPDATE:
                pass
            case _:
                self._print(f"[server:{packet_id}] Unknown packet")

    # ================================
    #  Connection
    # ================================
    def connect(self, address: tuple[str, int], password: str) -> None:
        # Validate inputs
        host_str, port = address
        if not host_str:
            raise ZandronumError("Host cannot be empty")
        if not (1 <= port <= 65535):
            raise ZandronumError(f"Invalid port: {port} (must be 1-65535)")
        self.address = address
        self.rcon_password = password

        # Resolve the address and try all available families (IPv4 + IPv6).
        # We try AF_INET6 first (dual-stack), then fall back to AF_INET.
        host_str = address[0]
        port = address[1]

        # Determine if host is an IPv6, IPv4, or hostname
        try:
            ipaddress.ip_address(host_str)
            is_ip = True
        except ValueError:
            is_ip = False

        # Try IPv6 dual-stack first, then IPv4
        families_to_try: list[int] = []
        if is_ip and ":" in host_str:
            families_to_try = [socket.AF_INET6]
        elif is_ip and "." in host_str:
            families_to_try = [socket.AF_INET]
        else:
            # Hostname: try both IPv6 and IPv4
            families_to_try = [socket.AF_INET6, socket.AF_INET]

        print(f"[+] Connecting to {address}...")
        last_error: Exception | None = None
        for family in families_to_try:
            try:
                self.socket = socket.socket(family, socket.SOCK_DGRAM)
                if family == socket.AF_INET6:
                    self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)  # dual-stack
                self.socket.settimeout(SOCKET_TIMEOUT)
                self.socket.connect(address)  # validates the address early
                print(f"[+] Using {('IPv6' if family == socket.AF_INET6 else 'IPv4')}")
                break
            except Exception as err:
                last_error = err
                if self.socket:
                    self.socket.close()
                self.socket = None
                continue

        if self.socket is None:
            raise ZandronumError(f"Connection failed: {last_error}")

        begin = self.encode((clrc["BeginConnection"], protocol_ver))
        self.socket.sendto(begin, self.address)

        # Handshake: answer the Salt challenge, then wait for the LoggedIn packet.
        self.logged_in = False
        while not self.logged_in:
            try:
                raw, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
            except socket.timeout:
                raise ZandronumError("Connection timed out.")
            data = self.decode(raw)
            self.handle_packet(data[0], data[1:])

        self.running = True
        threading.Thread(target=self.listen_loop, daemon=True).start()

    # ================================
    #  Listener
    # ================================
    def listen_loop(self) -> None:
        while self.running:
            try:
                data, _ = self.socket.recvfrom(MAX_PACKET_SIZE)
                decoded = self.decode(data)
                p_id = decoded[0]
                self.handle_packet(p_id, decoded[1:])

            except socket.timeout:
                if self.running:
                    self.send_packet((clrc["Pong"],))
                continue

            except ZandronumError as err:
                print("[ERROR]:", err)
                self.disconnect()
                break

            except Exception as e:
                print(f"[Unhandled error]: {e}")
                self.disconnect()
                break

    # ================================
    #  User commands
    # ================================
    def send_command(self, cmd: str):
        self.send_packet((clrc["Command"], cmd))

    def disconnect(self) -> None:
        self.running = False
        # Wake the socket so recvfrom unblocks
        if self.socket:
            try:
                self.socket.sendto(b"", self.address)
            except Exception:
                pass
        try:
            self.send_packet((clrc["Disconnect"],))
        except Exception:
            pass
        try:
            if self.socket:
                self.socket.close()
        except Exception:
            pass
        print("[Disconnected]")


# ================================
#  Main
# ================================
def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rcon_client.py",
        description="A Zandronum v3+ RCON client with Huffman compression, persistent history, and thread-safe comms.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Interactive mode:\n"
            "  RCON_PASSWORD=mypassword python3 rcon_client.py 127.0.0.1 7777\n"
            "\n"
            "  # Batch mode (single command):\n"
            "  RCON_PASSWORD=mypassword python3 rcon_client.py 127.0.0.1 7777 --command GameVersion\n"
        ),
    )
    parser.add_argument("ip", help="Server IP address or hostname")
    parser.add_argument("port", type=int, help="Server RCON port")
    parser.add_argument("--colors", action="store_true", help="Show raw color codes from server (default: strip)")
    parser.add_argument("--command", dest="batch_command", help="Send a single command and exit (batch/CI mode)")
    args = parser.parse_args()

    ip = args.ip
    port = args.port

    # Validate RCON password
    if not RCON_PASSWORD:
        print("Error: RCON_PASSWORD environment variable is not set.")
        print("Set it like this: RCON_PASSWORD=your_password python3 rcon_client.py <ip> <port>")
        sys.exit(1)

    # Enable readline features
    if readline:
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set editing-mode emacs")

    client = RCONClient(show_colors=args.colors)
    try:
        client.connect((ip, port), RCON_PASSWORD)

        identity = client.rcon_identity or ""
        print(f"[ Connected ]  {identity}")
        print(">> [ OK ] Logged in.")
        print("Type commands. Ctrl+C to quit.")

        if args.batch_command:
            # Batch mode: send one command and wait for response
            client.send_command(args.batch_command)
            # Wait for server response
            time.sleep(BATCH_RESPONSE_DELAY)
        else:
            while True:
                try:
                    cmd = input().strip()
                except EOFError:
                    break
                if not cmd:
                    continue
                client.send_command(cmd)  # terminal echoes the typed command
                # Add to history only if not duplicate of last
                if readline and (readline.get_current_history_length() == 0 or
                                 readline.get_history_item(readline.get_current_history_length()) != cmd):
                                    readline.add_history(cmd)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[FATAL] {e}")
    finally:
        save_history()
        client.disconnect()


if __name__ == "__main__":
    main()
