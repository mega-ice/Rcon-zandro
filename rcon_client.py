#!/usr/bin/env python3
# Zandronum RCON client (with Cli args + command history in active session)

import hashlib
import socket
import threading
import time
from io import BytesIO
import sys

import huffman
from fixedcolors import get_color_less
from headers import svrc, svrcu, clrc, protocol_ver

# ------------ COMMAND HISTORY ---------------
try:
    import readline  # Linux/macOS
except ImportError:
    try:
        import pyreadline as readline  # Older Windows
    except ImportError:
        try:
            import pyreadline3 as readline  # Newer Windows
        except ImportError:
            readline = None  # No history available


# Zandronum-specific Huffman Frequencies
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

    # -------------------------------
    #  Huffman wrappers encode/decode
    # -------------------------------
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

    # -------------------------------
    #  Packet handling
    # -------------------------------
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
            msg = get_color_less(packet_data.decode(errors="replace"))
            print(msg, end="")

        elif packet_id == svrc["Update"]:
            pass
        elif packet_id == svrc["TabComplete"]:
            pass
        elif packet_id == svrc["TooManyTabCompletes"]:
            pass

        elif packet_id in svrcu.values():
            msg = get_color_less(packet_data.decode(errors="replace"))
            print(msg, end="")

        else:
            print(f"[server:{packet_id}] Unknown packet")

    # -------------------------------
    #  Connection
    # -------------------------------
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

    # -------------------------------
    #  Listener
    # -------------------------------
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

    # -------------------------------
    #  User commands
    # -------------------------------
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


# ================================================================
#  Interactive console and server password
# ================================================================
def main():
    if len(sys.argv) != 3:
        print("Usage: python rcon_console.py <ip> <port>")
        sys.exit(1)

    ip = sys.argv[1]
    port = int(sys.argv[2])
    password = "YOUR_SERVER_PASSWORD_HERE"   # server password!

    # Enable command history if supported
    if readline:
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set editing-mode emacs")

    client = RCONClient()
    client.connect((ip, port), password)

    print("[ Connected ]")
    print("Type commands. Ctrl+C to quit.\n")

    try:
        while True:
            try:
                cmd = input(">> ")
                if cmd.strip():
                    client.send_command(cmd)
            except EOFError:
                break

    except KeyboardInterrupt:
        pass

    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
