protocol_ver = 4

# Named packet-type constants.
# Top-level int constants can be used as `match`/`case` value patterns via
# dotted-name references (e.g. `case headers.MESSAGE:`), unlike dict subscripts.
OLD_PROTOCOL = 32
BANNED = 33
SALT = 34
LOGGED_IN = 35
INVALID_PASSWORD = 36
MESSAGE = 37
UPDATE = 38
TABCOMPLETE = 39
TOO_MANY_TABCOMPLETE = 40

clrc = {
    'BeginConnection': 52,
    'Password':        53,
    'Command':         54,
    'Pong':            55,
    'Disconnect':      56,
    'TabComplete':     57,
}
