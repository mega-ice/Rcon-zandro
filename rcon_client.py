#!/usr/bin/env python3
# Zandronum RCON client (with CLI args + persistent command history)

import hashlib
import socket
import threading
import time
import os
from io import BytesIO
import sys
from pathlib import Path
import re

import huffman
from headers import svrc, svrcu, clrc, protocol_ver

# ================================
# CONFIGURATION SECTION
# ================================
# Enable color output (set to True to show colors, False to strip them)
SHOW_COLORS = False

# Hardcoded RCON password - CHANGE THIS!
RCON_PASSWORD = "YOUR_SERVER_PASSWORD_HERE"

# ================================
# COLOR STRIPPING UTILITY
# ================================
def strip_colors(text):
    # Strip Zandronum Player color codes from text using regex.
    # Handle color codes like \c[uh0] through \c[uh99], \c[a-z0-9-], etc.
    # This pattern matches both \c[uh0] and \cA style codes correctly
    color_pattern = r'\\c[a-zA-Z0-9\-]+$$9956$$|\c[a-zA-Z0-9\-]'

    # check, process text to avoid regex errors
    try:
        return re.sub(color_pattern, '', text)
    except re.error:
        # If regex fails, return text unchanged
        return text

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

def save_history():
    """Save current session history to file."""
    if not readline:
        return
    try:
        # Get current history
        hist = [readline.get_history_item(i) for i in range(1, readline.get_current_history_length() + 1)]
        # Keep only last N unique commands
        unique = []
        seen = set()
        for cmd in reversed(hist):
            if cmd and cmd not in seen:
                seen.add(cmd)
                unique.append(cmd)
                if len(unique) >= MAX_HISTORY:
                    break
        unique.reverse()
        # Write
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for cmd in unique:
                f.write(cmd + "\n")
    except Exception as e:
        print(f"[Warning] Failed to save history: {e}", file=sys.stderr)

# ================================
# HUFFMAN OBJECT
# ================================
H = huffman.HuffmanObject(huffman.SKULLTAG_FREQS)


class ZandronumError(Exception):
    pass


class RCONClient:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(4.0)
        self.address = None
        self.rcon_password = None
        self.running = False

    # ================================
    #  Huffman encode/decode
    # ================================
    def encode(self, seq):
        buf = BytesIO()
        for item in seq:
            if isinstance(item, bytes):
                buf.write(item)
            elif isinstance(item, str):
                buf.write(item.encode())
            elif isinstance(item, int):
                buf.write(bytes([item]))
            else:
                raise TypeError(f"Unsupported packet element: {item!r}")
        return H.encode(buf.getvalue())

    def decode(self, packet):
        return H.decode(packet)

    # ================================
    #  Packet handling
    # ================================
    def send_packet(self, parts):
        encoded = self.encode(parts)
        self.socket.sendto(encoded, self.address)

    def handle_packet(self, packet_id, packet_data):
        if packet_id == svrc["OldProtocol"]:
            raise ZandronumError("Server reports old protocol.")

        elif packet_id == svrc["Banned"]:
            raise ZandronumError("Your IP is banned on this server.")

        elif packet_id == svrc["Salt"]:
            salt = packet_data[:32]
            md5 = hashlib.md5(salt + self.rcon_password.encode()).hexdigest()
            self.send_packet((clrc["Password"], md5.encode()))

        elif packet_id == svrc["LoggedIn"]:
            print("[ OK ] Logged in.")

        elif packet_id == svrc["InvalidPassword"]:
            raise ZandronumError("Invalid RCON password.")

        elif packet_id == svrc["Message"]:
            msg = packet_data.decode(errors="replace")
            if not SHOW_COLORS:
                msg = strip_colors(msg)
            print(msg, end="")

        elif packet_id == svrc["Update"]:
            pass
        elif packet_id == svrc["TabComplete"]:
            pass
        elif packet_id == svrc["TooManyTabCompletes"]:
            pass

        elif packet_id in svrcu.values():
            msg = packet_data.decode(errors="replace")
            if not SHOW_COLORS:
                msg = strip_colors(msg)
            print(msg, end="")

        else:
            print(f"[server:{packet_id}] Unknown packet")

    # ================================
    #  Connection
    # ================================
    def connect(self, address, password):
        self.address = address
        self.rcon_password = password

        print(f"[+] Connecting to {address}...")

        begin = self.encode((clrc["BeginConnection"], protocol_ver))
        self.socket.sendto(begin, self.address)

        try:
            raw, srv = self.socket.recvfrom(4096)
        except socket.timeout:
            raise ZandronumError("Connection timed out.")

        print("[ OK ] Server found:", srv)

        data = self.decode(raw)
        packet_id = data[0]
        self.handle_packet(packet_id, data[1:])

        self.running = True
        threading.Thread(target=self.listen_loop, daemon=True).start()

    # ================================
    #  Listener
    # ================================
    def listen_loop(self):
        while self.running:
            try:
                data, _ = self.socket.recvfrom(4096)
                decoded = self.decode(data)
                p_id = decoded[0]
                self.handle_packet(p_id, decoded[1:])

            except socket.timeout:
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

    def disconnect(self):
        if self.running:
            self.running = False
            try:
                self.send_packet((clrc["Disconnect"],))
            except:
                pass
        try:
            self.socket.close()
        except:
            pass
        print("[Disconnected]")


# ================================
#  Main
# ================================
def main():
    if len(sys.argv) != 3:
        print("Usage: python rcon_client.py <ip> <port>")
        sys.exit(1)

    ip = sys.argv[1]
    port = int(sys.argv[2])

    # Enable readline features
    if readline:
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set editing-mode emacs")

    client = RCONClient()
    try:
        client.connect((ip, port), RCON_PASSWORD)
        print("[ Connected ]")
        print("Type commands. Ctrl+C to quit.\n")

        while True:
            try:
                cmd = input(">> ").strip()
                if cmd:
                    client.send_command(cmd)
                    # Add to history only if not duplicate of last
                    if readline and (readline.get_current_history_length() == 0 or
                                     readline.get_history_item(readline.get_current_history_length()) != cmd):
                        readline.add_history(cmd)
            except EOFError:
                break
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"[FATAL] {e}")
    finally:
        save_history()  # ← Save on exit
        client.disconnect()


if __name__ == "__main__":
    main()
