# Rcon-zandro

A Python-based Remote Console (RCON) client for Zandronum v3+ servers, featuring persistent command history, thread-safe communication, and Zandronum-specific protocol support.

## Overview

Rcon-zandro provides a command-line interface for remote administration of Zandronum servers. It implements the Zandronum RCON protocol using UDP, including support for the proprietary Huffman compression algorithm used by Zandronum (Skulltag frequencies).

## Features

- **Remote Server Administration**: Execute console commands on remote Zandronum servers
- **Persistent Command History**: Commands are saved to `~/.rcon_history` and persist across sessions
- **Huffman Compression**: Uses Zandronum's proprietary compression algorithm for efficient protocol communication
- **Color Support**: Optional color code stripping (`--colors` flag)
- **Batch/CI Mode**: Send a single command and exit (`--command <cmd>`)
- **CLI Help**: `argparse`-based help with usage examples
- **IPv4/IPv6 Auto-Detection**: Automatically detects address family and falls back gracefully
- **Thread-Safe Output**: Lock-guarded `_print()` prevents output interleaving from the background listener thread
- **match/case Dispatch**: Clean `handle_packet()` using Python 3.10+ pattern matching
- **Tab Completion**: Readline-based tab completion
- **Graceful Disconnection**: Automatic cleanup on exit or errors
- **Secure Credential Handling**: RCON password configured via environment variable

## Requirements

- Python 3.10 or higher (for `match/case` syntax)
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

Set the RCON password via the `RCON_PASSWORD` environment variable (required):

```bash
RCON_PASSWORD=your_server_password python3 rcon_client.py <server_ip> <server_port>
```

## Usage

### Basic Connection

Connect to a Zandronum server interactively:

```bash
RCON_PASSWORD=your_password python3 rcon_client.py <server_ip> <server_port>
```

Example:
```bash
RCON_PASSWORD=mypass python3 rcon_client.py 10.10.0.2 10667
```

### Batch / CI Mode

Send a single command and exit (useful for scripts and CI):

```bash
RCON_PASSWORD=mypass python3 rcon_client.py 10.10.0.2 10667 --command "GameVersion"
```

### Color Output

Preserve server color codes in output:

```bash
RCON_PASSWORD=mypass python3 rcon_client.py 10.10.0.2 10667 --colors --command "status"
```

### Help

Display usage information:

```bash
python3 rcon_client.py --help
```

### Interactive Commands

Once connected, you can type commands directly:

```
>> kick #1 reason
>> map dmmap1
>> say Hello everyone!
>> cvarlist
>> GameVersion
>> CmdList
```

### Command History

- Use **Up/Down Arrow Keys** to navigate through previous commands
- Commands are automatically saved to `~/.rcon_history`
- History persists across sessions (up to 1000 commands)
- Tab key completes partial commands

### Exiting

- Press **Ctrl+C** to gracefully disconnect
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

**Client-to-Server** (`headers.clrc`):
- `52` - BeginConnection (protocol version)
- `53` - Password (MD5 hash)
- `54` - Command
- `55` - Pong (keep-alive)
- `56` - Disconnect
- `57` - TabComplete

**Server-to-Client** (top-level constants):
- `32` - OldProtocol
- `33` - Banned
- `34` - Salt (32 bytes)
- `35` - LoggedIn
- `36` - InvalidPassword
- `37` - Message
- `38` - Update
- `39` - TabComplete
- `40` - TooManyTabCompletes

## Huffman Compression

Zandronum uses a proprietary Huffman codec with specific frequency tables. The implementation in `huffman.py`:

- **Frequency Table**: Contains 256 character frequencies (Zandronum's Skulltag implementation)
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

The RCON password should **not** be hardcoded. Configure it via the `RCON_PASSWORD` environment variable instead:

```bash
export RCON_PASSWORD="your_server_password_here"
```

## Troubleshooting

### Connection Timed Out
- Verify server IP and port are correct
- Ensure the server is running and accepts RCON connections
- Check firewall settings
- Confirm the server's RCON port is not blocked

### Missing Password
- Ensure `RCON_PASSWORD` is set before running:
  ```bash
  export RCON_PASSWORD="your_password"
  ```
- The client will exit with a clear error if the variable is not set

### Command Not Recognized
- Server might not support the command
- Check server console for error messages
- Ensure you're using the correct Zandronum version

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
