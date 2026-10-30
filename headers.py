protocol_ver = 4

svrc = {
    'OldProtocol':         32,
    'Banned':              33,
    'Salt':                34,
    'LoggedIn':            35,
    'InvalidPassword':     36,
    'Message':             37,
    'Update':              38,
    'TabComplete':         39,
    'TooManyTabCompletes': 40,
}

clrc = {
    'BeginConnection': 52,
    'Password':        53,
    'Command':         54,
    'Pong':            55,
    'Disconnect':      56,
    'TabComplete':     57,
}

svrcu = {
    'PlayerData': 0,
    'AdminCount': 1,
    'Map':        77,
}

# Named packet-type constants.
# Top-level int constants can be used as `match`/`case` value patterns via
# dotted-name references (e.g. `case headers.MESSAGE:`), unlike dict subscripts.
OLD_PROTOCOL: int = 32
BANNED: int = 33
SALT: int = 34
LOGGED_IN: int = 35
INVALID_PASSWORD: int = 36
MESSAGE: int = 37
UPDATE: int = 38
TABCOMPLETE: int = 39
TOO_MANY_TABCOMPLETE: int = 40
