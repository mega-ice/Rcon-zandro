# Rcon-zandro

A Python-based Remote Console (RCON) client for Zandronum v3+ servers, featuring persistent command history, thread-safe communication, and Zandronum-specific protocol support.

## Overview

Rcon-zandro provides a command-line interface for remote administration of Zandronum servers. It implements the Zandronum RCON protocol using UDP, including support for the proprietary Huffman compression algorithm used by Zandronum (Skulltag frequencies).

## Features

- **Remote Server Administration**: Execute console commands on remote Zandronum servers
- **Persistent Command History**: Commands are saved to `~/.rcon_history` and persist across sessions
- **Huffman Compression**: Uses Zandronum's proprietary compression algorithm for efficient protocol communication
- **Color Support**: Optional color code stripping in server output
- **Tab Completion**: Command completion support for easier typing
- **Thread-Safe Communication**: Background thread handles incoming server messages
- **Graceful Disconnection**: Automatic cleanup on exit or errors

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only Python standard library)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Rcon-zandro
```

2. Make the script executable (optional):
```bash
chmod +x rcon_client.py
```

## Configuration

Edit `rcon_client.py` to configure the RCON password and other options:

```python
# Line 21-25 in rcon_client.py
SHOW_COLORS = False  # Set to True to enable color codes in output

# CHANGE THIS LINE with your server password!
RCON_PASSWORD = "your_server_password_here"
```

## Usage

### Basic Connection

Connect to a Zandronum server:

```bash
python3 rcon_client.py <server_ip> <server_port>
```

Example:
```bash
python3 rcon_client.py 127.0.0.1 7777
```

### Interactive Commands

Once connected, you can type commands directly:

```
>> kick #1 reason
>> map dmmap1
>> say Hello everyone!
>> cvarlist
>> status
```

### Command History

- Use **Up/Down Arrow Keys** to navigate through previous commands
- Commands are automatically saved to `~/.rcon_history`
- History persists across sessions (up to 1000 commands)
- Tab key completes partial commands

### Exiting

- Press **Ctrl+C** to gracefully disconnect
- Use the `disconnect` command if needed
- Connection is automatically cleaned up on exit

## Protocol Details

### UDP Communication

The RCON protocol uses UDP for communication, with the following characteristics:

- **Connection Flow**:
  1. Client sends `BeginConnection` packet with protocol version
  2. Server responds with `Salt` packet containing a 32-byte salt
  3. Client calculates MD5 hash of (salt + password) and sends `Password` packet
  4. Server responds with `LoggedIn` or `InvalidPassword`

### Packet Types

**Client-to-Server**:
- `52` - BeginConnection (protocol version)
- `53` - Password (MD5 hash)
- `54` - Command
- `55` - Pong (keep-alive)
- `56` - Disconnect
- `57` - TabComplete

**Server-to-Client**:
- `32` - OldProtocol
- `33` - Banned
- `34` - Salt (32 bytes)
- `35` - LoggedIn
- `36` - InvalidPassword
- `37` - Message
- `38` - Update
- `39` - TabComplete
- `40+` - PlayerData, AdminCount, Map (various updates)

### Huffman Compression

Zandronum uses a proprietary Huffman codec with specific frequency tables. The implementation in `huffman.py`:

- **Frequency Table**: Contains 91 character frequencies (Zandronum's Skulltag implementation)
- **Encoding**: Characters are encoded using Huffman tree
- **Fallback**: If compression doesn't reduce size, raw data is sent with `0xFF` prefix
- **Padding**: Compressed data is padded to byte boundaries

## Project Structure

```
Rcon-zandro/
├── rcon_client.py    # Main RCON client implementation
├── huffman.py         # Zandronum Huffman compression codec
├── headers.py         # Protocol constants and packet IDs
└── README.md          # This file
```

## Security Considerations

**⚠️ IMPORTANT SECURITY WARNING**

The RCON password is currently hardcoded in `rcon_client.py` (line 24).

## Troubleshooting

### Connection Timed Out
- Verify server IP and port are correct
- Ensure the server is running and accepts RCON connections
- Check firewall settings
- Confirm the server's RCON port is not blocked

### Invalid Password
- Double-check the password in `rcon_client.py`
- Ensure no extra spaces or hidden characters
- Verify the password matches exactly what the server expects

### Command Not Recognized
- Server might not support the command
- Check server console for error messages
- Ensure you're using the correct Zandronum version

## Technical Implementation

### Key Components

**RCONClient Class**
- Handles UDP socket communication
- Manages connection lifecycle
- Encodes/decodes Huffman-compressed packets
- Processes incoming server packets

**Huffman Codec**
- Builds Huffman tree from frequency table
- Creates lookup table for all 256 byte values
- Handles compression fallback and padding

**History Management**
- Uses `readline` module for history
- Falls back to `pyreadline3` on Windows
- Saves to `~/.rcon_history` with 1000 command limit

## License

This project is a Python implementation of Zandronum RCON protocol.
Please refer to the original Zandronum project for licensing information.

## Contributing

To add features or fix bugs:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Acknowledgments

- Zandronum team for the RCON protocol specification


## Version History

- **v1.0** - Initial Python implementation
  - UDP-based RCON client
  - Huffman compression support
  - Persistent command history
  - Thread-safe communication
